from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html

from bd_law_multi_agent.api.v1 import endpoints, auth_endpoint, argument_generaion, legal_chat, conflict_detection
from bd_law_multi_agent.api.v1 import analyze
from bd_law_multi_agent.core.config import config
from bd_law_multi_agent.core.security import get_current_active_user
from bd_law_multi_agent.core.lifespan import lifespan, get_system_status

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
    allow_origins=["*"],  
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
    return get_system_status(app)
