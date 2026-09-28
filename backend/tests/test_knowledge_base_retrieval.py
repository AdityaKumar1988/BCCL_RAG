import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.chunk import DocumentChunk
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.rag.generator import RAGGenerator

client = TestClient(app)

def get_auth_token(username: str = "user", password: str = "user123") -> str:
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


# ==============================================================================
# TEST A: Selecting CDA_Rules retrieves CDA evidence.
# ==============================================================================
def test_a_selecting_cda_rules_retrieves_cda_evidence():
    db = SessionLocal()
    try:
        retriever = HybridRetriever(db)
        results = retriever.retrieve("rules regarding suspension", knowledge_base="CDA_Rules", top_k=5)
        
        assert len(results) > 0, "Retrieval on CDA_Rules must return candidate chunks."
        # Verify all returned chunks strictly originate from the CDA_Rules corpus
        for chunk, score in results:
            assert chunk.knowledge_base == "CDA_Rules", (
                f"Expected chunk knowledge_base to be 'CDA_Rules', got '{chunk.knowledge_base}'"
            )
            assert chunk.document.knowledge_base == "CDA_Rules"

        # Verify evidence content
        all_text = " ".join([c.content.lower() for c, _ in results])
        assert "suspension" in all_text or "subsistence" in all_text

        # Verify through RAG Generator
        gen = RAGGenerator(db)
        ans, citations, is_abstain, _, _ = gen.generate_answer(
            "What are the rules regarding suspension?",
            knowledge_base="CDA_Rules"
        )
        assert is_abstain is False
        assert len(citations) > 0
        assert all(c.knowledge_base == "CDA_Rules" for c in citations)
    finally:
        db.close()


# ==============================================================================
# TEST B: Selecting BCCL_Rules retrieves BCCL_Rules evidence.
# ==============================================================================
def test_b_selecting_bccl_rules_retrieves_bccl_rules_evidence():
    db = SessionLocal()
    try:
        retriever = HybridRetriever(db)
        results = retriever.retrieve("rules regarding suspension", knowledge_base="BCCL_Rules", top_k=5)
        
        assert len(results) > 0, "Retrieval on BCCL_Rules must return candidate chunks."
        # Verify all returned chunks strictly originate from the BCCL_Rules corpus
        for chunk, score in results:
            assert chunk.knowledge_base == "BCCL_Rules", (
                f"Expected chunk knowledge_base to be 'BCCL_Rules', got '{chunk.knowledge_base}'"
            )
            assert chunk.document.knowledge_base == "BCCL_Rules"

        # Verify evidence content
        all_text = " ".join([c.content.lower() for c, _ in results])
        assert "suspension" in all_text or "subsistence" in all_text or "suspended" in all_text

        # Verify through RAG Generator
        gen = RAGGenerator(db)
        ans, citations, is_abstain, _, _ = gen.generate_answer(
            "What are the rules regarding suspension?",
            knowledge_base="BCCL_Rules"
        )
        assert is_abstain is False
        assert len(citations) > 0
        assert all(c.knowledge_base == "BCCL_Rules" for c in citations)
    finally:
        db.close()


# ==============================================================================
# TEST C: Selecting All Sources can retrieve CDA_Rules evidence.
# ==============================================================================
def test_c_selecting_all_sources_can_retrieve_cda_rules_evidence():
    db = SessionLocal()
    try:
        retriever = HybridRetriever(db)
        # Query matching specific CDA Rules provisions
        results = retriever.retrieve("Rule 26 suspension subsistence allowance", knowledge_base="all", top_k=10)
        
        assert len(results) > 0, "Retrieval across all sources should return results."
        cda_chunks = [c for c, _ in results if c.knowledge_base == "CDA_Rules"]
        assert len(cda_chunks) > 0, "Unified search across 'all' sources must be able to retrieve CDA_Rules evidence."
        
        # Verify chunk properties
        cda_chunk = cda_chunks[0]
        assert cda_chunk.knowledge_base == "CDA_Rules"
        assert cda_chunk.document.knowledge_base == "CDA_Rules"
    finally:
        db.close()


# ==============================================================================
# TEST D: Selecting All Sources can retrieve BCCL_Rules evidence.
# ==============================================================================
def test_d_selecting_all_sources_can_retrieve_bccl_rules_evidence():
    db = SessionLocal()
    try:
        retriever = HybridRetriever(db)
        # Query matching specific BCCL_Rules amended provisions
        results = retriever.retrieve("amended rules July 2006 Rule 20 suspension", knowledge_base="all", top_k=10)
        
        assert len(results) > 0, "Retrieval across all sources should return results."
        bccl_chunks = [c for c, _ in results if c.knowledge_base == "BCCL_Rules"]
        assert len(bccl_chunks) > 0, "Unified search across 'all' sources must be able to retrieve BCCL_Rules evidence."
        
        # Verify chunk properties
        bccl_chunk = bccl_chunks[0]
        assert bccl_chunk.knowledge_base == "BCCL_Rules"
        assert bccl_chunk.document.knowledge_base == "BCCL_Rules"
    finally:
        db.close()


