import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from loguru import logger
from app.core.database import session_scope
from app.models import Article,Batch,BatchItem,TaskLog
sync_pool=ThreadPoolExecutor(max_workers=1)
pool=ThreadPoolExecutor(max_workers=1)
stop=threading.Event();local=threading.local();active=None;lock=threading.Lock()
class Stopped(BaseException):pass
def check_stop():
 if stop.is_set():raise Stopped()
def current_batch():return getattr(local,'batch_id',None)
def record_items(tids):
 ids=[]
 with session_scope() as db:
  for article in db.query(Article).filter(Article.website=='sehuatang',Article.tid.in_(tids)).all():
   ids.append(article.id)
   db.add(BatchItem(batch_id=current_batch(),article_id=article.id,status='captured'))
 from app.collector.sync import settings,process
 if ids and settings()['mode']=='realtime':sync_pool.submit(process,{'ids':ids})
def log_sink(message):
 batch=current_batch()
 if getattr(local,'logging',False):return
 if batch:
  try:
   local.logging=True
   with session_scope() as db:db.add(TaskLog(batch_id=batch,message=str(message).strip()))
  except Exception:pass
  finally:local.logging=False
logger.add(log_sink)
def launch(params):
 global active
 with lock:
  if active is not None:raise ValueError('已有采集任务运行，请先停止或等待完成')
  with session_scope() as db:
   b=Batch(kind='crawl');db.add(b);db.flush();bid=b.id
  active=bid;stop.clear();pool.submit(run,bid,params);return bid
def run(bid,params):
 global active
 local.batch_id=bid;status='completed'
 try:
  from app.scheduler.sht_sheduler import sync_sht
  result=sync_sht(**params)
  check_stop()
  from app.collector.sync import settings
  merged='由同步调度器按设置处理：'+settings()['mode']
  message=f'采集结果：{result}；合并：{merged}'
 except Stopped:status='stopped';message='用户停止，已保存的数据留在暂存表，未自动合并'
 except Exception as e:status='failed';message=f'{type(e).__name__}: {e}'
 finally:
  with session_scope() as db:
   b=db.get(Batch,bid);b.status=status;b.message=message;b.finished_at=datetime.now(timezone.utc)
  local.batch_id=None
  with lock:active=None
