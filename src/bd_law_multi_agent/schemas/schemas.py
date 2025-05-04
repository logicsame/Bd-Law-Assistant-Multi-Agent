# bd_law_multi_agent/schemas/schemas.py
from pydantic import BaseModel, Field, HttpUrl,EmailStr
from typing import List, Optional

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


class DocumentResponse(BaseModel):
    """
    Schema for document upload response
    """
    document_id: str
    source_type: str
    source_path: str
    text_preview: str
    description: Optional[str] = None
    
    
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


class User(UserBase):
    """User model for API responses"""
    id: str

    model_config = {
        "from_attributes": True
    }


class Token(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    """Token payload model"""
    sub: Optional[str] = None
    exp: Optional[int] = None