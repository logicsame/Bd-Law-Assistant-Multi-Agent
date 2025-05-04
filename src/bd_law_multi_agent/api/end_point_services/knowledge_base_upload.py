from typing import Optional
from bd_law_multi_agent.services.mistral_ocr import MistralOCRTextExtractor
from bd_law_multi_agent.services.vector_store import DocumentVectorDatabase
from bd_law_multi_agent.core.config import config
import os

ocr_extractor = MistralOCRTextExtractor()

vector_db = DocumentVectorDatabase(
    persist_directory=config.VECTOR_DB_PATH,
    allow_dangerous_deserialization=True)

async def process_document(
    file_path: str,
    source_type: str,
    source_path: str,
    document_id: str,
    description: Optional[str] = None
):
    """Background task to process a document and add it to the vector DB"""
    try:
        # Extract text using OCR
        text = ocr_extractor.extract_text_from_file(file_path)
        
        # Add to vector database
        vector_db.add_document(
            text=text,
            document_id=document_id,
            source_type=source_type,
            source_path=source_path
        )
        
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        print(f"Error processing document: {str(e)}")

async def process_url(
    url: str,
    source_type: str,
    document_id: str,
    description: Optional[str] = None
):
    """Background task to process a URL and add it to the vector DB"""
    try:
        # Extract text using OCR
        text = ocr_extractor.extract_text_from_url(url)
        
        # Add to vector database
        vector_db.add_document(
            text=text,
            document_id=document_id,
            source_type=source_type,
            source_path=url
        )
        
    except Exception as e:
        print(f"Error processing URL: {str(e)}")