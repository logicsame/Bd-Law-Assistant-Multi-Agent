from sqlalchemy import Column, String, Text, ForeignKey, Integer, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from bd_law_multi_agent.database.database import Base

class Document(Base):
    """Document storage model"""
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    source_type = Column(String, nullable=False)
    source_path = Column(String, nullable=False)
    description = Column(Text)
    text_preview = Column(Text)  # For initial preview text
    full_text = Column(Text)     # For complete text from background processing
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
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