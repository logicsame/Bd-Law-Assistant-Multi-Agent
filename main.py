from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from sqlalchemy import text
import time
import asyncio
import signal
import sys
import traceback

from bd_law_multi_agent.api.v1 import endpoints, auth_endpoint, argument_generaion, legal_chat, conflict_detection
from bd_law_multi_agent.api.v1 import analyze
from bd_law_multi_agent.core.config import config
from bd_law_multi_agent.database.database import (
    Base,
    AnalysisBase,
    main_engine,
    analysis_engine,
    SessionLocal,
    create_analysis_tables
)
from bd_law_multi_agent.core.security import get_current_active_user
from bd_law_multi_agent.workflows.analysis_and_argument_workflow import (
    create_legal_workflow,
    create_argument_workflow,
    PersistentLegalRAG
)
from bd_law_multi_agent.core.common import logger

_is_shutting_down = False
_db_connections_active = False
_agents_initialized = False

def signal_handler(sig, frame):
    """Handle termination signals for graceful shutdown"""
    global _is_shutting_down
    if not _is_shutting_down:
        logger.warning(f"Received termination signal {sig}. Initiating graceful shutdown...")
        _is_shutting_down = True
        

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

async def initialize_databases():
    """Initialize database connections and schemas with proper error handling"""
    global _db_connections_active
    
    if _db_connections_active:
        logger.info("Databases already initialized, skipping initialization")
        return True
        
    logger.info("Initializing database schemas...")
    try:
        Base.metadata.create_all(bind=main_engine)
        create_analysis_tables()
        logger.info("Database schemas created/verified.")
        
        logger.info("Testing main database connection...")
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            logger.info("✅ Main database connection successful")
            
        logger.info("Testing analysis database connection...")
        with analysis_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("✅ Analysis database connection successful")
            
        _db_connections_active = True
        return True
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        logger.error(traceback.format_exc())
        _db_connections_active = False
        return False

async def initialize_agents(app: FastAPI):
    """Initialize agent instances with proper error handling"""
    global _agents_initialized
    
    if _agents_initialized:
        logger.info("Agents already initialized, skipping initialization")
        return True
        
    logger.info("🤖 Creating and initializing agent instances...")
    try:
        logger.info("Initializing RAG System...")
        app.state.rag_system = PersistentLegalRAG()
        logger.info(f"  - RAG System (PersistentLegalRAG) instance created: {type(app.state.rag_system)}")
        
        logger.info("Initializing Legal Agent...")
        app.state.legal_agent = create_legal_workflow()
        logger.info(f"  - Legal Agent (LangGraph Workflow) instance created: {type(app.state.legal_agent)}")
        
        logger.info("Initializing Argument Agent...")
        app.state.argument_agent = create_argument_workflow()
        logger.info(f"  - Argument Agent (LangGraph Workflow) instance created: {type(app.state.argument_agent)}")
        
        logger.info("  - Simulating agent warm-up procedures (e.g., model loading)...")
        await asyncio.sleep(0.1)  
        
        _agents_initialized = True
        logger.info("✅ Agents are explicitly created, initialized, and available via app.state.")
        return True
    except Exception as e:
        logger.error(f"❌ Agent initialization failed: {str(e)}")
        logger.error(traceback.format_exc())
        _agents_initialized = False
        return False

async def shutdown_agents(app: FastAPI):
    """Shutdown agent instances with proper error handling"""
    global _agents_initialized
    
    if not _agents_initialized:
        logger.info("Agents not initialized or already shut down, skipping cleanup")
        return
        
    logger.info("🤖 Shutting down and cleaning up agent instances...")
    try:
        if hasattr(app.state, 'rag_system') and app.state.rag_system is not None:
            logger.info(f"  - Cleaning up RAG System: {type(app.state.rag_system)}")
            if hasattr(app.state.rag_system, 'cleanup'):
                await app.state.rag_system.cleanup()
            del app.state.rag_system
            
        if hasattr(app.state, 'legal_agent') and app.state.legal_agent is not None:
            logger.info(f"  - Cleaning up Legal Agent: {type(app.state.legal_agent)}")
            if hasattr(app.state.legal_agent, 'cleanup'):
                await app.state.legal_agent.cleanup()
            del app.state.legal_agent
            
        if hasattr(app.state, 'argument_agent') and app.state.argument_agent is not None:
            logger.info(f"  - Cleaning up Argument Agent: {type(app.state.argument_agent)}")
            if hasattr(app.state.argument_agent, 'cleanup'):
                await app.state.argument_agent.cleanup()
            del app.state.argument_agent
            
        _agents_initialized = False
        logger.info("✅ Agents explicitly cleaned up.")
    except Exception as e:
        logger.error(f"❌ Error during agent shutdown: {str(e)}")
        logger.error(traceback.format_exc())

