from typing import Optional
import os
from sqlalchemy.orm import Session
from uuid import uuid4

from bd_law_multi_agent.services.mistral_ocr import MistralOCRTextExtractor
from bd_law_multi_agent.services.vector_store import DocumentVectorDatabase
from bd_law_multi_agent.core.config import config
from bd_law_multi_agent.database.database import get_db, SessionLocal
from bd_law_multi_agent.models.document_model import Document
import logging
import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ocr_extractor = MistralOCRTextExtractor()

vector_db = DocumentVectorDatabase(
    persist_directory=config.VECTOR_DB_PATH,
    allow_dangerous_deserialization=True
)

async def process_document(
    file_path: str,
    document_id: str,
    user_id: str,
    description: Optional[str] = None,
):
    """Background task to process document content"""
    db = SessionLocal()
    try:
        # Get existing document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"Document {document_id} not found")
            return

        # Extract full text
        full_text = ocr_extractor.extract_text_from_file(file_path)
        
        # Update document with full text
        document.full_text = full_text
        db.commit()

        # Add to vector database
        vector_db.add_document(
            text=full_text,
            document_id=document_id,
            source_type=document.source_type,
            source_path=document.source_path,
            description=description,
            db=db
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing document: {str(e)}")
        raise
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        db.close()

async def process_url(
    url: str,
    source_type: str,  # Now receiving this parameter
    document_id: str,
    user_id: str,
    description: Optional[str] = None,
):
    """Background task to process URL and add to both databases"""
    db = SessionLocal()
    try:
        db_document = Document(
            id=document_id,
            source_type=source_type,
            source_path=url,
            description=description,
            user_id=user_id  
        )

        # Extract text using OCR
        text = ocr_extractor.extract_text_from_url(url)
        
        # Add to both vector DB and SQLite chunks
        vector_db.add_document(
            text=text,
            document_id=document_id,
            source_type=source_type,
            source_path=url,
            description=description,
            db=db
        )

    except Exception as e:
        db.rollback()
        print(f"Error processing URL: {str(e)}")
        raise
    finally:
        db.close()