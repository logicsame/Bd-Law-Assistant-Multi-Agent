from fastapi import APIRouter, HTTPException
import traceback
from bd_law_multi_agent.core.security import get_current_active_user
import os
from bd_law_multi_agent.schemas.analyze_sc import AnalysisRequest, AnalysisResponse, DocumentSource, ClassificationDetail
from bd_law_multi_agent.core.config import config
from bd_law_multi_agent.core.common import logger   
from langchain.callbacks.manager import tracing_v2_enabled
from fastapi import Request
from fastapi import APIRouter, HTTPException, UploadFile, File
from bd_law_multi_agent.services.mistral_ocr import MistralOCRTextExtractor
from bd_law_multi_agent.workflows.analysis_and_argument_workflow import legal_agent, rag_system
from langchain_core.documents import Document
from datetime import datetime 
from bd_law_multi_agent.services.analyze_vector_db import AnalysisVectorDB
import uuid
from bd_law_multi_agent.models.document_model import AnalysisChunk, AnalysisDocument
from bd_law_multi_agent.schemas.schemas import User  # If not already imported
from fastapi import Depends
from sqlalchemy.orm import Session
from bd_law_multi_agent.database.database import get_db,get_analysis_db

router = APIRouter()

@router.post("/analyze", summary="Analyze legal case from PDF", response_model=AnalysisResponse)
async def analyze_case(
    file: UploadFile = File(..., description="PDF file to analyze"),
    req: Request = None,
    current_user: User = Depends(get_current_active_user)
):
    """Perform comprehensive legal analysis using LangGraph workflow with PDF input"""
    try:
        # Verify file type
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        # Read the PDF bytes
        pdf_bytes = await file.read()
        
        # Create a temporary file to save the PDF bytes
        temp_file_path = f"/tmp/{file.filename}"
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(pdf_bytes)
        
        # Create an instance of MistralOCRTextExtractor
        extractor = MistralOCRTextExtractor()
        
        # Extract text using the instance method
        extracted_text = extractor.extract_text_from_file(temp_file_path)
        
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from the PDF")

        # Initialize state for LangGraph with extracted text
        state = {
            "query": extracted_text,  
            "documents": [],
            "classification": {},
            "analysis": "",
            "follow_ups": [],
            "conversation_history": [],
            "current_step": "start"
        }

        # Rest of your function remains unchanged
        final_state = None
        trace_url = None
        
        with tracing_v2_enabled() as session:
            try:
                final_state = legal_agent.invoke(state)
                
                if hasattr(session, 'run_id'):
                    trace_url = f"https://smith.langchain.com/trace/{session.run_id}"
                    logger.info(f"LangSmith trace: {trace_url}")
                
            except Exception as e:
                logger.error(f"Workflow failed: {str(e)}")
                if hasattr(session, 'run_id'):
                    trace_url = f"https://smith.langchain.com/trace/{session.run_id}/errors"
                traceback.print_exc()
                raise

        sources = [
            DocumentSource(
                source=doc.metadata.get("source", "Unknown"),
                page=str(doc.metadata.get("page", "N/A")),
                excerpt=doc.page_content[:config.CITATION_LENGTH]
            )
            for doc in final_state["documents"]
        ]
        
        analysis_db = AnalysisVectorDB()
        db: Session = next(get_analysis_db())  # Use analysis database session

        try:
            raw_case_doc = Document(
                page_content=extracted_text,
                metadata={
                    "source": file.filename,
                    "source_path": file.filename,
                    "document_type": "RawCase",
                    "created_at": str(datetime.now()),
                    "file_source": file.filename,
                    "user_id": current_user.id,
                    "unique_id": str(uuid.uuid4())
                }
            )
    
            existing_doc = db.query(AnalysisDocument)\
                .filter(AnalysisDocument.source_path == file.filename)\
                .first()
    
            if not existing_doc:
                analysis_db.add_documents([raw_case_doc])
            else:
                analysis_db.update_document(
                    source_hash=file.filename,
                    metadata={"last_accessed": str(datetime.now())}
                )
        
        except Exception as e:
            logger.error(f"Analysis DB error: {str(e)}")
        finally:
            db.close()
           
        return {
            "analysis": final_state["analysis"],
            "classification": final_state["classification"],
            "follow_up_questions": final_state["follow_ups"],
            "sources": [source.model_dump() for source in sources],
            "trace_url": trace_url 
        }
        
    except HTTPException as he:
        raise he
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Analysis error: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Legal analysis failed: {str(e)}"
        )