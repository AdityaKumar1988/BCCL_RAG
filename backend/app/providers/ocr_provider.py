import os
import io
import fitz
from PIL import Image
from abc import ABC, abstractmethod
from typing import List, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger

class BaseOCRProvider(ABC):
    @abstractmethod
    def extract_text_from_image(self, image: Image.Image) -> str:
        pass

    @abstractmethod
    def ocr_pdf_page(self, page: fitz.Page, dpi: int = 300) -> str:
        pass

class TesseractOCRProvider(BaseOCRProvider):
    def __init__(self, tesseract_cmd: Optional[str] = None):
        import pytesseract
        self.pytesseract = pytesseract
        cmd = tesseract_cmd or settings.TESSERACT_CMD
        if os.path.exists(cmd):
            self.pytesseract.pytesseract.tesseract_cmd = cmd
        else:
            logger.warning(f"Tesseract executable not found at {cmd}, OCR will use standard path search.")

    def extract_text_from_image(self, image: Image.Image) -> str:
        try:
            text = self.pytesseract.image_to_string(image, lang="eng")
            return text.strip()
        except Exception as e:
            logger.error(f"Tesseract OCR failed on image: {e}")
            return ""

    def ocr_pdf_page(self, page: fitz.Page, dpi: int = 300) -> str:
        try:
            pix = page.get_pixmap(dpi=dpi)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            return self.extract_text_from_image(img)
        except Exception as e:
            logger.error(f"Failed to rasterize and OCR PDF page {page.number}: {e}")
            return ""

class OCRProviderFactory:
    @staticmethod
    def get_provider() -> BaseOCRProvider:
        return TesseractOCRProvider()
