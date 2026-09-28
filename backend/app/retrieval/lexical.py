import math
import re
from typing import List, Tuple, Dict, Optional
from collections import Counter
from sqlalchemy.orm import Session
from backend.app.models.chunk import DocumentChunk
from backend.app.models.document import Document

class BM25Retriever:
    """
    Authentic Okapi BM25 Lexical Retrieval Engine.
    Implements standard BM25 formula:
    score(D, Q) = sum_{q in Q} IDF(q) * (f(q, D) * (k1 + 1)) / (f(q, D) + k1 * (1 - b + b * (|D| / avgdl)))
    with k1=1.5, b=0.75.
    """
    def __init__(self, db: Session, k1: float = 1.5, b: float = 0.75):
        self.db = db
        self.k1 = k1
        self.b = b

    def _tokenize(self, text: str) -> List[str]:
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return [t for t in cleaned.split() if len(t) > 1]

    def search(
        self,
        query: str,
        top_k: int = 10,
        document_id: Optional[int] = None,
        knowledge_base: Optional[str] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        chunk_query = self.db.query(DocumentChunk).join(Document, DocumentChunk.document_id == Document.id).filter(Document.status == "READY")
        if document_id:
            chunk_query = chunk_query.filter(DocumentChunk.document_id == document_id)
        if knowledge_base and knowledge_base.lower() != "all":
            chunk_query = chunk_query.filter(Document.knowledge_base == knowledge_base)

        chunks = chunk_query.all()
        if not chunks:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # Build corpus statistics for BM25
        doc_tokens_list: List[List[str]] = []
        doc_lengths: List[int] = []
        doc_freqs: Dict[str, int] = Counter()

        for c in chunks:
            # Include rule number and section title in text tokens
            searchable_text = f"{c.rule_number or ''} {c.section_title or ''} {c.content}"
            tokens = self._tokenize(searchable_text)
            doc_tokens_list.append(tokens)
            doc_lengths.append(len(tokens))
            
            unique_tokens = set(tokens)
            for t in unique_tokens:
                doc_freqs[t] += 1

        N = len(chunks)
        avgdl = sum(doc_lengths) / max(N, 1)

        # Calculate BM25 scores
        scored_chunks: List[Tuple[DocumentChunk, float]] = []

        for i, (chunk, tokens, doc_len) in enumerate(zip(chunks, doc_tokens_list, doc_lengths)):
            token_counts = Counter(tokens)
            score = 0.0

            for q in query_tokens:
                if q in token_counts:
                    f = token_counts[q]
                    df = doc_freqs.get(q, 0)
                    # Standard Robertson-Spärck Jones IDF
                    idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
                    
                    numerator = f * (self.k1 + 1.0)
                    denominator = f + self.k1 * (1.0 - self.b + self.b * (doc_len / max(avgdl, 1.0)))
                    score += idf * (numerator / denominator)

            # Extra weight if query mentions exact rule number and chunk matches it
            if chunk.rule_number and any(q in chunk.rule_number.lower() for q in query_tokens):
                score += 3.0

            if score > 0:
                scored_chunks.append((chunk, score))

        # Normalize BM25 scores between 0 and 1
        if scored_chunks:
            max_score = max(s[1] for s in scored_chunks)
            if max_score > 0:
                scored_chunks = [(c, s / max_score) for c, s in scored_chunks]

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]
