from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.app.core.database import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender = Column(String(32), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    citations_json = Column(Text, nullable=True)  # List of citations JSON
    retrieved_chunks_json = Column(Text, nullable=True)  # List of retrieved chunk IDs/scores
    latency_ms = Column(Float, default=0.0, nullable=False)
    token_usage_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    conversation = relationship("Conversation", back_populates="messages")
    feedback = relationship("Feedback", back_populates="message", uselist=False, cascade="all, delete-orphan")
