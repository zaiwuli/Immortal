import hashlib,json,threading
from datetime import datetime,timezone
from sqlalchemy.dialects.postgresql import insert
from concurrent.futures import ThreadPoolExecutor
from app.utils.log import logger
from app.core.database import session_scope
from app.models import Article,Converted,Target,Config
from app.collector.service import convert,filtered
lock=threading.Lock()
DEFAULT={'mode':'realtime','cron':'0 * * * *','fallback_minutes':15}
def settings():
 with session_scope() as db:
  row=db.get(Config,'sync');return {**DEFAULT,**(row.content if row else {})}
progress_lock=threading.Lock()
progress={"running":False,"processed":0,"total":0,"stats":{},"error":None}
executor=ThreadPoolExecutor(max_workers=1)
def state():
 with progress_lock:return {**progress,"stats":dict(progress["stats"])}
def start(filters=None,operation=None):
 with progress_lock:
  if progress["running"] or lock.locked():return {"started":False,"message":"同步正在运行，请查看进度"}
  progress.update(running=True,processed=0,total=0,stats={},error=None)
 executor.submit(process,filters,True,operation)
 return {"started":True,"message":"已开始后台同步"}
def process(filters=None,reserved=False,operation=None,wait=False):
 if not lock.acquire(blocking=wait):
  if reserved:
   with progress_lock:progress['running']=False
  return {'busy':True}
 stats={'inserted':0,'existing':0,'skipped':0,'failed':0,'conflict':0}
 try:
  with session_scope() as db:
   ids=[item[0] for item in filtered(db,filters or {}).with_entities(Article.id).order_by(Article.id).all()]
  with progress_lock:progress.update(running=True,processed=0,total=len(ids),stats=dict(stats),error=None)
  logger.info(f'开始转换同步，共 {len(ids)} 条文章')
  for offset in range(0,len(ids),500):
   with session_scope() as db:
    for a in db.query(Article).filter(Article.id.in_(ids[offset:offset+500])).order_by(Article.id).all():
     try:
      with db.begin_nested():
       row=db.get(Converted,a.id)
       if operation=='clear_size' and (a.merge_status!='failed' or a.error!='大小超出目标整数范围'):
        stats['skipped']+=1;continue
       if operation=='resolve_conflict' and a.merge_status!='conflict':
        stats['skipped']+=1;continue
       clear_size=bool(row and row.size_cleared) or operation=='clear_size'
       payload=convert(a,clear_size=clear_size)
       target_tid=row.target_tid if row and row.target_tid is not None else a.tid
       if operation=='resolve_conflict':target_tid=a.tid*10001
       if operation=='resolve_conflict' and (db.get(Target,target_tid) or db.query(Converted).filter(Converted.target_tid==target_tid,Converted.article_id!=a.id).first()):
        stats['conflict']+=1;a.error='备用 TID 已占用，请重新检查';continue
       if not 0<target_tid<=9007199254740991:raise ValueError('目标 TID 超出安全整数范围')
       payload['tid']=target_tid
       payload=json.loads(json.dumps(payload,default=str));fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
       if not operation and row and row.fingerprint==fingerprint and row.status in ('inserted','existing','conflict'):stats['skipped']+=1;continue
       if not row:row=Converted(article_id=a.id);db.add(row)
       row.payload=payload;row.fingerprint=fingerprint
       actual=dict(payload)
       if actual.get('publish_date'):actual['publish_date']=datetime.fromisoformat(actual['publish_date']).date()
       created=db.execute(insert(Target).values(**actual).on_conflict_do_nothing(index_elements=['tid']).returning(Target.tid)).scalar();old=db.get(Target,target_tid)
       status='inserted' if created is not None else ('existing' if old and old.website==a.website and old.detail_url==a.detail_url else 'conflict')
       if status in ('inserted','existing'):
        row.target_tid=target_tid;row.size_cleared=clear_size
       row.status=status;row.error='不同站点 ID 冲突' if status=='conflict' else None;row.synced_at=datetime.now(timezone.utc);a.merge_status=status;a.error=row.error;a.merged_at=row.synced_at;stats[status]+=1
     except Exception as e:
      row=db.get(Converted,a.id)
      if not row:row=Converted(article_id=a.id);db.add(row)
      row.status='failed';row.error=str(e);a.merge_status='failed';a.error=str(e);stats['failed']+=1
   with progress_lock:progress.update(processed=min(offset+500,len(ids)),stats=dict(stats))
   logger.info(f'同步进度 {min(offset+500,len(ids))}/{len(ids)}：新增 {stats["inserted"]}，已存在 {stats["existing"]}，跳过 {stats["skipped"]}，失败 {stats["failed"]}，冲突 {stats["conflict"]}')
  return stats
 except Exception as e:
  with progress_lock:progress['error']=str(e)
  logger.exception('转换同步异常中断')
  raise
 finally:
  with progress_lock:progress.update(running=False,stats=dict(stats))
  lock.release()
def tick():
 if settings()['mode']=='realtime':return process()
