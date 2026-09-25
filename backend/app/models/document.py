from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.app.core.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(256), nullable=False)
    filename = Column(String(256), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(BigInteger, default=0, nullable=False)
    mime_type = Column(String(64), default="application/pdf", nullable=False)
    total_pages = Column(Integer, default=0, nullable=False)
    status = Column(String(32), default="UPLOADED", nullable=False)  # UPLOADED, PROCESSING, OCR_REQUIRED, CHUNKING, EMBEDDING, INDEXING, READY, FAILED
    is_scanned = Column(Boolean, default=False, nullable=False)
    summary = Column(Text, nullable=True)
    uploaded_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    ingestion_jobs = relationship("IngestionJob", back_populates="document", cascade="all, delete-orphan")
