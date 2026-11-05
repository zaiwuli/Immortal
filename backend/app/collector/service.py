import ast,io,json,re
from datetime import datetime,timezone
import pandas as pd
from sqlalchemy import text,create_engine,inspect
from sqlalchemy.dialects.postgresql import insert
from app.core.database import session_scope,engine
from app.models import Article,Batch,BatchItem,Target

def links(value):
 if value is None:return []
 if isinstance(value,list):return list(dict.fromkeys(str(x).strip() for x in value if x))
 if not isinstance(value,(str,list)) and pd.isna(value):return []
 value=str(value).strip()
 if not value:return []
 if value.startswith('['):
  try:return links(json.loads(value))
  except Exception:
   try:return links(ast.literal_eval(value))
   except Exception:raise ValueError('无法解析数组字段')
 if value.startswith('{'):
  import csv
  return links(next(csv.reader([value[1:-1]],escapechar='\\')))
 if 'ed2k://' in value or 'magnet:?' in value:
  return list(dict.fromkeys(x.strip(' ,\r\n') for x in re.split(r'(?=ed2k://|magnet:\?)',value) if x.strip(' ,\r\n')))
 return list(dict.fromkeys(x.strip() for x in re.split(r'[,\r\n]+',value) if x.strip()))

def serialize(row):
 return {c.name:getattr(row,c.name) for c in row.__table__.columns}

def filtered(db,filters):
 q=db.query(Article)
 for key in ['website','section','source','batch_id','merge_status']:
  if filters.get(key) not in [None,'']:q=q.filter(getattr(Article,key)==filters[key])
 if filters.get('keyword'):q=q.filter(Article.title.ilike('%'+filters['keyword']+'%'))
 if filters.get('ids'):q=q.filter(Article.id.in_(filters['ids']))
 if filters.get('keep_section'):q=q.filter(Article.section!=filters['keep_section'])
 return q

def ingest(rows,kind):
 count={'inserted':0,'existing':0,'failed':0,'errors':[]}
 with session_scope() as db:
  b=Batch(kind=kind,status='running');db.add(b);db.flush();bid=b.id
  for index,row in enumerate(rows):
   try:
    with db.begin_nested():
     tid=int(row['tid']);website=str(row.get('website') or 'sehuatang').strip();title=str(row.get('title') or '').strip();section=str(row.get('section') or '').strip()
     if not title or not section:raise ValueError('标题和板块不能为空')
     old=db.query(Article).filter_by(tid=tid,website=website).first()
     if old:
      count['existing']+=1;db.add(BatchItem(batch_id=bid,article_id=old.id,status='existing'));continue
     date=row.get('publish_date');date=pd.to_datetime(date).date() if date else None
     a=Article(tid=tid,website=website,title=title,section=section,category=row.get('category'),match_number=row.get('match_number') or row.get('number'),publish_date=date,magnet=links(row.get('magnet')),edk=links(row.get('edk')),preview_images=links(row.get('preview_images')),detail_url=row.get('detail_url'),size=int(row['size']) if row.get('size') is not None else None,source=kind,batch_id=bid,merge_status='pending')
     db.add(a);db.flush();db.add(BatchItem(batch_id=bid,article_id=a.id,status='imported'));count['inserted']+=1
   except Exception as e:
    count['failed']+=1
    if len(count['errors'])<50:count['errors'].append({'row':index+2,'error':str(e)})
  b.status='completed';b.message=json.dumps(count,ensure_ascii=False);b.finished_at=datetime.now(timezone.utc)
 return {'batch_id':bid,**count}

def convert(a):
 urls=links(a.magnet)+links(a.edk);urls=list(dict.fromkeys(urls))
 if not urls:raise ValueError('没有可合并的下载链接')
 for key,limit in [('title',255),('section',255),('category',255),('detail_url',255),('website',32)]:
  if len(getattr(a,key) or '')>limit:raise ValueError(f'{key} 超过 {limit} 字符')
 if a.size is not None and not -2147483648<=a.size<=2147483647:raise ValueError('大小超出目标整数范围')
 return dict(tid=a.tid,title=a.title,number=a.match_number,publish_date=a.publish_date,magnet='\n'.join(urls),preview_images=','.join(links(a.preview_images)),detail_url=a.detail_url,size=a.size,section=a.section,category=a.category,website=a.website)

def merge(filters):
 stats={'inserted':0,'existing':0,'conflict':0,'failed':0}
 with session_scope() as db:
  b=Batch(kind='merge',status='running');db.add(b);db.flush()
  q=filtered(db,filters)
  if filters.get('batch_id'):
   ids=db.query(BatchItem.article_id).filter(BatchItem.batch_id==int(filters['batch_id'])).subquery();q=db.query(Article).filter(Article.id.in_(ids.select()))
  for a in q.order_by(Article.id).all():
   try:
    with db.begin_nested():
     payload=convert(a)
     created=db.execute(insert(Target).values(**payload).on_conflict_do_nothing(index_elements=['tid']).returning(Target.tid)).scalar()
     old=db.get(Target,a.tid)
     status='inserted' if created is not None else ('existing' if old.website==a.website else 'conflict')
     a.merge_status=status;a.error='目标 ID 属于不同站点' if status=='conflict' else None;a.merged_at=datetime.now(timezone.utc)
     db.add(BatchItem(batch_id=b.id,article_id=a.id,status=status,target_created=created is not None));stats[status]+=1
   except Exception as e:
    a.merge_status='failed';a.error=str(e);stats['failed']+=1;db.add(BatchItem(batch_id=b.id,article_id=a.id,status='failed',message=str(e)))
  b.status='completed';b.message=json.dumps(stats,ensure_ascii=False);b.finished_at=datetime.now(timezone.utc)
 return stats

def legacy_rows(filters):
 # Fixed old table on the same test database; never accepts SQL/table names.
 with engine.connect() as conn:
  conditions=[];params={}
  for key in ['website','section']:
   if filters.get(key):conditions.append(f'{key} = :{key}');params[key]=filters[key]
  if filters.get('min_tid'):conditions.append('tid >= :min_tid');params['min_tid']=int(filters['min_tid'])
  if filters.get('max_tid'):conditions.append('tid <= :max_tid');params['max_tid']=int(filters['max_tid'])
  sql='select * from article'+(' where '+' and '.join(conditions) if conditions else '')+' order by id'
  return [dict(r) for r in conn.execute(text(sql),params).mappings()]
