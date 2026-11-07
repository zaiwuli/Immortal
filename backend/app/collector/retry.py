"""Automatic extra retries, serialized with ordinary crawling."""
from datetime import datetime,timedelta,timezone
from sqlalchemy.dialects.postgresql import insert
from app.core.database import session_scope
from app.models import Retry,Article,Batch
from app.collector import runtime
from app.utils.log import logger

def register(website,section,tids):
 with session_scope() as db:
  for tid in set(tids):
   db.execute(insert(Retry).values(website=website,tid=tid,section=section,status='waiting',auto_attempts=0,manual_attempts=0,error='详情或附件未获得可用资源',next_run=datetime.now(timezone.utc)+timedelta(minutes=5)).on_conflict_do_nothing(index_elements=['website','tid']))

def launch(ids=None):
 with runtime.lock:
  if runtime.active is not None:return False
  with session_scope() as db:
   query=db.query(Retry).filter(Retry.status.in_(['waiting','manual']))
   if ids is not None:query=query.filter(Retry.id.in_(ids))
   else:query=query.filter(Retry.status=='waiting',Retry.next_run<=datetime.now(timezone.utc))
   rows=(query.order_by(Retry.id) if ids is not None else query.order_by(Retry.id).limit(50)).all()
   if not rows:return False
   bid=Batch(kind='retry',status='running',message='手动补抓' if ids is not None else '自动额外补抓');db.add(bid);db.flush();batch_id=bid.id
   selected=[r.id for r in rows]
   for r in rows:r.resume_status=r.status;r.status='running'
  runtime.active=batch_id;runtime.phase='retrying';runtime.stop.clear()
  runtime.pool.submit(run,batch_id,selected,ids is not None)
 return True

def tick():
 if runtime.active is not None:return
 from app.collector.recovery import replay
 replay()
 launch()

def run(bid,ids,manual):
 runtime.local.batch_id=bid;completed=False
 try:
  from app.modules.crawler.sht import sht
  from app.scheduler.crawler_scheduler import save_articles,_extract_article_match_number
  from app.collector.recovery import replay
  replay();sht.mode='direct'
  for rid in ids:
   runtime.check_stop()
   with session_scope() as db:
    r=db.get(Retry,rid);tid=r.tid;section=r.section;website=r.website
    exists=db.query(Article).filter_by(tid=tid,website=website).first() is not None
   error=None
   try:data=None if exists else sht.crawler_detail(tid, expanded_links=True)
   except Exception as e:data=None;error=f'{type(e).__name__}: {e}'
   if data:
    data.update(tid=tid,section=section,website=website,match_number=_extract_article_match_number(data.get('title')))
    save_articles([Article(**data)])
   with session_scope() as db:
    r=db.get(Retry,rid)
    if manual:r.manual_attempts+=1
    else:r.auto_attempts+=1
    if exists or data:r.status='recovered';r.error=None;r.next_run=None
    else:
     r.error=error or '详情或附件未获得可用资源'
     r.status='manual' if manual or r.auto_attempts>=3 else 'waiting'
     r.next_run=None if r.status=='manual' else datetime.now(timezone.utc)+timedelta(minutes=30 if r.auto_attempts==1 else 120)
    logger.info(f'补抓帖子 {tid}：{r.status}，自动次数 {r.auto_attempts}，手动次数 {r.manual_attempts}')
   if runtime.stop.wait(1):runtime.check_stop()
  completed=True
 except runtime.Stopped:logger.info('补抓已停止，未执行项保留')
 except Exception:logger.exception('补抓中断，未执行项保留，数据库失败不计入抓取次数')
 finally:
  try:
   with session_scope() as db:
    for r in db.query(Retry).filter(Retry.id.in_(ids),Retry.status=='running'):
     r.status=r.resume_status or ('manual' if r.auto_attempts>=3 else 'waiting')
    b=db.get(Batch,bid);b.status='completed' if completed else 'interrupted';b.finished_at=datetime.now(timezone.utc)
  finally:
   runtime.local.batch_id=None
   with runtime.lock:runtime.active=None;runtime.phase='idle'
