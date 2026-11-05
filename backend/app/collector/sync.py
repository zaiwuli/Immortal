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
def start(filters=None):
 with progress_lock:
  if progress["running"] or lock.locked():return {"started":False,"message":"同步正在运行，请查看进度"}
  progress.update(running=True,processed=0,total=0,stats={},error=None)
 executor.submit(process,filters,True)
 return {"started":True,"message":"已开始后台同步"}
def process(filters=None,reserved=False):
 if not lock.acquire(False):
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
       payload=convert(a);payload=json.loads(json.dumps(payload,default=str));fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest();row=db.get(Converted,a.id)
       if row and row.fingerprint==fingerprint and row.status in ('inserted','existing','conflict'):stats['skipped']+=1;continue
       if not row:row=Converted(article_id=a.id);db.add(row)
       row.payload=payload;row.fingerprint=fingerprint
       actual=dict(payload)
       if actual.get('publish_date'):actual['publish_date']=datetime.fromisoformat(actual['publish_date']).date()
       created=db.execute(insert(Target).values(**actual).on_conflict_do_nothing(index_elements=['tid']).returning(Target.tid)).scalar();old=db.get(Target,a.tid)
       status='inserted' if created is not None else ('existing' if old.website==a.website else 'conflict')
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
