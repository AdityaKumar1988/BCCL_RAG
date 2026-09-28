import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import require_admin, get_current_user
from backend.app.core.logging import logger
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.chunk import DocumentChunk
from backend.app.models.ingestion import IngestionJob
from backend.app.models.conversation import Conversation
from backend.app.models.message import Message
from backend.app.models.feedback import Feedback
from backend.app.models.audit import AuditLog
from backend.app.schemas.document import DocumentResponse
from backend.app.schemas.feedback import IngestionStatusResponse, AnalyticsSummary
from backend.app.ingestion.pipeline import IngestionPipeline

router = APIRouter(prefix="/api/admin", tags=["Admin Operations"])

def run_async_ingestion(document_id: int, job_id: int, db_url: str):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        pipeline = IngestionPipeline(db)
        pipeline.process_document(document_id=document_id, job_id=job_id)
    except Exception as e:
        logger.error(f"Async ingestion failed for Doc {document_id}: {e}")
    finally:
        db.close()

@router.post("/documents/upload", response_model=IngestionStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    knowledge_base: Optional[str] = Form("CDA_Rules"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents are supported for ingestion"
        )

    # Sanitize and store file
    safe_name = f"{uuid.uuid4().hex[:8]}_{os.path.basename(file.filename)}"
    dest_path = os.path.join(settings.RAW_DATA_DIR, safe_name)
    
    with open(dest_path, "wb") as buffer:
        content = await file.read()
        if len(content) > 50 * 1024 * 1024:  # 50 MB limit
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds 50MB limit")
        buffer.write(content)

    doc_title = title or os.path.splitext(file.filename)[0].replace("_", " ").title()
    doc = Document(
        title=doc_title,
        filename=file.filename,
        file_path=dest_path,
        file_size=len(content),
        mime_type="application/pdf",
        status="UPLOADED",
        knowledge_base=knowledge_base or "CDA_Rules",
        uploaded_by=current_user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    job = IngestionJob(
        document_id=doc.id,
        status="PROCESSING",
        stage="UPLOADED",
        progress_percentage=10,
        started_at=datetime.now(timezone.utc)
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Trigger background ingestion task
    background_tasks.add_task(run_async_ingestion, doc.id, job.id, settings.DATABASE_URL)

    # Log audit
    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="DOCUMENT_UPLOAD",
        resource=f"document/{doc.id}",
        details_json=f'{{"filename": "{file.filename}", "size": {len(content)}}}',
        created_at=datetime.now(timezone.utc)
    )
    db.add(audit)
    db.commit()

    return IngestionStatusResponse(
        job_id=job.id,
        document_id=doc.id,
        document_title=doc.title,
        status=job.status,
        stage=job.stage,
        progress_percentage=job.progress_percentage,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at
    )

@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass

    db.delete(doc)
    db.commit()

    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="DOCUMENT_DELETED",
        resource=f"document/{document_id}",
        details_json=f'{{"title": "{doc.title}"}}',
        created_at=datetime.now(timezone.utc)
    )
    db.add(audit)
    db.commit()
    return None

@router.post("/documents/{document_id}/reindex", response_model=IngestionStatusResponse)
def reindex_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    job = IngestionJob(
        document_id=doc.id,
        status="PROCESSING",
        stage="REINDEXING",
        progress_percentage=10,
        started_at=datetime.now(timezone.utc)
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_async_ingestion, doc.id, job.id, settings.DATABASE_URL)

    audit = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="DOCUMENT_REINDEX",
        resource=f"document/{doc.id}",
        created_at=datetime.now(timezone.utc)
    )
    db.add(audit)
    db.commit()

    return IngestionStatusResponse(
        job_id=job.id,
        document_id=doc.id,
        document_title=doc.title,
        status=job.status,
        stage=job.stage,
        progress_percentage=job.progress_percentage,
        started_at=job.started_at,
        completed_at=job.completed_at
    )

@router.get("/ingestion/{job_id}", response_model=IngestionStatusResponse)
def get_ingestion_status(
    job_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion job not found")
    
    doc = db.query(Document).filter(Document.id == job.document_id).first()
    title = doc.title if doc else "Unknown"

    return IngestionStatusResponse(
        job_id=job.id,
        document_id=job.document_id,
        document_title=title,
        status=job.status,
        stage=job.stage,
        progress_percentage=job.progress_percentage,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at
    )

@router.get("/analytics", response_model=AnalyticsSummary)
def get_analytics(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    total_docs = db.query(Document).count()
    total_chunks = db.query(DocumentChunk).count()
    total_convs = db.query(Conversation).count()
    total_queries = db.query(Message).filter(Message.sender == "user").count()
    total_users = db.query(User).count()
    scanned_count = db.query(Document).filter(Document.is_scanned == True).count()
    
    pos_feedback = db.query(Feedback).filter(Feedback.rating > 0).count()
    neg_feedback = db.query(Feedback).filter(Feedback.rating < 0).count()

    messages = db.query(Message).filter(Message.sender == "assistant").all()
    avg_latency = sum(m.latency_ms for m in messages) / max(len(messages), 1)

    return AnalyticsSummary(
        total_documents=total_docs,
        total_chunks=total_chunks,
        total_conversations=total_convs,
        total_queries=total_queries,
        total_users=total_users,
        avg_latency_ms=round(avg_latency, 2),
        positive_feedback_count=pos_feedback,
        negative_feedback_count=neg_feedback,
        scanned_docs_count=scanned_count
    )

@router.get("/audit-logs")
def get_audit_logs(limit: int = 50, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return logs
