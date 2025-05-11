from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from bd_law_multi_agent.schemas.chat_sc import ChatbotRequest, ChatbotResponse
from bd_law_multi_agent.workflows.chat_workflow import chat_agent
from langchain.callbacks.manager import tracing_v2_enabled
from bd_law_multi_agent.core.common import logger
from bd_law_multi_agent.core.security import get_current_active_user
from bd_law_multi_agent.models.document_model import UserHistory
from bd_law_multi_agent.database.database import get_analysis_db
from bd_law_multi_agent.schemas.schemas import User
from datetime import datetime
import traceback
import uuid

router = APIRouter()

@router.post("/chat", response_model=ChatbotResponse)
async def handle_chatbot_query(
    request: ChatbotRequest,
    background_tasks: BackgroundTasks,
    req: Request = None,
    current_user: User = Depends(get_current_active_user)
):
    """LangGraph-powered legal chatbot endpoint"""
    try:
        conversation_history = request.conversation_history if hasattr(request, 'conversation_history') else []
        
        initial_state = {
            "query": request.query,
            "documents": [],
            "response": "",
            "response_type": "general_advice",
            "sources": [],
            "conversation_history": conversation_history,
            "current_step": "start"
        }
        
        final_state = None
        trace_url = None
        
        with tracing_v2_enabled(
            project_name="legal-chatbot",
            tags=["production", "chatbot-endpoint"]
        ) as session:
            try:
                final_state = chat_agent.invoke(initial_state)
                
                if hasattr(session, 'run_id'):
                    trace_url = f"https://smith.langchain.com/trace/{session.run_id}"
                    logger.info(f"LangSmith trace: {trace_url}")
                
            except Exception as e:
                logger.error(f"Chatbot workflow failed: {str(e)}")
                if hasattr(session, 'run_id'):
                    trace_url = f"https://smith.langchain.com/trace/{session.run_id}/errors"
                traceback.print_exc()
                raise
        
        if "error" in final_state and final_state["error"]:
            raise HTTPException(
                status_code=500,
                detail=f"Processing error: {final_state['error']}"
            )
        
        sources = final_state.get("sources", [])
        formatted_sources = []
        for source in sources:
            if isinstance(source, dict):
                if "page" not in source:
                    source["page"] = 1  
                formatted_sources.append(source)
        
        # Add background task for history storage
        background_tasks.add_task(
            process_chat_history,
            user_id=current_user.id,
            user_email=current_user.email,
            user_name=current_user.full_name,
            query=request.query,
            response=final_state.get("response", ""),
            sources=formatted_sources,
            response_type=final_state.get("response_type", "general_advice")
        )
        
        return {
            "response_type": final_state.get("response_type", "general_advice"),
            "response": final_state.get("response", "I couldn't process your query at this time."),
            "sources": formatted_sources,
            "trace_url": trace_url
        }
        
    except Exception as e:
        logger.error(f"Chatbot error: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="Chatbot service unavailable. Please try again later."
        )

# Background task handler
async def process_chat_history(
    user_id: str,
    user_email: str,
    user_name: str,
    query: str,
    response: str,
    sources: list,
    response_type: str
):
    """Store chat interaction in history"""
    db = next(get_analysis_db())
    try:
        history_entry = UserHistory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            feature_used="legal_chat",
            case_file_name="",  
            case_file_content=query,
            agent_response={
                "response": response,
                "sources": sources,
                "response_type": response_type,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        db.add(history_entry)
        db.commit()
        logger.info(f"Created chat history entry for {user_email}")
        
    except Exception as e:
        logger.error(f"Chat history storage failed: {str(e)}")
        db.rollback()
    finally:
        db.close()