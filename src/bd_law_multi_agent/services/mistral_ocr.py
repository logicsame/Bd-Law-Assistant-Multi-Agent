import os
import base64
from io import BytesIO
from mistralai import Mistral
from PIL import Image
from pathlib import Path
from typing import Dict, Optional, Any
from dotenv import load_dotenv
from bd_law_multi_agent.core.config import config

load_dotenv()

class MistralOCRTextExtractor:
    """
    A class to extract text from documents and images using Mistral AI's OCR capabilities.
    Simplified to focus only on text extraction.
    """
    
    VALID_DOCUMENT_EXTENSIONS = {".pdf"}
    VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the MistralOCRTextExtractor client.
        
        Args:
            api_key: Mistral API key. If None, tries to get from environment variable.
        """
        self.api_key = config.MISTRAL_API_KEY
        self.client = Mistral(api_key=self.api_key)
    
    def upload_pdf(self, content: bytes, filename: str) -> str:
        """
        Upload a PDF file to Mistral.
        
        Args:
            content: PDF file content as bytes
            filename: Name of the file
            
        Returns:
            Signed URL for the uploaded file
        """
        uploaded_file = self.client.files.upload(
            file={"file_name": filename, "content": content},
            purpose="ocr",
        )
        signed_url = self.client.files.get_signed_url(file_id=uploaded_file.id)
        return signed_url.url
    
    def process_ocr(self, document_source: Dict[str, str]) -> Any:
        """
        Process OCR on a document.
        
        Args:
            document_source: Dictionary containing document source information
            
        Returns:
            OCR processing result
        """
        return self.client.ocr.process(
            model=config.Mistral_LLM_MODEL,
            document=document_source,
            include_image_base64=False  
        )
    
    def extract_text_from_url(self, url: str) -> str:
        """
        Extract text from a document or image URL.
        
        Args:
            url: URL of the document or image
            
        Returns:
            Extracted text
        """
        url_lower = url.lower()
        if any(url_lower.endswith(ext) for ext in self.VALID_IMAGE_EXTENSIONS):
            document_source = {"type": "image_url", "image_url": url.strip()}
        else:
            document_source = {"type": "document_url", "document_url": url.strip()}
            
        return self._extract_text_from_source(document_source)

    def extract_text_from_file(self, file_path: str) -> str:
        """
        Extract text from a local file.
        
        Args:
            file_path: Path to the local file
            
        Returns:
            Extracted text
        """
        file_name = file_path.lower()
        file_extension = os.path.splitext(file_name)[1]
        
        if file_extension in self.VALID_DOCUMENT_EXTENSIONS:
            with open(file_path, "rb") as f:
                content = f.read()
            signed_url = self.upload_pdf(content, os.path.basename(file_name))
            document_source = {"type": "document_url", "document_url": signed_url}
        elif file_extension in self.VALID_IMAGE_EXTENSIONS:
            img = Image.open(file_path)
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            document_source = {"type": "image_url", "image_url": f"data:image/png;base64,{img_str}"}
        else:
            raise ValueError(f"Unsupported file type. Supported types: {', '.join(self.VALID_DOCUMENT_EXTENSIONS | self.VALID_IMAGE_EXTENSIONS)}")
            
        return self._extract_text_from_source(document_source)
    
    def extract_text_from_image_bytes(self, image_bytes: bytes) -> str:
        """
        Extract text from image bytes.
        
        Args:
            image_bytes: Image content as bytes
            
        Returns:
            Extracted text
        """
        img = Image.open(BytesIO(image_bytes))
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        document_source = {"type": "image_url", "image_url": f"data:image/png;base64,{img_str}"}
        
        return self._extract_text_from_source(document_source)
    
    def _extract_text_from_source(self, document_source: Dict[str, str]) -> str:
        """
        Internal method to process document source and extract text.
        
        Args:
            document_source: Dictionary containing document source information
            
        Returns:
            Extracted text
        """
        try:
            ocr_response = self.process_ocr(document_source)
        except Exception as e:
            raise RuntimeError(f"Error processing OCR: {str(e)}")

        text = "\n\n".join(page.markdown for page in ocr_response.pages)
        return text.strip()


# if __name__ == "__main__":
# #     # Example usage
#     extractor = MistralOCRTextExtractor()
    
# #     # Extract text from a URL
#     text = extractor.extract_text_from_url("https://arxiv.org/pdf/2501.12948")
#     print(f"Extracted {len(text.split())} words")
#     print(text[:500] + "...")  # Print first 500 characters
    
# #     # Extract text from a local file
# #     # text = extractor.extract_text_from_file("document.pdf")
# #     # print(f"Extracted {len(text.split())} words")