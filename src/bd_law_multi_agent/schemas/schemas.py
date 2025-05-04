# bd_law_multi_agent/schemas/schemas.py
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional

class UrlRequest(BaseModel):
    """Schema for URL request"""
    url: HttpUrl
    description: Optional[str] = None

class SearchQuery(BaseModel):
    """Schema for search query"""
    query_text: str = Field(..., description="The search query text")
    limit: Optional[int] = Field(5, description="Maximum number of results to return")

class DocumentMetadata(BaseModel):
    """Schema for document metadata"""
    document_id: str
    source_type: str
    source_path: str
    score: Optional[float] = None
    text_preview: Optional[str] = None
    description: Optional[str] = None

class DocumentResponse(BaseModel):
    """Schema for document response"""
    document_id: str
    source_type: str
    source_path: str
    description: Optional[str] = None
    text_preview: Optional[str] = None

class SearchResult(BaseModel):
    """Schema for search results"""
    query: str
    results: List[DocumentMetadata]