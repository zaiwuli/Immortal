import hashlib,json,threading
from datetime import datetime,timezone
from sqlalchemy.dialects.postgresql import insert
from app.core.database import session_scope
from app.models import Article,Converted,Target,Config
from app.collector.service import convert,filtered
lock=threading.Lock()
DEFAULT={'mode':'realtime','cron':'0 * * * *','fallback_minutes':15}
def settings():
 with session_scope() as db:
  row=db.get(Config,'sync');return {**DEFAULT,**(row.content if row else {})}
def process(filters=None):
 if not lock.acquire(False):return {'busy':True}
 stats={'inserted':0,'existing':0,'skipped':0,'failed':0,'conflict':0}
 try:
  with session_scope() as db:
   for a in filtered(db,filters or {}).order_by(Article.id).all():
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
  return stats
 finally:lock.release()
def tick():
 if settings()['mode']=='realtime':return process()
