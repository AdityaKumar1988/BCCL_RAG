from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime, timezone
from backend.app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String(64), nullable=True)
    action = Column(String(64), nullable=False)  # DOCUMENT_UPLOAD, QUERY_EXECUTED, DOCUMENT_DELETED, REINDEX, FEEDBACK
    resource = Column(String(128), nullable=True)
    details_json = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
