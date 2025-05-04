import sys
import os


 

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from bd_law_multi_agent.database.database import SessionLocal, engine, Base
from bd_law_multi_agent.models.user_model import User
from bd_law_multi_agent.services.user_services import get_user_by_email, create_user
from bd_law_multi_agent.schemas.schemas import UserCreate

def create_admin_user(email: str, password: str, full_name: str = "Admin User"):
    """Create an admin user if it doesn't exist"""
    Base.metadata.create_all(bind=engine)
    
    # Create session
    db = SessionLocal()
    
    try:
        # Check if user already exists
        user = get_user_by_email(email, db)
        if user:
            print(f"User with email {email} already exists")
            return
        
        # Create user
        user_in = UserCreate(
            email=email,
            password=password,
            full_name=full_name,
            is_active=True
        )
        
        user = create_user(user_in, db)
        print(f"Admin user created with ID: {user.id}")
        
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <email> <password> [full_name]")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    full_name = sys.argv[3] if len(sys.argv) > 3 else "Admin User"
    
    create_admin_user(email, password, full_name)