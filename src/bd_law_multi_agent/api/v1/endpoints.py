import os
import tempfile 
import uuid
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks, Depends
import aiofiles
from sqlalchemy.orm import Session
from datetime import datetime
from sqlalchemy.orm import joinedload

from bd_law_multi_agent.utils.common import get_file_type, get_url_type
from bd_law_multi_agent.schemas.schemas import DocumentResponse, SearchQuery, SearchResult
from bd_law_multi_agent.schemas.schemas import User
from bd_law_multi_agent.services.mistral_ocr import MistralOCRTextExtractor
from bd_law_multi_agent.services.vector_store import DocumentVectorDatabase
from bd_law_multi_agent.core.config import config
from bd_law_multi_agent.database.database import get_db
from bd_law_multi_agent.core.security import get_current_active_user
from bd_law_multi_agent.api.background_task.knowledge_base_upload import process_document, process_url
from bd_law_multi_agent.models.document_model import Document, DocumentChunk

app = APIRouter(tags=["documents"])

ocr_extractor = MistralOCRTextExtractor()

vector_db = DocumentVectorDatabase(
    persist_directory=config.VECTOR_DB_PATH,
    allow_dangerous_deserialization=True  
)

@app.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload a document (PDF or image) or process a URL"""
    try:
        if not file and not url:
            raise HTTPException(status_code=400, detail="Either file or URL must be provided")
        
        document_id = str(uuid.uuid4())
        source_type = None
        file_path = None

        # Create base document record
        document = Document(
            id=document_id,
            user_id=current_user.id,
            description=description,
            created_at=datetime.utcnow(),
            text_preview="Processing..."  # Default preview text
        )

        if file:
            try:
                source_type = get_file_type(file.filename)
                document.source_type = source_type
                document.source_path = file.filename
                
                # Save temporary file
                temp_dir = tempfile.gettempdir()
                file_path = os.path.join(temp_dir, f"{document_id}_{file.filename}")
                async with aiofiles.open(file_path, 'wb') as out_file:
                    content = await file.read()
                    await out_file.write(content)
                
                # Extract preview text
                preview_text = ocr_extractor.extract_text_from_file(file_path)
                document.text_preview = preview_text[:200] + "..." if len(preview_text) > 200 else preview_text

            except Exception as e:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                raise HTTPException(status_code=422, detail=f"File processing failed: {str(e)}")

        else:  # URL processing
            try:
                source_type = get_url_type(url)
                document.source_type = source_type
                document.source_path = url
                
                # Extract preview text
                preview_text = ocr_extractor.extract_text_from_url(url)
                document.text_preview = preview_text[:200] + "..." if len(preview_text) > 200 else preview_text

            except Exception as e:
                raise HTTPException(status_code=422, detail=f"URL processing failed: {str(e)}")

        # Commit base document
        db.add(document)
        db.commit()
        db.refresh(document)

        # Add background processing
        if file:
            background_tasks.add_task(
                process_document,
                file_path=file_path,
                document_id=document_id,
                user_id=current_user.id,
                description=description
            )
        else:
                background_tasks.add_task(
                process_url,
                url=url,
                source_type=source_type,  
                document_id=document_id,
                user_id=current_user.id,
                description=description
            )

        # Return document with owner info
        return db.query(Document)\
            .options(joinedload(Document.owner))\
            .filter(Document.id == document_id)\
            .first()

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.post("/search", response_model=list[SearchResult])
async def search_documents(
    query: SearchQuery,
    current_user: User = Depends(get_current_active_user)
):
    """Search documents in vector store"""
    results = vector_db.search(query.query, query.top_k if query.top_k else None)
    return results


@app.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a document from both stores"""
    # Delete from SQLite
    db_document = db.query(Document).filter(Document.id == document_id).first()
    if not db_document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    db.delete(db_document)
    db.commit()
    
    # Delete from vector store
    success = vector_db.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete from vector store")
    
    return {"status": "success", "message": f"Document {document_id} deleted"}


@app.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get document with all chunks"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
    
    return {
        **document.__dict__,
        "chunks": chunks,
        "owner": document.owner
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}