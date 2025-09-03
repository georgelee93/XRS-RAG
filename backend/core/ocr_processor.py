"""
OCR Processor Module
Handles text extraction from scanned PDFs and images
"""

import os
import logging
from typing import Optional, List
import tempfile
from pathlib import Path

try:
    import pytesseract
    from PIL import Image
    from pdf2image import convert_from_path
    import PyPDF2
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("OCR libraries not available. Install pytesseract, pdf2image, and Pillow for OCR support.")

logger = logging.getLogger(__name__)


class OCRProcessor:
    """Process scanned documents and images to extract text"""
    
    def __init__(self):
        self.ocr_available = OCR_AVAILABLE
        
        # Configure Tesseract path for Windows
        if os.name == 'nt':  # Windows
            # Common Tesseract installation paths on Windows
            tesseract_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                r"C:\Users\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
            ]
            
            for path in tesseract_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    logger.info(f"Tesseract found at: {path}")
                    break
    
    async def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF, using OCR if necessary"""
        try:
            # First, try to extract text directly (for text-based PDFs)
            text = self._extract_text_pypdf2(pdf_path)
            
            if text and len(text.strip()) > 50:  # If we got meaningful text
                logger.info(f"Extracted text directly from PDF: {pdf_path}")
                return text
            
            # If no text or very little text, try OCR
            if self.ocr_available:
                logger.info(f"PDF appears to be scanned/image-based. Attempting OCR: {pdf_path}")
                text = await self._ocr_pdf(pdf_path)
                return text
            else:
                logger.warning("OCR not available. Cannot extract text from scanned PDF.")
                return ""
                
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return ""
    
    def _extract_text_pypdf2(self, pdf_path: str) -> str:
        """Extract text using PyPDF2 (for text-based PDFs)"""
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)
                
                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            return text
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed: {str(e)}")
            return ""
    
    async def _ocr_pdf(self, pdf_path: str) -> str:
        """Perform OCR on PDF pages"""
        if not self.ocr_available:
            return ""
        
        try:
            # Convert PDF to images
            images = convert_from_path(pdf_path, dpi=300)
            
            text = ""
            for i, image in enumerate(images):
                logger.info(f"Processing page {i+1}/{len(images)} with OCR...")
                
                # Perform OCR on each page
                # Use Korean + English for better recognition
                page_text = pytesseract.image_to_string(image, lang='kor+eng')
                text += f"\n--- Page {i+1} ---\n{page_text}\n"
            
            return text
            
        except Exception as e:
            logger.error(f"OCR processing failed: {str(e)}")
            
            # Check if Tesseract is installed
            if "tesseract is not installed" in str(e).lower():
                logger.error("""
                Tesseract OCR is not installed. Please install it:
                - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
                - Linux: sudo apt-get install tesseract-ocr tesseract-ocr-kor
                - Mac: brew install tesseract tesseract-lang
                """)
            
            return ""
    
    async def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from image file using OCR"""
        if not self.ocr_available:
            logger.warning("OCR not available for image processing")
            return ""
        
        try:
            image = Image.open(image_path)
            # Use Korean + English for better recognition
            text = pytesseract.image_to_string(image, lang='kor+eng')
            return text
        except Exception as e:
            logger.error(f"Image OCR failed: {str(e)}")
            return ""
    
    async def process_document(self, file_path: str) -> str:
        """Process any document type and extract text"""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            return await self.extract_text_from_pdf(file_path)
        elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            return await self.extract_text_from_image(file_path)
        elif file_ext in ['.txt', '.md']:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            logger.warning(f"Unsupported file type: {file_ext}")
            return ""
    
    def is_ocr_available(self) -> bool:
        """Check if OCR is available and configured"""
        if not self.ocr_available:
            return False
        
        try:
            # Test if Tesseract is accessible
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False


# Singleton instance
_ocr_processor = None

def get_ocr_processor() -> OCRProcessor:
    """Get or create OCR processor instance"""
    global _ocr_processor
    if _ocr_processor is None:
        _ocr_processor = OCRProcessor()
    return _ocr_processor