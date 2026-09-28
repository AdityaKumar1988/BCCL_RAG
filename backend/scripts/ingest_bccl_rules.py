import os
import sys
from datetime import datetime, timezone

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.core.database import SessionLocal
from backend.app.models.document import Document
from backend.app.models.chunk import DocumentChunk
from backend.app.models.ingestion import IngestionJob
from backend.app.ingestion.pipeline import IngestionPipeline

def ingest_bccl_rules(pdf_path: str = None):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if not pdf_path:
        pdf_path = os.path.join(base_dir, "new_data", "CDA_Rules_1978_amended_upto_July_2006_10052018-ocr.pdf")

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Source PDF not found at {pdf_path}")

    db = SessionLocal()
    try:
        # Check if already ingested into BCCL_Rules
        existing_doc = db.query(Document).filter(
            Document.knowledge_base == "BCCL_Rules",
            Document.filename == os.path.basename(pdf_path)
        ).first()

        if existing_doc and existing_doc.status == "READY":
            chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == existing_doc.id).count()
            print(f"Document already ingested: ID={existing_doc.id}, Title='{existing_doc.title}', Chunks={chunk_count}, KB={existing_doc.knowledge_base}")
            return existing_doc.id

        file_size = os.path.getsize(pdf_path)
        title = "BCCL Conduct, Discipline & Appeal Rules, 1978 (Amended upto July 2006)"
        
        if existing_doc:
            doc = existing_doc
            doc.status = "UPLOADED"
            doc.file_size = file_size
            doc.file_path = pdf_path
            doc.updated_at = datetime.now(timezone.utc)
        else:
            doc = Document(
                title=title,
                filename=os.path.basename(pdf_path),
                file_path=pdf_path,
                file_size=file_size,
                mime_type="application/pdf",
                status="UPLOADED",
                knowledge_base="BCCL_Rules",
                uploaded_by=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

        print(f"Processing ingestion pipeline for Doc ID {doc.id} ({doc.title}) into knowledge_base='BCCL_Rules'...")
        pipeline = IngestionPipeline(db)
        processed_doc = pipeline.process_document(doc.id)
        
        total_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == processed_doc.id).count()
        print(f"Ingestion successful! Processed {processed_doc.total_pages} pages into {total_chunks} chunks.")
        
        # Verify isolation
        cda_count = db.query(DocumentChunk).filter(DocumentChunk.knowledge_base == "CDA_Rules").count()
        bccl_count = db.query(DocumentChunk).filter(DocumentChunk.knowledge_base == "BCCL_Rules").count()
        print(f"Knowledge Base Isolation Verified: CDA_Rules chunks = {cda_count}, BCCL_Rules chunks = {bccl_count}")
        return processed_doc.id
    finally:
        db.close()

if __name__ == "__main__":
    ingest_bccl_rules()
