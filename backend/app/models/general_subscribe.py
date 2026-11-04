from datetime import datetime

from sqlalchemy import Column, Date, DateTime, func, BigInteger, String, Boolean
from sqlalchemy.dialects.postgresql import ARRAY

from app.core.database import Base


class GeneralSubscribe(Base):
    __tablename__ = "general_subscribe"

    id: int = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    number_prefix: str = Column(String(255))
    publisher: str = Column(String(255))
    series: str = Column(String(255))
    producer: str = Column(String(255))
    genres = Column(ARRAY(String))
    max_coactors: int = Column(BigInteger)
    earliest_release_date = Column(Date)
    exclude_vr: bool = Column(Boolean, nullable=False, server_default='false')
    filter_id: int = Column(BigInteger)
    priority_id: int = Column(BigInteger)
    status: str = Column(String, nullable=False, index=True)
    create_time: datetime = Column(DateTime(timezone=True), server_default=func.now())
    update_time: datetime = Column(DateTime(timezone=True), onupdate=func.now())
