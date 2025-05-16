from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi import Form

from bd_law_multi_agent.core.config import config
from bd_law_multi_agent.core.security import create_access_token, get_current_active_user
from bd_law_multi_agent.database.database import get_db
from bd_law_multi_agent.schemas.schemas import User, UserCreate, Token
from bd_law_multi_agent.services.user_services import authenticate_user, create_user, get_user_by_email
from bd_law_multi_agent.models.document_model import UserHistory
from bd_law_multi_agent.database.database import get_analysis_db
from bd_law_multi_agent.utils.logger import logger

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

@router.post("/promote-to-admin", summary="Promote user to admin")
async def promote_to_admin(
    email: str = Form(..., description="Email of user to promote"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    
    from bd_law_multi_agent.models.user_model import User as DBUser  # <-- Add this import
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can promote users"
        )
    
    
    user = db.query(DBUser).filter(DBUser.email == email).first()  # <-- Changed User to DBUser
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already an admin"
        )
    
    try:
        user.is_admin = True
        db.commit()
        return {"status": "success", "message": f"{email} promoted to admin"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Promotion failed: {str(e)}"
        )



@router.get("/me", response_model=User, summary="Get current user info")
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get current user information.
    
    Requires authentication.
    """
    return current_user


# Add to analyze.py or endpoints.py
@router.get("/history", summary="Get user analysis history")
async def get_user_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_analysis_db)
):
    """Get analysis history for the current user"""
    try:
        history = db.query(UserHistory)\
            .filter(UserHistory.user_id == current_user.id)\
            .order_by(UserHistory.created_at.desc())\
            .all()
        
        return [
            {
                "id": item.id,
                "case_file_name": item.case_file_name,
                "created_at": item.created_at.isoformat(),
                "case_file_content": item.case_file_content,
                "agent_response": item.agent_response
            }
            for item in history
        ]
    except Exception as e:
        logger.error(f"History retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not retrieve history")