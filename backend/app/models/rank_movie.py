from datetime import datetime
from typing import List

from sqlalchemy import Column, String, DateTime, func, BigInteger
from sqlalchemy.dialects.postgresql import ARRAY

from app.core.database import Base


class RankMovie(Base):
    __tablename__ = "rank_movie"

    id: int = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    rank_name: str = Column(String(255), nullable=False)
    movie_ids: List[int] = Column(ARRAY(BigInteger), nullable=False)
    create_time: datetime = Column(DateTime(timezone=True), server_default=func.now())
    update_time: datetime = Column(DateTime(timezone=True), onupdate=func.now())
