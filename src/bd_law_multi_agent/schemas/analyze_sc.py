from pydantic import BaseModel,Field
from typing import List, Optional
from pydantic import field_validator

class AnalysisRequest(BaseModel):
    query: str

class DocumentSource(BaseModel):
    source: str
    page: str  # Keep as string but allow conversion
    excerpt: str

    @field_validator('page', mode='before')
    def convert_page_to_string(cls, value):
        return str(value) if value is not None else 'N/A'

class ClassificationDetail(BaseModel):
    primary_category: str
    secondary_category: Optional[str] = None
    complexity_level: str
    legal_domains: List[str]
    risk_assessment: str
    initial_strategy: str
    key_considerations: List[str]

class AnalysisResponse(BaseModel):
    analysis: str
    classification: ClassificationDetail  
    follow_up_questions: List[str]  
    sources: List[DocumentSource]