from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from sqlalchemy import text

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup/shutdown"""
    # Startup operations
    print("⏳ Initializing database schemas...")
    
    try:
        Base.metadata.create_all(bind=main_engine)
        create_analysis_tables()
        print("🔍 Testing main database connection...")
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            print("✅ Main database connection successful")
        print("🔍 Testing analysis database connection...")
        with analysis_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("✅ Analysis database connection successful")
            
    except Exception as e:
        print(f"❌ Database initialization failed: {str(e)}")
        raise
    
    yield 
    
    # Shutdown operations
    print("🛑 Closing database connections...")
    main_engine.dispose()
    analysis_engine.dispose()
    print("🚪 Databases connections closed")

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
    return {
        "status": "healthy",
        "databases": {
            "main": "connected",
            "analysis": "connected"
        }
    }