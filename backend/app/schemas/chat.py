from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class CitationItem(BaseModel):
    chunk_id: int
    document_id: int
    document_name: str
    page_number: int
    rule_number: Optional[str] = None
    section_title: Optional[str] = None
    excerpt: str
    score: float

    model_config = ConfigDict(from_attributes=True)

class ChatRequest(BaseModel):
    conversation_id: Optional[int] = None
    message: str
    stream: Optional[bool] = False
    document_id: Optional[int] = None

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender: str
    content: str
    citations: List[CitationItem] = []
    latency_ms: float = 0.0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)

class ChatResponse(BaseModel):
    conversation_id: int
    message_id: int
    answer: str
    citations: List[CitationItem] = []
    is_abstention: bool = False
    latency_ms: float
    retrieval_count: int
