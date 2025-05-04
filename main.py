from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from bd_law_multi_agent.api.v1 import endpoints, auth_endpoint
from bd_law_multi_agent.core.config import config
from bd_law_multi_agent.database.database import Base, engine
from bd_law_multi_agent.core.security import get_current_active_user

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=config.PROJECT_NAME,
    openapi_url=f"{config.API_V1_STR}/openapi.json",
    # Add these docs configuration to improve Swagger UI behavior
    docs_url=None,  # Disable default docs
    redoc_url=None  # Disable default redoc
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
# Auth endpoints
app.include_router(
    auth_endpoint.router, 
    prefix=f"{config.API_V1_STR}/auth"
)

# Protected endpoints
app.include_router(
    endpoints.app,
    prefix=config.API_V1_STR,
)

# Custom Swagger UI with better OAuth2 integration
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
    """Health check endpoint"""
    return {"status": "healthy"}