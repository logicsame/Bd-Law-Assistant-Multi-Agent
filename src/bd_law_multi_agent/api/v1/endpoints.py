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

# Combined upload endpoint that handles both files and URLs
@app.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
):
    """Upload a document (PDF or image) or process a URL"""
    try:
        # Check if either file or URL is provided
        if not file and not url:
            raise HTTPException(status_code=400, detail="Either file or URL must be provided")
        
        # Generate a unique ID for the document
        document_id = str(uuid.uuid4())
        
        # Handle file upload
        if file:
            # Determine file type
            try:
                source_type = get_file_type(file.filename)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            
            # Save the uploaded file to temp directory
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, f"{document_id}_{file.filename}")
            
            # Write file to disk with proper error handling
            try:
                async with aiofiles.open(file_path, 'wb') as out_file:
                    content = await file.read()
                    await out_file.write(content)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"File write error: {str(e)}")
            
            # Try to extract a preview of the text first to validate the file
            try:
                preview_text = ocr_extractor.extract_text_from_file(file_path)
                text_preview = preview_text[:200] + "..." if len(preview_text) > 200 else preview_text
            except Exception as e:
                # Clean up the file if OCR extraction fails
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise HTTPException(status_code=422, detail=f"OCR extraction failed: {str(e)}")
            
            # Process the document in the background
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
            
        # Handle URL processing
        else:
            # Determine URL type with error handling
            try:
                source_type = get_url_type(url)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            
            # Extract a small preview of the text to validate the URL
            try:
                preview_text = ocr_extractor.extract_text_from_url(url)
                text_preview = preview_text[:200] + "..." if len(preview_text) > 200 else preview_text
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"URL content extraction failed: {str(e)}")
            
            # Process the URL in the background
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
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# Search endpoint to search for documents
@app.post("/search", response_model=SearchResult)
async def search_documents(query: SearchQuery):
    """Search for documents based on a text query"""
    try:
        # Search the vector database for relevant documents
        results = vector_db.search(
            query=query.query_text,
            limit=query.limit if query.limit else 5
        )
        
        # Format the results
        documents = []
        for doc in results:
            documents.append({
                "document_id": doc.metadata.get("document_id"),
                "source_type": doc.metadata.get("source_type"),
                "source_path": doc.metadata.get("source_path"),
                "score": doc.score,
                "text_preview": doc.text[:200] + "..." if len(doc.text) > 200 else doc.text
            })
        
        return {
            "query": query.query_text,
            "results": documents
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}