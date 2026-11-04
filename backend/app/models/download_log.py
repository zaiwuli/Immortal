from datetime import datetime

from sqlalchemy import Column,  String, BigInteger, DateTime, func

from app.core.database import Base


class DownloadLog(Base):
    __tablename__ = "download_log"

    id: int = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    article_id: int = Column(BigInteger)
    downloader: str = Column(String(32), index=True)
    save_path: str = Column(String(255))
    create_time: datetime = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
