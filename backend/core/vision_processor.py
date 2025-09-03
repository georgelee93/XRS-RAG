"""
Vision Processor Module using OpenAI Vision API
Handles text extraction from images and scanned PDFs using GPT-4 Vision
"""

import os
import logging
import base64
from typing import Optional, List
import tempfile
from pathlib import Path
from io import BytesIO

from openai import AsyncOpenAI
from PIL import Image

try:
    from pdf2image import convert_from_path
    PDF_TO_IMAGE_AVAILABLE = True
except ImportError:
    PDF_TO_IMAGE_AVAILABLE = False
    print("pdf2image not available. Install pdf2image for PDF processing support.")

logger = logging.getLogger(__name__)


class VisionProcessor:
    """Process images and scanned documents using OpenAI Vision API"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Get API key from config
        if not api_key:
            from core.config import get_settings
            settings = get_settings()
            api_key = settings.openai_api_key
        
        self.client = AsyncOpenAI(api_key=api_key)
        self.pdf_to_image_available = PDF_TO_IMAGE_AVAILABLE
    
    async def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from image using OpenAI Vision API"""
        try:
            # Read and encode image
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Call OpenAI Vision API
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",  # Using the more cost-effective vision model
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please extract all text from this image. If it's a document, preserve the structure. If it's in Korean, keep the Korean text. Return only the extracted text, no explanations."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000
            )
            
            extracted_text = response.choices[0].message.content
            logger.info(f"Successfully extracted text from image using Vision API")
            return extracted_text
            
        except Exception as e:
            logger.error(f"Vision API error: {str(e)}")
            return ""
    
    async def extract_text_from_pdf(self, pdf_path: str, max_pages: int = 5) -> str:
        """Extract text from scanned PDF using Vision API"""
        if not self.pdf_to_image_available:
            logger.warning("pdf2image not available for PDF processing")
            return ""
        
        try:
            # Convert PDF pages to images
            images = convert_from_path(pdf_path, dpi=200, first_page=1, last_page=max_pages)
            
            all_text = []
            
            for i, image in enumerate(images):
                logger.info(f"Processing page {i+1}/{len(images)} with Vision API...")
                
                # Convert PIL Image to bytes
                img_byte_arr = BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                # Encode to base64
                base64_image = base64.b64encode(img_byte_arr).decode('utf-8')
                
                # Call Vision API for each page
                response = await self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"This is page {i+1} of a document. Please extract all text from this page. Preserve the structure and formatting. If it's in Korean, keep the Korean text. Return only the extracted text."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=4000
                )
                
                page_text = response.choices[0].message.content
                all_text.append(f"\n--- Page {i+1} ---\n{page_text}")
            
            return "\n".join(all_text)
            
        except Exception as e:
            logger.error(f"PDF Vision processing error: {str(e)}")
            return ""
    
    async def process_document(self, file_path: str) -> str:
        """Process any document type and extract text using Vision API"""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            # For PDF, check if it's text-based first
            import PyPDF2
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages[:3]:
                        text += page.extract_text()
                    
                    # If we got substantial text, it's not a scanned PDF
                    if len(text.strip()) > 100:
                        return text
            except:
                pass
            
            # It's likely a scanned PDF, use Vision API
            logger.info("PDF appears to be scanned, using Vision API...")
            return await self.extract_text_from_pdf(file_path)
            
        elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            return await self.extract_text_from_image(file_path)
        else:
            logger.warning(f"Unsupported file type for Vision processing: {file_ext}")
            return ""


# Singleton instance
_vision_processor = None

def get_vision_processor() -> VisionProcessor:
    """Get or create vision processor instance"""
    global _vision_processor
    if _vision_processor is None:
        _vision_processor = VisionProcessor()
    return _vision_processor