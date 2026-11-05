from sqlalchemy import Column, BigInteger, Integer, String, Text, Date, DateTime, Boolean, JSON, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY
from app.core.database import Base
class Article(Base):
 __tablename__='immortal_article'
 id=Column(BigInteger,primary_key=True);tid=Column(BigInteger,nullable=False);website=Column(String(32),nullable=False,default='sehuatang');title=Column(Text,nullable=False);match_number=Column(String(64));publish_date=Column(Date);magnet=Column(ARRAY(Text));edk=Column(ARRAY(Text));preview_images=Column(ARRAY(Text));detail_url=Column(Text);size=Column(BigInteger);section=Column(Text,nullable=False);category=Column(Text);source=Column(String(24),default='crawl');batch_id=Column(BigInteger,index=True);merge_status=Column(String(24),default='pending');error=Column(Text);merged_at=Column(DateTime(timezone=True));create_time=Column(DateTime(timezone=True),server_default=func.now());update_time=Column(DateTime(timezone=True),onupdate=func.now())
 __table_args__=(UniqueConstraint('tid','website',name='immortal_article_source_unique'),)
class Task(Base):
 __tablename__='immortal_task'
 id=Column(BigInteger,primary_key=True);name=Column(Text,nullable=False);params=Column(JSON,default=dict);cron=Column(Text);enabled=Column(Boolean,default=False)
class Batch(Base):
 __tablename__='immortal_batch'
 id=Column(BigInteger,primary_key=True);kind=Column(Text);status=Column(Text,default='running');message=Column(Text);create_time=Column(DateTime(timezone=True),server_default=func.now());finished_at=Column(DateTime(timezone=True))
class BatchItem(Base):
 __tablename__='immortal_batch_item'
 id=Column(BigInteger,primary_key=True);batch_id=Column(BigInteger,index=True);article_id=Column(BigInteger,index=True);status=Column(Text);message=Column(Text);target_created=Column(Boolean,default=False)
class TaskLog(Base):
 __tablename__='immortal_task_log'
 id=Column(BigInteger,primary_key=True);batch_id=Column(BigInteger,index=True);message=Column(Text);create_time=Column(DateTime(timezone=True),server_default=func.now())
class Config(Base):
 __tablename__='immortal_config'
 key=Column(String(100),primary_key=True);content=Column(JSON)
class Target(Base):
 __tablename__='immortal_article_target'
 tid=Column(BigInteger,primary_key=True);emby=Column(Integer);number=Column(Text);title=Column(String(255),nullable=False);publish_date=Column(Date);magnet=Column(Text,nullable=False);preview_images=Column(Text);detail_url=Column(String(255));size=Column(Integer);section=Column(String(255),nullable=False);category=Column(String(255));website=Column(String(32));sub_type=Column(Text);create_time=Column(DateTime(timezone=True),server_default=func.now());update_time=Column(DateTime(timezone=True))
class Converted(Base):
 __tablename__='immortal_article_converted'
 article_id=Column(BigInteger,primary_key=True);payload=Column(JSON);fingerprint=Column(String(64));version=Column(Integer,default=1);status=Column(Text,default='pending');error=Column(Text);synced_at=Column(DateTime(timezone=True))
