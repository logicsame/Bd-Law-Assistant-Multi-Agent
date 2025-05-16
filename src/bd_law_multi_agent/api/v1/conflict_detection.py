from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Request, BackgroundTasks
from bd_law_multi_agent.utils.logger import logger
from fastapi import Depends
from bd_law_multi_agent.core.security import get_current_active_user
from bd_law_multi_agent.schemas.schemas import User
from bd_law_multi_agent.models.document_model import UserHistory
from datetime import datetime
import uuid
import traceback
from bd_law_multi_agent.schemas.conflict_sc import ConflictResponse
from langchain.callbacks.manager import tracing_v2_enabled
from bd_law_multi_agent.workflows.conflict_workflow import detect_conflicts
from bd_law_multi_agent.database.database import get_analysis_db


router = APIRouter()




@router.post("/check", summary="Check for conflicts of interest in legal document", response_model=ConflictResponse)
async def check_conflicts(
    file: UploadFile = File(..., description="PDF file to check for conflicts"),
    similarity_threshold: float = Query(0.85, ge=0.0, le=1.0, description="Similarity threshold for conflict detection"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    req: Request = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Check for conflicts of interest in a legal document using LangGraph workflow.
    """
    
    
    try:
        # File validation
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        # Read file content
        pdf_bytes = await file.read()
        
        
        final_result = None
        trace_url = None
        
        with tracing_v2_enabled(
            project_name="legal-conflict-detection",
            tags=["production", "conflict-detection"]
        ) as session:
            try:
                # Execute the workflow
                final_result = detect_conflicts(
                file_content=pdf_bytes,
                file_name=file.filename,
                similarity_threshold=similarity_threshold
            )
                
               
                if hasattr(session, 'run_id'):
                    trace_url = f"https://smith.langchain.com/trace/{session.run_id}"
                    logger.info(f"LangSmith trace: {trace_url}")
                    final_result["trace_url"] = trace_url
                
            except Exception as e:
                logger.error(f"Conflict detection workflow failed: {str(e)}")
                if hasattr(session, 'run_id'):
                    error_trace_url = f"https://smith.langchain.com/trace/{session.run_id}/errors"
                    logger.info(f"Error trace: {error_trace_url}")
                raise
        
       
        if final_result.get("error"):
            raise HTTPException(
                status_code=500,
                detail=f"Processing error: {final_result['error']}"
            )
        
        
        background_tasks.add_task(
        process_conflict_check,
        user_id=current_user.id,
        user_email=current_user.email,
        user_name=current_user.full_name,
        file_name=file.filename,
        conflict_results=final_result,
        extracted_text=final_result.get("extracted_text", "")  
        )
        
        
        return ConflictResponse(
            conflicts_detected=final_result.get("conflicts_detected", False),
            explanation=final_result.get("explanation", ""),
            entities_found=final_result.get("entities_found", []),
            conflicts=final_result.get("conflicts", []),
            trace_url=final_result.get("trace_url"),
            case_title=final_result.get("case_title", "")
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Conflict detection error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Conflict detection failed: {str(e)}")

async def process_conflict_check(
    user_id: str,
    user_email: str,
    user_name: str,
    file_name: str,
    conflict_results: dict,
    extracted_text: str  

):
    """Background task to store conflict check results"""
    db = next(get_analysis_db())
    try:
        history_entry = UserHistory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            feature_used="conflict_detection",
            case_file_content=extracted_text,  

            case_file_name=file_name,
            agent_response={
                "conflicts_detected": conflict_results.get("conflicts_detected", False),
                "entities_found": conflict_results.get("entities_found", []),
                "conflicts": conflict_results.get("conflicts", []),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        db.add(history_entry)
        db.commit()
        logger.info(f"Created conflict check history entry for {user_email}")

    except Exception as e:
        logger.error(f"Conflict history storage failed: {str(e)}")
        db.rollback()
    finally:
        db.close()