from typing import Optional
from sqlalchemy.orm import Session

from bd_law_multi_agent.core.security import get_password_hash, verify_password
from bd_law_multi_agent.database.database import SessionLocal
from bd_law_multi_agent.models.user_model import User
from bd_law_multi_agent.schemas.schemas import UserCreate, UserUpdate, User as UserSchema


def get_user_by_email(email: str, db: Session = None) -> Optional[User]:
    """
    Get a user by email.
    
    Args:
        email: User email
        db: Database session
        
    Returns:
        User object or None if not found
    """
    if db is None:
        db = SessionLocal()
        
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(user_id: str, db: Session = None) -> Optional[User]:
    """
    Get a user by ID.
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        User object or None if not found
    """
    if db is None:
        db = SessionLocal()
        
    return db.query(User).filter(User.id == user_id).first()


def authenticate_user(email: str, password: str, db: Session = None) -> Optional[User]:
    """
    Authenticate a user by email and password.
    
    Args:
        email: User email
        password: User password
        db: Database session
        
    Returns:
        User object if authenticated, None otherwise
    """
    user = get_user_by_email(email, db)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_user(user_in: UserCreate, db: Session = None) -> User:
    """
    Create a new user.
    
    Args:
        user_in: User creation data
        db: Database session
        
    Returns:
        Created user object
    """
    if db is None:
        db = SessionLocal()
        db_created = True
    else:
        db_created = False
        
    db_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        is_active=user_in.is_active
    )
    
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    finally:
        if db_created:
            db.close()


def update_user(user_id: str, user_in: UserUpdate, db: Session = None) -> Optional[User]:
    """
    Update an existing user.
    
    Args:
        user_id: User ID
        user_in: User update data
        db: Database session
        
    Returns:
        Updated user object or None if not found
    """
    if db is None:
        db = SessionLocal()
        db_created = True
    else:
        db_created = False
        
    db_user = get_user_by_id(user_id, db)
    if not db_user:
        return None
    
    update_data = user_in.dict(exclude_unset=True)
    
    if "password" in update_data:
        hashed_password = get_password_hash(update_data["password"])
        del update_data["password"]
        update_data["hashed_password"] = hashed_password
        
    for field, value in update_data.items():
        setattr(db_user, field, value)
        
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    finally:
        if db_created:
            db.close()


def delete_user(user_id: str, db: Session = None) -> bool:
    """
    Delete a user.
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        True if deleted, False if not found
    """
    if db is None:
        db = SessionLocal()
        db_created = True
    else:
        db_created = False
        
    db_user = get_user_by_id(user_id, db)
    if not db_user:
        return False
    
    try:
        db.delete(db_user)
        db.commit()
        return True
    finally:
        if db_created:
            db.close()