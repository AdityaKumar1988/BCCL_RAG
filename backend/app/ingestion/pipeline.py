import os
import json
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from backend.app.core.logging import logger
from backend.app.models.document import Document
from backend.app.models.chunk import DocumentChunk
from backend.app.models.ingestion import IngestionJob
from backend.app.ingestion.pdf_parser import PDFParser
from backend.app.ingestion.chunker import StructureAwareChunker
from backend.app.providers.embedding_provider import EmbeddingProviderFactory

class IngestionPipeline:
    def __init__(self, db: Session):
        self.db = db
        self.parser = PDFParser()
        self.chunker = StructureAwareChunker()
        self.embedding_provider = EmbeddingProviderFactory.get_provider()

    def process_document(self, document_id: int, job_id: Optional[int] = None) -> Document:
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        job = None
        if job_id:
            job = self.db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
        if not job:
            job = IngestionJob(
                document_id=doc.id,
                status="PROCESSING",
                stage="VALIDATION",
                progress_percentage=10,
                started_at=datetime.now(timezone.utc)
            )
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)

        try:
            # Stage 1: Validation & PDF Text Extraction
            logger.info(f"Starting ingestion pipeline for Document {doc.id} ({doc.filename})")
            doc.status = "PROCESSING"
            job.stage = "TEXT_EXTRACTION"
            job.progress_percentage = 20
            self.db.commit()

            parsed_pages, is_scanned = self.parser.parse_pdf(doc.file_path)
            doc.total_pages = len(parsed_pages)
            doc.is_scanned = is_scanned
            
            if is_scanned:
                doc.status = "OCR_REQUIRED"
                job.stage = "OCR"
                job.progress_percentage = 40
                self.db.commit()

            # Stage 2: Chunking
            doc.status = "CHUNKING"
            job.stage = "CHUNKING"
            job.progress_percentage = 55
            self.db.commit()

            chunks_metadata = self.chunker.chunk_pages(parsed_pages)
            logger.info(f"Generated {len(chunks_metadata)} chunks for Document {doc.id}")

            if not chunks_metadata:
                raise ValueError("No text or structural chunks could be extracted from this document")

            # Remove any old chunks for this document
            self.db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
            self.db.commit()

            # Stage 3: Embedding Generation
            doc.status = "EMBEDDING"
            job.stage = "EMBEDDING"
            job.progress_percentage = 75
            self.db.commit()

            chunk_texts = [c.content for c in chunks_metadata]
            embeddings = self.embedding_provider.embed_documents(chunk_texts)

            # Stage 4: Indexing & Storage
            doc.status = "INDEXING"
            job.stage = "INDEXING"
            job.progress_percentage = 90
            self.db.commit()

            db_chunks = []
            for meta, emb in zip(chunks_metadata, embeddings):
                db_chunk = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=meta.chunk_index,
                    page_number=meta.page_number,
                    rule_number=meta.rule_number,
                    section_title=meta.section_title,
                    content=meta.content,
                    token_count=meta.token_count,
                    embedding_json=json.dumps(emb)
                )
                db_chunks.append(db_chunk)

            self.db.bulk_save_objects(db_chunks)

            # Mark Document & Job as READY/COMPLETED
            doc.status = "READY"
            doc.updated_at = datetime.now(timezone.utc)
            job.status = "COMPLETED"
            job.stage = "INDEXED"
            job.progress_percentage = 100
            job.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(doc)
            logger.info(f"Successfully processed Document {doc.id} with {len(db_chunks)} indexed chunks.")
            return doc

        except Exception as e:
            logger.error(f"Ingestion failed for Document {doc.id}: {e}", exc_info=True)
            doc.status = "FAILED"
            job.status = "FAILED"
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            raise e
