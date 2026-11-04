from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, String, func

from app.core.database import Base


class CastSubscribe(Base):
    __tablename__ = 'cast_subscribe'

    id: int = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    cast_id: int = Column(BigInteger, nullable=False, unique=True, index=True)
    max_coactors: int = Column(BigInteger)
    max_page: int = Column(BigInteger)
    replace_max_page: int = Column(BigInteger)
    is_single: bool = Column(Boolean, nullable=False, server_default='false')
    earliest_release_date: date = Column(Date)
    exclude_vr: bool = Column(Boolean, nullable=False, server_default='false')
    filter_id: int = Column(BigInteger)
    priority_id: int = Column(BigInteger)
    status: str = Column(String, nullable=False, index=True)
    create_time: datetime = Column(DateTime(timezone=True), server_default=func.now())
    update_time: datetime = Column(DateTime(timezone=True), onupdate=func.now())
