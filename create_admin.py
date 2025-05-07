import sys
import uuid
from sqlalchemy.orm import Session
from bd_law_multi_agent.database.database import SessionLocal
from bd_law_multi_agent.models.user_model import User
from bd_law_multi_agent.core.security import get_password_hash

# Add this import to resolve circular dependency
from bd_law_multi_agent.models.document_model import Document  # <-- Add this line

def create_admin():
    """Create initial admin user directly in the database"""
    db = SessionLocal()
    try:
        print("\nCreate First Admin User")
        print("-----------------------")
        
        email = "hakim@gmail.com"
        full_name = "hakim"
        password = "12345678"
        
        # Check if user exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"\n⚠️  User {email} already exists!")
            return

        # Create new admin user
        new_user = User(
            id=str(uuid.uuid4()),
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            is_admin=True
        )
        
        db.add(new_user)
        db.commit()
        print(f"\n✅ Admin user {email} created successfully!")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error creating admin: {str(e)}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()