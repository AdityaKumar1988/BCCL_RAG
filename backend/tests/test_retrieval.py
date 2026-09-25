import pytest
from backend.app.core.database import SessionLocal
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.retrieval.lexical import BM25Retriever
from backend.app.retrieval.semantic import SemanticRetriever

def test_bm25_and_semantic_retrieval():
    db = SessionLocal()
    try:
        bm25 = BM25Retriever(db)
        semantic = SemanticRetriever(db)
        hybrid = HybridRetriever(db)

        # Test BM25 exact rule query
        bm25_res = bm25.search("Rule 26 suspension subsistence allowance", top_k=5)
        assert len(bm25_res) > 0
        assert any("26" in (c[0].rule_number or "") or "suspension" in c[0].content.lower() for c in bm25_res)

        # Test Semantic query
        sem_res = semantic.search("What happens when an employee is temporarily relieved pending inquiry?", top_k=5)
        assert len(sem_res) > 0

        # Test Hybrid Fusion
        hybrid_res = hybrid.retrieve("penalties and dismissal", top_k=5)
        assert len(hybrid_res) > 0
        assert any("penalty" in c[0].content.lower() or "penalties" in c[0].content.lower() for c in hybrid_res)
    finally:
        db.close()
