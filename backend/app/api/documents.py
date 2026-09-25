from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.app.core.database import get_db
from backend.app.models.document import Document
from backend.app.models.chunk import DocumentChunk
from backend.app.schemas.document import DocumentResponse, DocumentDetailResponse, ChunkResponse, DocumentSearchQuery
from backend.app.retrieval.hybrid import HybridRetriever

router = APIRouter(prefix="/api/documents", tags=["Documents"])

@router.get("", response_model=List[DocumentResponse])
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    results = []
    for d in docs:
        chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == d.id).count()
        doc_resp = DocumentResponse.model_validate(d)
        doc_resp.chunks_count = chunk_count
        results.append(doc_resp)
    return results

@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index).all()
    doc_resp = DocumentDetailResponse.model_validate(doc)
    doc_resp.chunks_count = len(chunks)
    doc_resp.chunks = [ChunkResponse.model_validate(c) for c in chunks]
    return doc_resp

@router.get("/{document_id}/chunks", response_model=List[ChunkResponse])
def get_document_chunks(
    document_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    rule: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id)
    if rule:
        query = query.filter(DocumentChunk.rule_number.ilike(f"%{rule}%"))
    
    chunks = query.order_by(DocumentChunk.chunk_index).offset((page - 1) * limit).limit(limit).all()
    return [ChunkResponse.model_validate(c) for c in chunks]

@router.post("/search", response_model=List[ChunkResponse])
def search_knowledge_base(search_in: DocumentSearchQuery, db: Session = Depends(get_db)):
    retriever = HybridRetriever(db)
    results = retriever.retrieve(
        query=search_in.query,
        top_k=search_in.top_k or 5,
        document_id=search_in.document_id
    )
    
    resp_list = []
    for chunk, score in results:
        cr = ChunkResponse.model_validate(chunk)
        cr.score = round(score, 4)
        resp_list.append(cr)
    return resp_list
