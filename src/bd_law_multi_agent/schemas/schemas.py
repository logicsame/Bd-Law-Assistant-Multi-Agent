# bd_law_multi_agent/schemas/schemas.py
from pydantic import BaseModel, Field, HttpUrl
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