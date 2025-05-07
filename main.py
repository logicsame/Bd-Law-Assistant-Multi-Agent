from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from sqlalchemy import text
import time 

from bd_law_multi_agent.api.v1 import endpoints, auth_endpoint
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

# Import necessary agent classes and creation functions
from bd_law_multi_agent.workflows.analysis_and_argument_workflow import (
    create_legal_workflow,
    create_argument_workflow,
    PersistentLegalRAG
)
from bd_law_multi_agent.core.common import logger # Assuming your logger is set up

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events for startup/shutdown with more explicit agent lifecycle demonstration.
    This demonstrates where you would put more complex agent startup/shutdown logic
    if your agent classes had specific methods for these (e.g., loading models,
    releasing resources not handled by Python GC).
    """
    # --- APPLICATION STARTUP --- #
    logger.info("Application startup sequence initiated...")

    # 1. Initialize Database Schemas and Connections
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
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        raise

    # 2. Explicitly Create and Initialize Agents
    logger.info("🤖 Creating and initializing agent instances...")
    
    # Instantiate agents directly within the lifespan startup
    app.state.rag_system = PersistentLegalRAG() # This initializes its own vector_store
    logger.info(f"  - RAG System (PersistentLegalRAG) instance created: {type(app.state.rag_system)}")
    
    app.state.legal_agent = create_legal_workflow() # This compiles the LangGraph workflow
    logger.info(f"  - Legal Agent (LangGraph Workflow) instance created: {type(app.state.legal_agent)}")
    
    app.state.argument_agent = create_argument_workflow() # This compiles the LangGraph workflow
    logger.info(f"  - Argument Agent (LangGraph Workflow) instance created: {type(app.state.argument_agent)}")

    # --- Illustrative Agent-Specific Startup Logic --- # 
    # If your agents had specific startup methods, you would call them here.
    # For example, if PersistentLegalRAG needed to load a large model or connect to a remote service:
    # if hasattr(app.state.rag_system, 'custom_startup_routine'):
    #     logger.info("  - Executing custom startup for RAG System...")
    #     await app.state.rag_system.custom_startup_routine() # Assuming it's an async method
    #     logger.info("  - RAG System custom startup complete.")
    # else:
    #     logger.info("  - RAG System does not have a custom_startup_routine method.")

    # Simulate some agent initialization work (e.g., loading models, warming up cache)
    logger.info("  - Simulating agent warm-up procedures (e.g., model loading)... ")
    # time.sleep(2) # Replace with actual async startup tasks if any
    logger.info("✅ Agents are explicitly created, (simulated warm-up complete), and available via app.state.")

    logger.info("Application startup sequence complete. Ready to serve requests.")
    yield
    # --- APPLICATION SHUTDOWN --- # (Code after yield runs on shutdown)
    logger.info("Application shutdown sequence initiated...")

    # 1. Explicitly Shut Down and Clean Up Agents
    logger.info("🤖 Shutting down and cleaning up agent instances...")

    # --- Illustrative Agent-Specific Shutdown Logic --- #
    # If your agents had specific shutdown methods (e.g., releasing resources, saving state):
    # if hasattr(app.state, 'rag_system') and hasattr(app.state.rag_system, 'custom_shutdown_routine'):
    #     logger.info("  - Executing custom shutdown for RAG System...")
    #     await app.state.rag_system.custom_shutdown_routine() # Assuming it's an async method
    #     logger.info("  - RAG System custom shutdown complete.")
    # else:
    #     logger.info("  - RAG System does not have a custom_shutdown_routine method or was already cleaned up.")

    # Remove from app.state and dereference to allow garbage collection
    if hasattr(app.state, 'rag_system'):
        logger.info(f"  - Cleaning up RAG System: {type(app.state.rag_system)}")
        del app.state.rag_system
    if hasattr(app.state, 'legal_agent'):
        logger.info(f"  - Cleaning up Legal Agent: {type(app.state.legal_agent)}")
        del app.state.legal_agent
    if hasattr(app.state, 'argument_agent'):
        logger.info(f"  - Cleaning up Argument Agent: {type(app.state.argument_agent)}")
        del app.state.argument_agent
    
    logger.info("✅ Agents explicitly cleaned up.")

    # 2. Close Database Connections
    logger.info("🛑 Closing database connections...")
    if main_engine:
        main_engine.dispose()
        logger.info("  - Main database connections closed.")
    if analysis_engine:
        analysis_engine.dispose()
        logger.info("  - Analysis database connections closed.")
    logger.info("🚪 All database connections closed.")
    logger.info("Application shutdown sequence complete.")

app = FastAPI(
    title=config.PROJECT_NAME,
    openapi_url=f"{config.API_V1_STR}/openapi.json",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
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
    """Endpoint for health checks"""
    agent_status = {}
    if hasattr(app, 'state'):
        agent_status["legal_agent"] = "available" if hasattr(app.state, 'legal_agent') and app.state.legal_agent is not None else "unavailable"
        agent_status["argument_agent"] = "available" if hasattr(app.state, 'argument_agent') and app.state.argument_agent is not None else "unavailable"
        agent_status["rag_system"] = "available" if hasattr(app.state, 'rag_system') and app.state.rag_system is not None else "unavailable"
    else:
        agent_status["legal_agent"] = "app.state not initialized"
        agent_status["argument_agent"] = "app.state not initialized"
        agent_status["rag_system"] = "app.state not initialized"

    return {
        "status": "healthy",
        "databases": {
            "main": "connected", 
            "analysis": "connected" 
        },
        "agents": agent_status
    }



