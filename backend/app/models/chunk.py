from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.app.core.database import Base

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=False, index=True)
    rule_number = Column(String(64), nullable=True, index=True)
    section_title = Column(String(256), nullable=True)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0, nullable=False)
    embedding_json = Column(Text, nullable=True)  # JSON-serialized dense float vector for portable storage
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document", back_populates="chunks")
