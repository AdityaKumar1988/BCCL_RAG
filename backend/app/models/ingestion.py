from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.app.core.database import Base

class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), default="PENDING", nullable=False)  # PENDING, PROCESSING, COMPLETED, FAILED
    stage = Column(String(32), default="INIT", nullable=False)  # VALIDATION, TEXT_EXTRACTION, OCR, CHUNKING, EMBEDDING, INDEXING
    progress_percentage = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)

    document = relationship("Document", back_populates="ingestion_jobs")
