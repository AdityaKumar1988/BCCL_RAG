import os
import fitz
import pytest
from backend.app.ingestion.pdf_parser import PDFParser
from backend.app.providers.ocr_provider import TesseractOCRProvider

def test_ocr_extraction_on_scanned_pdf():
    scanned_pdf_path = os.path.join("data", "raw", "BCCL_Office_Order_Scanned.pdf")
    if not os.path.exists(scanned_pdf_path):
        pytest.skip("Scanned sample PDF not found")

    parser = PDFParser(ocr_provider=TesseractOCRProvider(), min_char_threshold=40)
    pages, is_scanned = parser.parse_pdf(scanned_pdf_path)

    assert len(pages) == 1
    assert pages[0].is_scanned is True
    assert is_scanned is True
    # Verify OCR extracted keywords from the scanned image
    text_lower = pages[0].text.lower()
    assert any(k in text_lower for k in ["bharat", "coking", "coal", "systems", "circular", "rule"])
