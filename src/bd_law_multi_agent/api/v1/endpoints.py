import os
import tempfile 
import uuid
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
import aiofiles
from bd_law_multi_agent.utils.common import get_file_type, get_url_type
from bd_law_multi_agent.schemas.schemas import SearchQuery, DocumentResponse, SearchResult
from bd_law_multi_agent.services.mistral_ocr import MistralOCRTextExtractor
from bd_law_multi_agent.services.vector_store import DocumentVectorDatabase
from bd_law_multi_agent.core.config import config
from bd_law_multi_agent.api.end_point_services.knowledge_base_upload import process_document, process_url

app = FastAPI(title="Bd Law Multi Agent API", version="1.0.0")

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
    description: Optional[str] = Form(None)
):
    """Upload a document (PDF or image) or process a URL"""
    try:
        if not file and not url:
            raise HTTPException(status_code=400, detail="Either file or URL must be provided")
        
        document_id = str(uuid.uuid4())
        
        if file:
            try:
                source_type = get_file_type(file.filename)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, f"{document_id}_{file.filename}")
            
            try:
                async with aiofiles.open(file_path, 'wb') as out_file:
                    content = await file.read()
                    await out_file.write(content)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"File write error: {str(e)}")
            
            try:
                preview_text = ocr_extractor.extract_text_from_file(file_path)
                text_preview = preview_text[:200] + "..." if len(preview_text) > 200 else preview_text
            except Exception as e:
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise HTTPException(status_code=422, detail=f"OCR extraction failed: {str(e)}")
            
            background_tasks.add_task(
                process_document,
                file_path=file_path,
                source_type=source_type,
                source_path=file.filename,
                document_id=document_id,
                description=description
            )
            
            return {
                "document_id": document_id,
                "source_type": source_type,
                "source_path": file.filename,
                "description": description,
                "text_preview": text_preview
            }
            
        else:
            try:
                source_type = get_url_type(url)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            
            try:
                preview_text = ocr_extractor.extract_text_from_url(url)
                text_preview = preview_text[:200] + "..." if len(preview_text) > 200 else preview_text
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"URL content extraction failed: {str(e)}")
            
            background_tasks.add_task(
                process_url,
                url=url,
                source_type=source_type,
                document_id=document_id,
                description=description
            )
            
            return {
                "document_id": document_id,
                "source_type": source_type,
                "source_path": url,
                "description": description,
                "text_preview": text_preview
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}