import pytest
from backend.app.ingestion.pdf_parser import ParsedPage
from backend.app.ingestion.chunker import StructureAwareChunker

def test_structure_aware_chunker_rule_preservation():
    sample_text = """CHAPTER II: CONDUCT RULES
Rule 4: General Conduct
(1) Every employee shall maintain integrity.

Rule 5: Misconduct
(1) Theft, fraud, and embezzlement are misconduct.
(2) Taking bribes is strictly prohibited.
"""
    pages = [ParsedPage(page_number=1, text=sample_text, is_scanned=False, character_count=len(sample_text))]
    
    chunker = StructureAwareChunker(target_chunk_size=200, chunk_overlap=30, min_chunk_size=10)
    chunks = chunker.chunk_pages(pages)
    
    assert len(chunks) >= 2
    rule_numbers = [c.rule_number for c in chunks if c.rule_number]
    assert any("Rule 4" in r for r in rule_numbers)
    assert any("Rule 5" in r for r in rule_numbers)
    
    for c in chunks:
        assert c.page_number == 1
        assert len(c.content) > 0