async def shutdown_databases():
    """Shutdown database connections with proper error handling"""
    global _db_connections_active
    
    if not _db_connections_active:
        logger.info("Databases not initialized or already shut down, skipping cleanup")
        return
        
    logger.info("🛑 Closing database connections...")
    try:
        if main_engine:
            main_engine.dispose()
            logger.info("  - Main database connections closed.")
            
        if analysis_engine:
            analysis_engine.dispose()
            logger.info("  - Analysis database connections closed.")
            
        _db_connections_active = False
        logger.info("🚪 All database connections closed.")
    except Exception as e:
        logger.error(f"❌ Error during database shutdown: {str(e)}")
        logger.error(traceback.format_exc())

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Production-level lifespan management for startup/shutdown with explicit agent and database lifecycle.
    Includes proper error handling, graceful shutdown support, and resource cleanup.
    """
    global _is_shutting_down
    
    # --- APPLICATION STARTUP --- #
    logger.info("Application startup sequence initiated...")
    
    db_init_success = await initialize_databases()
    if not db_init_success:
        logger.critical("Database initialization failed. Application cannot start properly.")
        
  
    agent_init_success = await initialize_agents(app)
    if not agent_init_success:
        logger.critical("Agent initialization failed. Application may not function properly.")
    
    logger.info("Application startup sequence complete. Ready to serve requests.")
    
    try:
        yield
    except Exception as e:
        logger.error(f"Unhandled exception in application lifespan: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        _is_shutting_down = True
        logger.info("Application shutdown sequence initiated...")
        
        await shutdown_agents(app)
        
        await shutdown_databases()
        
        logger.info("Application shutdown sequence complete.")

app = FastAPI(
    title=config.PROJECT_NAME,
    openapi_url=f"{config.API_V1_STR}/openapi.json",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    auth_endpoint.router,
    prefix=f"{config.API_V1_STR}/auth"
)

app.include_router(
    endpoints.app,
    prefix=config.API_V1_STR,
)

app.include_router(
    analyze.router,
    prefix=config.API_V1_STR,
    tags=["analyze"],
    dependencies=[Depends(get_current_active_user)]
)
app.include_router(
    argument_generaion.router,
    prefix=config.API_V1_STR,
    tags = ['argument_generation'],
    dependencies=[Depends(get_current_active_user)]
)

app.include_router(
    legal_chat.router,
    prefix=config.API_V1_STR,
    tags=['Legal-Chat_system'],
    dependencies=[Depends(get_current_active_user)]
)


app.include_router(
    conflict_detection.router,
    prefix=config.API_V1_STR,
    tags=['Conflic-Detection'],
    dependencies=[Depends(get_current_active_user)]
)

# Custom Swagger UI
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        oauth2_redirect_url=f"/api/v1/oauth2-redirect",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
        init_oauth={
            "clientId": "",
            "clientSecret": "",
            "usePkceWithAuthorizationCodeGrant": False,
            "useBasicAuthenticationWithAccessCodeGrant": True
        }
    )

@app.get("/api/v1/oauth2-redirect", include_in_schema=False)
async def oauth2_redirect():
    return {"message": "Auth redirect"}

@app.get("/health")
async def health_check():
    """Endpoint for health checks with detailed status information"""
    global _db_connections_active, _agents_initialized, _is_shutting_down
    
    if _is_shutting_down:
        raise HTTPException(status_code=503, detail="Service is shutting down")
    
    db_status = {"status": "unknown"}
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db_status["main"] = "connected"
    except Exception as e:
        db_status["main"] = f"error: {str(e)}"
    
    try:
        with analysis_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_status["analysis"] = "connected"
    except Exception as e:
        db_status["analysis"] = f"error: {str(e)}"
    
    agent_status = {}
    if hasattr(app, 'state'):
        agent_status["legal_agent"] = "available" if hasattr(app.state, 'legal_agent') and app.state.legal_agent is not None else "unavailable"
        agent_status["argument_agent"] = "available" if hasattr(app.state, 'argument_agent') and app.state.argument_agent is not None else "unavailable"
        agent_status["rag_system"] = "available" if hasattr(app.state, 'rag_system') and app.state.rag_system is not None else "unavailable"
    else:
        agent_status["legal_agent"] = "app.state not initialized"
        agent_status["argument_agent"] = "app.state not initialized"
        agent_status["rag_system"] = "app.state not initialized"
    
    # Determine overall status
    overall_status = "healthy"
    if not _db_connections_active or "error" in db_status.get("main", "") or "error" in db_status.get("analysis", ""):
        overall_status = "degraded"
    if not _agents_initialized or all(status == "unavailable" for status in agent_status.values()):
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "databases": db_status,
        "agents": agent_status,
        "system": {
            "shutting_down": _is_shutting_down,
            "db_connections_active": _db_connections_active,
            "agents_initialized": _agents_initialized,
            "uptime": time.time()  
        }
    }
