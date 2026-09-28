import json
import numpy as np
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from backend.app.models.chunk import DocumentChunk
from backend.app.models.document import Document
from backend.app.providers.embedding_provider import EmbeddingProviderFactory, BaseEmbeddingProvider

class SemanticRetriever:
    def __init__(self, db: Session, embedding_provider: Optional[BaseEmbeddingProvider] = None):
        self.db = db
        self.embedding_provider = embedding_provider or EmbeddingProviderFactory.get_provider()

    def search(
        self,
        query: str,
        top_k: int = 10,
        document_id: Optional[int] = None,
        knowledge_base: Optional[str] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        query_embedding = np.array(self.embedding_provider.embed_query(query), dtype=np.float32)
        query_norm = np.linalg.norm(query_embedding)
        if query_norm > 0:
            query_embedding = query_embedding / query_norm

        chunk_query = self.db.query(DocumentChunk).join(Document, DocumentChunk.document_id == Document.id).filter(Document.status == "READY")
        if document_id:
            chunk_query = chunk_query.filter(DocumentChunk.document_id == document_id)
        if knowledge_base and knowledge_base.lower() != "all":
            chunk_query = chunk_query.filter(Document.knowledge_base == knowledge_base)

        chunks = chunk_query.all()
        if not chunks:
            return []

        scored_chunks: List[Tuple[DocumentChunk, float]] = []
        for c in chunks:
            if not c.embedding_json:
                continue
            emb_list = json.loads(c.embedding_json)
            c_emb = np.array(emb_list, dtype=np.float32)
            c_norm = np.linalg.norm(c_emb)
            if c_norm > 0:
                c_emb = c_emb / c_norm
            score = float(np.dot(query_embedding, c_emb))
            scored_chunks.append((c, score))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]
