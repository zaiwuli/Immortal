from datetime import datetime
from sqlalchemy import Column, String, BigInteger, DateTime, func, Text, Boolean
from app.core.database import Base

class Token(Base):
    __tablename__ = 'token'
    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    token_key = Column(String(64), nullable=False)
    token_value = Column(String(255), nullable=False)
    permissions = Column(Text, nullable=False, server_default='[]')
    enabled = Column(Boolean, nullable=False, server_default='true')
    expires_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))
    create_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

class TokenAudit(Base):
    __tablename__ = 'token_audit'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    token_id = Column(BigInteger, nullable=False, index=True)
    method = Column(String(10), nullable=False)
    path = Column(String(512), nullable=False)
    status_code = Column(BigInteger, nullable=False)
    create_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
