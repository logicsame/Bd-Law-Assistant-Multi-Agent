from pydantic import BaseModel
from typing import List
from bd_law_multi_agent.schemas.analyze_sc import DocumentSource

class ChatbotRequest(BaseModel):
    query: str

class ChatbotResponse(BaseModel):
    response_type: str  
    response: str
    sources: List[DocumentSource]