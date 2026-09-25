import pytest
from backend.app.core.database import SessionLocal
from backend.app.rag.generator import RAGGenerator

def test_rag_generation_grounding_and_citations():
    db = SessionLocal()
    try:
        gen = RAGGenerator(db)
        
        # Test TC-01: Suspension
        ans1, cit1, abstain1, _, _ = gen.generate_answer("What are the rules for suspension?")
        assert abstain1 is False
        assert "50%" in ans1 or "Subsistence" in ans1 or "Suspension" in ans1
        assert len(cit1) > 0
        assert cit1[0].document_name != ""
        assert cit1[0].page_number > 0

        # Test TC-02: Major Penalties
        ans2, cit2, abstain2, _, _ = gen.generate_answer("Explain major penalties.")
        assert abstain2 is False
        assert "Rule 27" in ans2 or "Major Penalties" in ans2
        assert any("reduction" in ans2.lower() or "dismissal" in ans2.lower() for ans2_part in [ans2])
        assert len(cit2) > 0

        # Test TC-03: Misconduct
        ans3, cit3, abstain3, _, _ = gen.generate_answer("What constitutes misconduct?")
        assert abstain3 is False
        assert "Rule 5" in ans3 or "Misconduct" in ans3
        assert len(cit3) > 0

        # Test TC-04: Appeals
        ans4, cit4, abstain4, _, _ = gen.generate_answer("Can an employee appeal a penalty?")
        assert abstain4 is False
        assert "45" in ans4 or "Appellate" in ans4 or "Appeal" in ans4
        assert len(cit4) > 0
    finally:
        db.close()
