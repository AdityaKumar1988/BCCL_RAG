from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class ChunkResponse(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    page_number: int
    rule_number: Optional[str] = None
    section_title: Optional[str] = None
    content: str
    token_count: int
    score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class DocumentBase(BaseModel):
    title: str

class DocumentResponse(DocumentBase):
    id: int
    filename: str
    file_size: int
    mime_type: str
    total_pages: int
    status: str
    is_scanned: bool
    summary: Optional[str] = None
    chunks_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DocumentDetailResponse(DocumentResponse):
    chunks: List[ChunkResponse] = []

class DocumentSearchQuery(BaseModel):
    query: str
    document_id: Optional[int] = None
    top_k: Optional[int] = 5
