from datetime import datetime
from typing import List

from sqlalchemy import Column, String, BigInteger, DateTime, func, Text, Boolean
from sqlalchemy.dialects.postgresql import ARRAY

from app.core.database import Base


class Filter(Base):
    __tablename__ = "filter"

    id: int = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    filter_name: str = Column(Text, nullable=False)
    keyword: str = Column(Text)
    regex: str = Column(Text)
    resolutions: List[str] = Column(ARRAY(String))
    subtitles: List[str] = Column(ARRAY(String))
    mosaic: List[str] = Column(ARRAY(String))
    min_size: int = Column(BigInteger)
    max_size: int = Column(BigInteger)
    skip_in_library_check: bool = Column(Boolean, nullable=False, server_default='false')
    enable_pre_download: bool = Column(Boolean, nullable=False, server_default='false')
    is_default: bool = Column(Boolean, nullable=False)
    create_time: datetime = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    update_time: datetime = Column(DateTime(timezone=True), onupdate=func.now())