# ==============================================================================
# TEST E: All Sources can return evidence from both corpora when appropriate.
# ==============================================================================
def test_e_all_sources_can_return_evidence_from_both_corpora():
    db = SessionLocal()
    try:
        retriever = HybridRetriever(db)
        # Broad disciplinary query applicable across both CDA_Rules and BCCL_Rules
        results = retriever.retrieve("disciplinary action and penalties", knowledge_base="all", top_k=10)
        
        assert len(results) > 0, "Broad query across all sources should return results."
        retrieved_kbs = set(c.knowledge_base for c, _ in results)
        
        # Verify both knowledge bases are actively represented in the multi-corpus retrieval result
        assert "CDA_Rules" in retrieved_kbs, f"CDA_Rules should be present in multi-corpus results, got: {retrieved_kbs}"
        assert "BCCL_Rules" in retrieved_kbs, f"BCCL_Rules should be present in multi-corpus results, got: {retrieved_kbs}"
        assert len(retrieved_kbs) >= 2, "Results must contain evidence from both corpora."

        # Verify via Chat API endpoint
        token = get_auth_token()
        resp = client.post(
            "/api/chat",
            json={
                "message": "Explain penalties under the rules.",
                "knowledge_base": "all"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_abstention"] is False
        assert len(data["citations"]) > 0
    finally:
        db.close()


# ==============================================================================
# TEST F: Selecting CDA_Rules does NOT return BCCL_Rules-only evidence.
# ==============================================================================
def test_f_selecting_cda_rules_does_not_return_bccl_rules_evidence():
    db = SessionLocal()
    try:
        retriever = HybridRetriever(db)
        
        # 1. Broad query with CDA_Rules selected
        results = retriever.retrieve("subsistence allowance during suspension", knowledge_base="CDA_Rules", top_k=10)
        assert len(results) > 0
        for chunk, _ in results:
            assert chunk.knowledge_base != "BCCL_Rules", (
                f"Leak detected: Chunk {chunk.id} from 'BCCL_Rules' was returned when knowledge_base='CDA_Rules' was selected!"
            )
            assert chunk.knowledge_base == "CDA_Rules"

        # 2. Query targeting amended BCCL rules (phrased with BCCL 2006 terms)
        bccl_specific_query = "amended upto July 2006 10052018 ocr"
        results_isolated = retriever.retrieve(bccl_specific_query, knowledge_base="CDA_Rules", top_k=10)
        # Must never return any BCCL_Rules chunk even if query matches BCCL document metadata
        for chunk, _ in results_isolated:
            assert chunk.knowledge_base == "CDA_Rules"
            assert chunk.knowledge_base != "BCCL_Rules"

        # 3. Verify via API endpoint with knowledge_base="CDA_Rules"
        token = get_auth_token()
        resp = client.post(
            "/api/chat",
            json={
                "message": "What are the rules regarding suspension?",
                "knowledge_base": "CDA_Rules"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        for cit in data.get("citations", []):
            assert cit["knowledge_base"] == "CDA_Rules"
            assert cit["knowledge_base"] != "BCCL_Rules"
    finally:
        db.close()


# ==============================================================================
# TEST G: Selecting BCCL_Rules does NOT return CDA_Rules evidence.
# ==============================================================================
def test_g_selecting_bccl_rules_does_not_return_cda_rules_evidence():
    db = SessionLocal()
    try:
        retriever = HybridRetriever(db)
        
        # 1. Broad query with BCCL_Rules selected
        results = retriever.retrieve("subsistence allowance during suspension", knowledge_base="BCCL_Rules", top_k=10)
        assert len(results) > 0
        for chunk, _ in results:
            assert chunk.knowledge_base != "CDA_Rules", (
                f"Leak detected: Chunk {chunk.id} from 'CDA_Rules' was returned when knowledge_base='BCCL_Rules' was selected!"
            )
            assert chunk.knowledge_base == "BCCL_Rules"

        # 2. Query targeting baseline CDA rule numbers
        cda_specific_query = "Rule 26: Suspension Conduct Discipline and Appeal Rules 1978"
        results_isolated = retriever.retrieve(cda_specific_query, knowledge_base="BCCL_Rules", top_k=10)
        # Must never return any CDA_Rules chunk
        for chunk, _ in results_isolated:
            assert chunk.knowledge_base == "BCCL_Rules"
            assert chunk.knowledge_base != "CDA_Rules"

        # 3. Verify via API endpoint with knowledge_base="BCCL_Rules"
        token = get_auth_token()
        resp = client.post(
            "/api/chat",
            json={
                "message": "What are the rules regarding suspension?",
                "knowledge_base": "BCCL_Rules"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        for cit in data.get("citations", []):
            assert cit["knowledge_base"] == "BCCL_Rules"
            assert cit["knowledge_base"] != "CDA_Rules"
    finally:
        db.close()
