from fastapi import APIRouter, HTTPException,BackgroundTasks
from fastapi import Depends

from bd_law_multi_agent.schemas.argument_sc import ArgumentResponse
import tempfile
import os 
import uuid
import aiofiles
from bd_law_multi_agent.core.config import config
from bd_law_multi_agent.workflows.analysis_and_argument_workflow import argument_agent
from bd_law_multi_agent.schemas.schemas import User
from langchain.callbacks.manager import tracing_v2_enabled
import traceback
from bd_law_multi_agent.core.security import get_current_active_user
from bd_law_multi_agent.database.database import get_analysis_db
from bd_law_multi_agent.models.document_model import UserHistory
from datetime import datetime
from bd_law_multi_agent.services.legal_service import LegalAnalyzer
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi import Request
from bd_law_multi_agent.services.mistral_ocr import  MistralOCRTextExtractor



router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/argument_generation", summary="argument generation", response_model=ArgumentResponse)
async def generate_argument(
    file: UploadFile = File(..., description="PDF file to analyze"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    req: Request = None,
    current_user: User = Depends(get_current_active_user)
):
    """Generate structured legal argument for court defense"""
    try:
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
       
        initial_state = {
            "query": extracted_text,
            "documents": [],
            "classification": {
                "primary_category": "General"  # Provide default value
            }, 
            "analysis": extracted_text,  # Provide initial analysis with case details
            "argument": "",
            "follow_ups": [],
            "conversation_history": [],
            "current_step": "init"
        }
        
        # Enable LangSmith tracing for this run
        with tracing_v2_enabled(
            project_name="legal-argument-generation",
            tags=["production", "argument-endpoint"]
        ):
           
            result = argument_agent.invoke(
                initial_state, 
                {"recursion_limit": 50}
            )

            if "argument" not in result or not result["argument"]:
                if not result.get("documents"):
                    logger.warning("No documents retrieved, using direct generation")
                else:
                    logger.error("Documents found but argument missing!")
        
        logger.info(f"Final workflow state: current_step={result.get('current_step')}, has_argument={bool(result.get('argument'))}")
        sources = []
        if "documents" in result and result["documents"]:
            sources = [
                {
                    "source": doc.metadata.get("source_path", "Unknown"), \
                    "excerpt": doc.page_content
                }
                for doc in result.get("documents", [])
            ]
            
        
  
        if "argument" not in result or not result["argument"]:
            context = "\n\n".join([
                f"Source: {doc.metadata.get('source', 'Unknown')}\nContent: {doc.page_content[:500]}"
                for doc in result.get("documents", [])
            ])
            
            # Generate argument directly
            fallback_result = LegalAnalyzer.generate_legal_argument(
                case_details=extracted_text,
                context=context,
                category=result.get("classification", {}).get("primary_category", "General")  
            )
            
            argument = fallback_result
            legal_category = result.get("classification", {}).get("primary_category", "General")
        else:
            argument = result["argument"]
            legal_category = result.get("legal_category", "Unclassified")
        
        background_tasks.add_task(
            process_argument_history,
            temp_file_path=temp_file_path,
            user_id=current_user.id,
            user_email=current_user.email,
            user_name=current_user.full_name,
            file_name=file.filename,
            extracted_text=extracted_text,
            argument_result=argument,
            legal_category=legal_category
        )
        
        
        return {
            "argument": argument,
            "legal_category": legal_category,
            "sources": sources
        }
    except Exception as e:
        logger.error(f"Argument generation error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Argument generation failed")
    
    
    
    
# Add new background task handler
async def process_argument_history(
    temp_file_path: str,
    user_id: str,
    user_email: str,
    user_name: str,
    file_name: str,
    extracted_text: str,
    argument_result: str,
    legal_category: str
):
    """Background task to store argument generation history"""
    db = next(get_analysis_db())
    try:
        history_entry = UserHistory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            feature_used="argument_generation",
            case_file_name=file_name,
            case_file_content=extracted_text,
            agent_response={
                "argument": argument_result,
                "legal_category": legal_category,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        db.add(history_entry)
        db.commit()
        logger.info(f"Created argument history entry for user {user_email}")
        
    except Exception as e:
        logger.error(f"Background history processing error: {str(e)}")
        db.rollback()
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        db.close()