from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from bd_law_multi_agent.core.config import config
from bd_law_multi_agent.core.security import create_access_token, get_current_active_user
from bd_law_multi_agent.database.database import get_db
from bd_law_multi_agent.schemas.schemas import User, UserCreate, Token
from bd_law_multi_agent.services.user_services import authenticate_user, create_user, get_user_by_email

# Note: No prefix here - the prefix is added in main.py
router = APIRouter(tags=["authentication"])


@router.post("/login", response_model=Token, summary="Login for access token")
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    
    - **username**: Email address used as username
    - **password**: User password
    """
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            subject=user.id,
            expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.post("/register", response_model=User, summary="Register new user")
async def register_user(
    user_in: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    Register a new user.
    
    - **email**: Required unique email address
    - **password**: Required password
    - **full_name**: Optional full name
    - **is_active**: User active status, defaults to true
    """
    user = get_user_by_email(user_in.email, db)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    return create_user(user_in, db)


@router.get("/me", response_model=User, summary="Get current user info")
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get current user information.
    
    Requires authentication.
    """
    return current_user