from datetime import datetime
from typing import List

from sqlalchemy import Column, String, BigInteger, DateTime, func, Text,  Boolean
from sqlalchemy.dialects.postgresql import ARRAY

from app.core.database import Base


class Priority(Base):
    __tablename__ = "priority"

    id: int = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    priority_name: str = Column(Text, nullable=False)
    resolutions: List[str] = Column(ARRAY(String), nullable=False)
    subtitles: List[str] = Column(ARRAY(String), nullable=False)
    mosaic: List[str] = Column(ARRAY(String), nullable=False)
    priority_sort: List[str] = Column(ARRAY(String), nullable=False)
    is_default: bool = Column(Boolean, nullable=False)
    create_time: datetime = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    update_time: datetime = Column(DateTime(timezone=True), onupdate=func.now())
