# bd_law_multi_agent/schemas/schemas.py
from pydantic import BaseModel, Field, HttpUrl,EmailStr, conlist
from typing import List, Optional, Dict, Any
from datetime import datetime

class UrlRequest(BaseModel):
    """Schema for URL request"""
    url: HttpUrl
    description: Optional[str] = None

class SearchQuery(BaseModel):
    """
    Schema for search query requests
    """
    query_text: str = Field(..., description="Text to search for")
    limit: Optional[int] = Field(5, description="Maximum number of results to return")


class DocumentResult(BaseModel):
    """
    Schema for search result document
    """
    document_id: str
    source_type: str
    source_path: str
    score: float
    text_preview: str
    description: Optional[str] = None


class SearchResult(BaseModel):
    """
    Schema for search response
    """
    query: str
    results: List[DocumentResult]




    
    
class UserBase(BaseModel):
    """Base user model with common attributes"""
    email: EmailStr
    is_active: Optional[bool] = True
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """User model for creation with password"""
    password: str = Field(..., min_length=8)


class UserUpdate(UserBase):
    """User model for updates"""
    password: Optional[str] = Field(None, min_length=8)


class UserInDB(UserBase):
    """User model in database with hashed password"""
    id: str
    hashed_password: str

    model_config = {
        "from_attributes": True
    }


class User(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    is_active: bool

    class Config:
        orm_mode = True
        from_attributes = True

class DocumentResponse(BaseModel):
    id: str  # Changed from document_id to match model
    source_type: str
    source_path: str
    description: Optional[str] = None
    text_preview: str
    created_at: datetime
    owner: User

    class Config:
        from_attributes = True  # For Pydantic v2 (orm_mode renamed)
        populate_by_name = True  # Allow alias population
class Token(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    """Token payload model"""
    sub: Optional[str] = None
    exp: Optional[int] = None
    
    
class DocumentBase(BaseModel):
    document_id: str
    source_type: str
    source_path: str
    description: Optional[str] = None
    created_at: datetime

class DocumentChunkBase(BaseModel):
    chunk_index: int
    content: str
    chunk_metadata: Dict[str, Any] 


class DocumentCreate(BaseModel):
    source_type: str
    source_path: str
    description: Optional[str] = None