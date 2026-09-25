import os
import fitz
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from backend.app.core.logging import logger
from backend.app.ingestion.text_cleaner import TextCleaner
from backend.app.providers.ocr_provider import OCRProviderFactory, BaseOCRProvider

@dataclass
class ParsedPage:
    page_number: int
    text: str
    is_scanned: bool
    character_count: int

class PDFParser:
    def __init__(self, ocr_provider: BaseOCRProvider = None, min_char_threshold: int = 40):
        self.ocr_provider = ocr_provider or OCRProviderFactory.get_provider()
        self.min_char_threshold = min_char_threshold

    def parse_pdf(self, file_path: str) -> Tuple[List[ParsedPage], bool]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at {file_path}")

        parsed_pages: List[ParsedPage] = []
        has_scanned_pages = False

        doc = fitz.open(file_path)
        try:
            total_pages = len(doc)
            logger.info(f"Parsing PDF {os.path.basename(file_path)} ({total_pages} pages)")

            for page_idx in range(total_pages):
                page = doc[page_idx]
                page_num = page_idx + 1
                
                # 1. Try native text extraction
                extracted_text = page.get_text()
                cleaned_text = TextCleaner.clean_text(extracted_text)
                
                is_scanned = False
                # If page contains fewer characters than threshold, treat as scanned and run OCR
                if len(cleaned_text) < self.min_char_threshold:
                    logger.info(f"Page {page_num} has only {len(cleaned_text)} chars. Triggering OCR engine...")
                    ocr_text = self.ocr_provider.ocr_pdf_page(page, dpi=300)
                    cleaned_ocr_text = TextCleaner.clean_text(ocr_text)
                    if len(cleaned_ocr_text) > len(cleaned_text):
                        cleaned_text = cleaned_ocr_text
                        is_scanned = True
                        has_scanned_pages = True

                parsed_pages.append(ParsedPage(
                    page_number=page_num,
                    text=cleaned_text,
                    is_scanned=is_scanned,
                    character_count=len(cleaned_text)
                ))

            return parsed_pages, has_scanned_pages
        finally:
            doc.close()
