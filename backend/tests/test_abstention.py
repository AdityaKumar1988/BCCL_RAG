import pytest
from backend.app.core.database import SessionLocal
from backend.app.rag.generator import RAGGenerator

def test_abstention_on_unavailable_information():
    db = SessionLocal()
    try:
        gen = RAGGenerator(db)
        
        # Test out-of-scope queries
        unsupported_queries = [
            "What is the policy for leave encashment in overseas branches?",
            "How do I apply for international astronaut training under BCCL?",
            "What is the interest rate for personal cryptocurrency loans?"
        ]

        for q in unsupported_queries:
            ans, cit, abstain, _, _ = gen.generate_answer(q)
            assert abstain is True
            assert "could not find sufficient information" in ans.lower()
            assert len(cit) == 0  # No fake citations!
    finally:
        db.close()
