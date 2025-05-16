"""
Lifespan management module for the BD Law Multi-Agent system.

This module handles the initialization and cleanup of all agents and database connections
in a production-grade manner with proper error handling and resource management.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from sqlalchemy import text
import asyncio
import signal
import traceback
import time

from bd_law_multi_agent.core.common import logger
from bd_law_multi_agent.database.database import (
    Base,
    main_engine,
    analysis_engine,
    SessionLocal,
    create_analysis_tables
)
from bd_law_multi_agent.workflows.analysis_and_argument_workflow import (
    create_legal_workflow,
    create_argument_workflow,
    PersistentLegalRAG
)
from bd_law_multi_agent.services.legal_chat import LegalChatbot
from bd_law_multi_agent.services.conflict_detection import ConflictDetectionService

_is_shutting_down = False
_db_connections_active = False
_agents_initialized = False
_legal_chat_initialized = False
_conflict_detection_initialized = False

def signal_handler(sig, frame):
    """Handle termination signals for graceful shutdown"""
    global _is_shutting_down
    if not _is_shutting_down:
        logger.warning(f"Received termination signal {sig}. Initiating graceful shutdown...")
        _is_shutting_down = True
      

# Register signal handlers
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
    """Initialize core agent instances with proper error handling"""
    global _agents_initialized
    
    if _agents_initialized:
        logger.info("Core agents already initialized, skipping initialization")
        return True
        
    logger.info("🤖 Creating and initializing core agent instances...")
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
        logger.info("✅ Core agents are explicitly created, initialized, and available via app.state.")
        return True
    except Exception as e:
        logger.error(f"❌ Core agent initialization failed: {str(e)}")
        logger.error(traceback.format_exc())
        _agents_initialized = False
        return False

async def initialize_legal_chat(app: FastAPI):
    """Initialize legal chat agent with proper error handling"""
    global _legal_chat_initialized
    
    if _legal_chat_initialized:
        logger.info("Legal chat agent already initialized, skipping initialization")
        return True
    
    if not hasattr(app.state, 'rag_system') or app.state.rag_system is None:
        logger.error("Cannot initialize legal chat agent: RAG system not available")
        return False
    
    logger.info("🤖 Creating and initializing legal chat agent...")
    try:
        # Initialize legal chat agent
        logger.info("Initializing Legal Chat Agent...")
        app.state.legal_chat_agent = LegalChatbot(app.state.rag_system)
        logger.info(f"  - Legal Chat Agent (LegalChatbot) instance created: {type(app.state.legal_chat_agent)}")
        
        # Warm up the legal chat agent
        logger.info("  - Warming up Legal Chat Agent...")
        
        _legal_chat_initialized = True
        logger.info("✅ Legal Chat Agent explicitly created, initialized, and available via app.state.")
        return True
    except Exception as e:
        logger.error(f"❌ Legal Chat Agent initialization failed: {str(e)}")
        logger.error(traceback.format_exc())
        _legal_chat_initialized = False
        return False

async def initialize_conflict_detection(app: FastAPI):
    """Initialize conflict detection agent with proper error handling"""
    global _conflict_detection_initialized
    
    if _conflict_detection_initialized:
        logger.info("Conflict detection agent already initialized, skipping initialization")
        return True
    
    logger.info("🤖 Creating and initializing conflict detection agent...")
    try:
        # Initialize conflict detection agent
        logger.info("Initializing Conflict Detection Agent...")
        app.state.conflict_detection_agent = ConflictDetectionService()
        logger.info(f"  - Conflict Detection Agent (ConflictDetectionService) instance created: {type(app.state.conflict_detection_agent)}")
        
        # Warm up the conflict detection agent
        logger.info("  - Warming up Conflict Detection Agent...")
        if hasattr(app.state.conflict_detection_agent, 'nlp') and app.state.conflict_detection_agent.nlp is None:
            try:
                import spacy
                app.state.conflict_detection_agent.nlp = spacy.load("en_core_web_sm")
                logger.info("    - Successfully preloaded spaCy model for conflict detection")
            except Exception as e:
                logger.warning(f"    - Could not preload spaCy model: {str(e)}")
        
        _conflict_detection_initialized = True
        logger.info("✅ Conflict Detection Agent explicitly created, initialized, and available via app.state.")
        return True
    except Exception as e:
        logger.error(f"❌ Conflict Detection Agent initialization failed: {str(e)}")
        logger.error(traceback.format_exc())
        _conflict_detection_initialized = False
        return False

async def shutdown_agents(app: FastAPI):
    """Shutdown core agent instances with proper error handling"""
    global _agents_initialized
    
    if not _agents_initialized:
        logger.info("Core agents not initialized or already shut down, skipping cleanup")
        return
        
    logger.info("🤖 Shutting down and cleaning up core agent instances...")
    try:
        # Clean up RAG system
        if hasattr(app.state, 'rag_system') and app.state.rag_system is not None:
            logger.info(f"  - Cleaning up RAG System: {type(app.state.rag_system)}")
            if hasattr(app.state.rag_system, 'cleanup'):
                await app.state.rag_system.cleanup()
            del app.state.rag_system
            
        # Clean up Legal Agent
        if hasattr(app.state, 'legal_agent') and app.state.legal_agent is not None:
            logger.info(f"  - Cleaning up Legal Agent: {type(app.state.legal_agent)}")
            if hasattr(app.state.legal_agent, 'cleanup'):
                await app.state.legal_agent.cleanup()
            del app.state.legal_agent
            
        # Clean up Argument Agent
        if hasattr(app.state, 'argument_agent') and app.state.argument_agent is not None:
            logger.info(f"  - Cleaning up Argument Agent: {type(app.state.argument_agent)}")
            if hasattr(app.state.argument_agent, 'cleanup'):
                await app.state.argument_agent.cleanup()
            del app.state.argument_agent
            
        _agents_initialized = False
        logger.info("✅ Core agents explicitly cleaned up.")
    except Exception as e:
        logger.error(f"❌ Error during core agent shutdown: {str(e)}")
        logger.error(traceback.format_exc())

async def shutdown_legal_chat(app: FastAPI):
    """Shutdown legal chat agent with proper error handling"""
    global _legal_chat_initialized
    
    if not _legal_chat_initialized:
        logger.info("Legal chat agent not initialized or already shut down, skipping cleanup")
        return
    
    logger.info("🤖 Shutting down and cleaning up legal chat agent...")
    try:
        if hasattr(app.state, 'legal_chat_agent') and app.state.legal_chat_agent is not None:
            logger.info(f"  - Cleaning up Legal Chat Agent: {type(app.state.legal_chat_agent)}")
            if hasattr(app.state.legal_chat_agent, 'cleanup'):
                await app.state.legal_chat_agent.cleanup()
            if hasattr(app.state.legal_chat_agent, 'llm'):
                app.state.legal_chat_agent.llm = None
            del app.state.legal_chat_agent
        
        _legal_chat_initialized = False
        logger.info("✅ Legal Chat Agent explicitly cleaned up.")
    except Exception as e:
        logger.error(f"❌ Error during legal chat agent shutdown: {str(e)}")
        logger.error(traceback.format_exc())

async def shutdown_conflict_detection(app: FastAPI):
    """Shutdown conflict detection agent with proper error handling"""
    global _conflict_detection_initialized
    
    if not _conflict_detection_initialized:
        logger.info("Conflict detection agent not initialized or already shut down, skipping cleanup")
        return
    
    logger.info("🤖 Shutting down and cleaning up conflict detection agent...")
    try:
        # Clean up Conflict Detection Agent
        if hasattr(app.state, 'conflict_detection_agent') and app.state.conflict_detection_agent is not None:
            logger.info(f"  - Cleaning up Conflict Detection Agent: {type(app.state.conflict_detection_agent)}")
            if hasattr(app.state.conflict_detection_agent, 'cleanup'):
                await app.state.conflict_detection_agent.cleanup()
            if hasattr(app.state.conflict_detection_agent, 'nlp'):
                app.state.conflict_detection_agent.nlp = None
            if hasattr(app.state.conflict_detection_agent, 'llm'):
                app.state.conflict_detection_agent.llm = None
            if hasattr(app.state.conflict_detection_agent, 'analysis_db'):
                app.state.conflict_detection_agent.analysis_db = None
            del app.state.conflict_detection_agent
        
        _conflict_detection_initialized = False
        logger.info("✅ Conflict Detection Agent explicitly cleaned up.")
    except Exception as e:
        logger.error(f"❌ Error during conflict detection agent shutdown: {str(e)}")
        logger.error(traceback.format_exc())

async def shutdown_databases():
    """Shutdown database connections with proper error handling"""
    global _db_connections_active
    
    if not _db_connections_active:
        logger.info("Databases not initialized or already shut down, skipping cleanup")
        return
        
    logger.info("🛑 Closing database connections...")
    try:
        # Close main database connections
        if main_engine:
            main_engine.dispose()
            logger.info("  - Main database connections closed.")
            
        # Close analysis database connections
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
    Includes proper error handling, graceful shutdown support, and resource cleanup for all agents.
    """
    global _is_shutting_down
    
    # --- APPLICATION STARTUP --- #
    logger.info("Application startup sequence initiated...")
    
    # Initialize databases
    db_init_success = await initialize_databases()
    if not db_init_success:
        logger.critical("Database initialization failed. Application cannot start properly.")
        
    
    # Initialize core agents
    agent_init_success = await initialize_agents(app)
    if not agent_init_success:
        logger.critical("Core agent initialization failed. Application may not function properly.")
    
    # Initialize legal chat agent
    legal_chat_init_success = await initialize_legal_chat(app)
    if not legal_chat_init_success:
        logger.critical("Legal chat agent initialization failed. Legal chat functionality may not be available.")
    
    # Initialize conflict detection agent
    conflict_detection_init_success = await initialize_conflict_detection(app)
    if not conflict_detection_init_success:
        logger.critical("Conflict detection agent initialization failed. Conflict detection functionality may not be available.")
    
    logger.info("Application startup sequence complete. Ready to serve requests.")
    
    try:
        # Application is now running
        yield
    except Exception as e:
        logger.error(f"Unhandled exception in application lifespan: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        # --- APPLICATION SHUTDOWN --- #
        _is_shutting_down = True
        logger.info("Application shutdown sequence initiated...")
        
        # Shutdown agents in reverse order of initialization
        await shutdown_conflict_detection(app)
        await shutdown_legal_chat(app)
        
        # Then, shutdown core agents
        await shutdown_agents(app)
        
        # Finally, shutdown databases
        await shutdown_databases()
        
        logger.info("Application shutdown sequence complete.")

def get_system_status(app: FastAPI):
    """Get detailed system status for health checks"""
    global _db_connections_active, _agents_initialized, _legal_chat_initialized, _conflict_detection_initialized, _is_shutting_down
    
    # Check if application is shutting down
    if _is_shutting_down:
        raise HTTPException(status_code=503, detail="Service is shutting down")
    
    # Check database connections
    db_status = {"status": "unknown"}
    try:
        # Test main database connection
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db_status["main"] = "connected"
    except Exception as e:
        db_status["main"] = f"error: {str(e)}"
    
    try:
        # Test analysis database connection
        with analysis_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_status["analysis"] = "connected"
    except Exception as e:
        db_status["analysis"] = f"error: {str(e)}"
    
    # Check agent status
    agent_status = {}
    if hasattr(app, 'state'):
        # Core agents
        agent_status["legal_agent"] = "available" if hasattr(app.state, 'legal_agent') and app.state.legal_agent is not None else "unavailable"
        agent_status["argument_agent"] = "available" if hasattr(app.state, 'argument_agent') and app.state.argument_agent is not None else "unavailable"
        agent_status["rag_system"] = "available" if hasattr(app.state, 'rag_system') and app.state.rag_system is not None else "unavailable"
        
        # Specialized agents
        agent_status["legal_chat_agent"] = "available" if hasattr(app.state, 'legal_chat_agent') and app.state.legal_chat_agent is not None else "unavailable"
        agent_status["conflict_detection_agent"] = "available" if hasattr(app.state, 'conflict_detection_agent') and app.state.conflict_detection_agent is not None else "unavailable"
    else:
        agent_status["legal_agent"] = "app.state not initialized"
        agent_status["argument_agent"] = "app.state not initialized"
        agent_status["rag_system"] = "app.state not initialized"
        agent_status["legal_chat_agent"] = "app.state not initialized"
        agent_status["conflict_detection_agent"] = "app.state not initialized"
    
    # Determine overall status
    overall_status = "healthy"
    if not _db_connections_active or "error" in db_status.get("main", "") or "error" in db_status.get("analysis", ""):
        overall_status = "degraded"
    if not _agents_initialized or all(status == "unavailable" for status in [agent_status["legal_agent"], agent_status["argument_agent"], agent_status["rag_system"]]):
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "databases": db_status,
        "agents": agent_status,
        "system": {
            "shutting_down": _is_shutting_down,
            "db_connections_active": _db_connections_active,
            "core_agents_initialized": _agents_initialized,
            "legal_chat_initialized": _legal_chat_initialized,
            "conflict_detection_initialized": _conflict_detection_initialized,
            "uptime": time.time()  
        }
    }
