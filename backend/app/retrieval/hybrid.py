from typing import List, Tuple, Dict, Optional
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.chunk import DocumentChunk
from backend.app.retrieval.semantic import SemanticRetriever
from backend.app.retrieval.lexical import BM25Retriever
from backend.app.retrieval.reranker import Reranker
from backend.app.providers.embedding_provider import EmbeddingProviderFactory

class HybridRetriever:
    def __init__(self, db: Session):
        self.db = db
        self.semantic_retriever = SemanticRetriever(db)
        self.bm25_retriever = BM25Retriever(db)
        self.reranker = Reranker()
        self.dense_weight = settings.DENSE_SEARCH_WEIGHT
        self.sparse_weight = settings.SPARSE_SEARCH_WEIGHT

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        document_id: Optional[int] = None,
        use_rrf: bool = True
    ) -> List[Tuple[DocumentChunk, float]]:
        k = top_k or settings.RETRIEVAL_TOP_K
        pool_size = max(k * 2, settings.RERANKER_TOP_N)

        dense_results = self.semantic_retriever.search(query, top_k=pool_size, document_id=document_id)
        sparse_results = self.bm25_retriever.search(query, top_k=pool_size, document_id=document_id)

        # Merge candidate pools
        chunk_map: Dict[int, DocumentChunk] = {}
        dense_ranks: Dict[int, int] = {}
        sparse_ranks: Dict[int, int] = {}
        dense_scores: Dict[int, float] = {}
        sparse_scores: Dict[int, float] = {}

        for rank, (chunk, score) in enumerate(dense_results):
            chunk_map[chunk.id] = chunk
            dense_ranks[chunk.id] = rank + 1
            dense_scores[chunk.id] = score

        for rank, (chunk, score) in enumerate(sparse_results):
            chunk_map[chunk.id] = chunk
            sparse_ranks[chunk.id] = rank + 1
            sparse_scores[chunk.id] = score

        combined_scores: Dict[int, float] = {}
        rrf_k = 60.0

        for chunk_id, chunk in chunk_map.items():
            if use_rrf:
                # Reciprocal Rank Fusion
                rrf_dense = (self.dense_weight / (rrf_k + dense_ranks[chunk_id])) if chunk_id in dense_ranks else 0.0
                rrf_sparse = (self.sparse_weight / (rrf_k + sparse_ranks[chunk_id])) if chunk_id in sparse_ranks else 0.0
                combined_score = (rrf_dense + rrf_sparse) * 60.0  # scaled to 0-1 approx range
            else:
                # Weighted score combination
                s_dense = dense_scores.get(chunk_id, 0.0)
                s_sparse = sparse_scores.get(chunk_id, 0.0)
                combined_score = self.dense_weight * s_dense + self.sparse_weight * s_sparse

            combined_scores[chunk_id] = combined_score

        # Initial sorted candidates
        candidates = [(chunk_map[c_id], score) for c_id, score in combined_scores.items()]
        candidates.sort(key=lambda x: x[1], reverse=True)

        # Pass top candidates through Reranker
        reranked = self.reranker.rerank(query, candidates[:pool_size])

        logger.info(f"Hybrid retrieval for query '{query[:40]}...': found {len(reranked)} candidates, returning top {k}")
        return reranked[:k]
