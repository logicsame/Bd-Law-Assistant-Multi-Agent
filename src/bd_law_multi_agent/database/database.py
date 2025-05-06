from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from bd_law_multi_agent.core.config import config

# Create main database engine
main_engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}
)

# Create analysis database engine
analysis_db_path = os.path.join(config.ANALYSIS_VECTOR_DB_PATH, "analyzed_database.db")
os.makedirs(os.path.dirname(analysis_db_path), exist_ok=True)
analysis_engine = create_engine(
    f"sqlite:///{analysis_db_path}",
    connect_args={"check_same_thread": False}
)

# Create session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=main_engine)
AnalysisSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=analysis_engine)

# Create base classes for each database
Base = declarative_base()  # For main database
AnalysisBase = declarative_base()  # For analysis database

def get_db():
    """Get main database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_analysis_db():
    """Get analysis database session"""
    db = AnalysisSessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_analysis_tables():
    """Create tables for analysis database"""
    AnalysisBase.metadata.create_all(bind=analysis_engine)