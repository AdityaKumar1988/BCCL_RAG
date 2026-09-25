from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class FeedbackCreate(BaseModel):
    message_id: int
    rating: int  # 1 or -1
    comment: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: int
    message_id: int
    user_id: int
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class IngestionStatusResponse(BaseModel):
    job_id: int
    document_id: int
    document_title: str
    status: str
    stage: str
    progress_percentage: int
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AnalyticsSummary(BaseModel):
    total_documents: int
    total_chunks: int
    total_conversations: int
    total_queries: int
    total_users: int
    avg_latency_ms: float
    positive_feedback_count: int
    negative_feedback_count: int
    scanned_docs_count: int
