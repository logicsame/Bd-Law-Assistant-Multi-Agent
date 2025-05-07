from fastapi import APIRouter, HTTPException, BackgroundTasks
import traceback
from bd_law_multi_agent.core.security import get_current_active_user
import os
import tempfile
import aiofiles
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
from bd_law_multi_agent.schemas.schemas import User
from fastapi import Depends
from sqlalchemy.orm import Session
from bd_law_multi_agent.database.database import get_db, get_analysis_db, SessionLocal

router = APIRouter()

@router.post("/analyze", summary="Analyze legal case from PDF", response_model=AnalysisResponse)
async def analyze_case(
    file: UploadFile = File(..., description="PDF file to analyze"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    req: Request = None,
    current_user: User = Depends(get_current_active_user)
):
    """Perform comprehensive legal analysis using LangGraph workflow with PDF input"""
    try:
        # Verify file type
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        # Read the PDF bytes and save to temp file
        pdf_bytes = await file.read()
        temp_file_path = None
        
        # Create a temporary file to save the PDF bytes
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{file.filename}")
        
        async with aiofiles.open(temp_file_path, 'wb') as out_file:
            await out_file.write(pdf_bytes)
        
        # Create an instance of MistralOCRTextExtractor
        extractor = MistralOCRTextExtractor()
        
        # Extract text using the instance method
        extracted_text = extractor.extract_text_from_file(temp_file_path)
            
        if not extracted_text.strip():
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            raise HTTPException(status_code=400, detail="No text could be extracted from the PDF")

        # Generate a unique ID for this analysis
        analysis_id = str(uuid.uuid4())

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
        
        # Add background task for processing the analysis
        background_tasks.add_task(
            process_analysis,
            temp_file_path=temp_file_path,
            analysis_id=analysis_id,
            user_id=current_user.id,
            file_name=file.filename,
            extracted_text=extracted_text,
            analysis_result=final_state["analysis"],
            classification=final_state["classification"]
        )
        
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

async def process_analysis(
    temp_file_path: str,
    analysis_id: str,
    user_id: str,
    file_name: str,
    extracted_text: str,
    analysis_result: str,
    classification: dict
):
    """Background task to process analysis results and store them"""
    db = next(get_analysis_db())
    try:
        # Create AnalysisVectorDB instance
        analysis_db = AnalysisVectorDB()
        
        # Create raw case document
        raw_case_doc = Document(
            page_content=extracted_text,
            metadata={
                "source": file_name,
                "source_path": file_name,
                "document_type": "RawCase",
                "created_at": str(datetime.now()),
                "file_source": file_name,
                "user_id": user_id,
                "unique_id": analysis_id,
                "analysis_result": analysis_result,
                "classification": classification
            }
        )

        # Check if document already exists
        existing_doc = db.query(AnalysisDocument)\
            .filter(AnalysisDocument.source_path == file_name)\
            .first()

        if not existing_doc:
            # Add to vector database
            analysis_db.add_documents([raw_case_doc])
            logger.info(f"Added new analysis document with ID: {analysis_id}")
        else:
            # Update existing document
            analysis_db.update_document(
                source_hash=file_name,
                metadata={
                    "last_accessed": str(datetime.now()),
                    "analysis_result": analysis_result
                    # Removed 'classification' that was causing the error
                }
            )
            logger.info(f"Updated existing analysis document for: {file_name}")

    except Exception as e:
        logger.error(f"Background analysis processing error: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        db.close()