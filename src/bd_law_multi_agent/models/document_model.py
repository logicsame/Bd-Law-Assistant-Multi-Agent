from sqlalchemy import Column, String, Text, ForeignKey, Integer, DateTime, JSON
from sqlalchemy import UniqueConstraint

from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
from bd_law_multi_agent.database.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    admin_email = Column(String, nullable=False)  
    source_type = Column(String, nullable=False)
    source_path = Column(String, nullable=False)
    description = Column(Text)
    text_preview = Column(Text)
    full_text = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    """Document chunk storage model"""
    __tablename__ = "document_chunks"
    
    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey('documents.id'))
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    chunk_metadata = Column(JSON)  # Changed from 'metadata' to 'chunk_metadata'
    
    document = relationship("Document", back_populates="chunks")
    
from bd_law_multi_agent.database.database import AnalysisBase  

# In document_model.py
class AnalysisDocument(AnalysisBase):
    __tablename__ = "analyzed_documents"
    
    id = Column(String, primary_key=True, index=True)
    source_path = Column(String, unique=True, index=True)
    document_type = Column(String) 
    created_at = Column(DateTime)
    user_id = Column(String)
    unique_id = Column(String, unique=True)
    full_text = Column(Text)
    source_type = Column(String) 

class AnalysisChunk(AnalysisBase):  # Use analysis base model
    __tablename__ = "analyzed_chunks"
    
    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey('analyzed_documents.id'))
    chunk_index = Column(Integer)
    content = Column(Text)
    chunk_metadata = Column(Text)
    
    
# In document_model.py (AnalysisBase section)
class UserHistory(AnalysisBase):
    __tablename__ = "user_history"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    user_email = Column(String)
    user_name = Column(String)
    feature_used = Column(String)  
    case_file_name = Column(String)
    case_file_content = Column(Text)
    agent_response = Column(JSON)  # Stores the full response object
    created_at = Column(DateTime, default=datetime.utcnow)

