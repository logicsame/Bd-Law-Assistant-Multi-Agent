
from pydantic import BaseModel,Field
from typing import List

class ArgumentRequest(BaseModel):
    case_details: str

class ArgumentSource(BaseModel):
    source: str
    excerpt: str

class ArgumentResponse(BaseModel):
    argument: str
    legal_category: str
    sources: List[ArgumentSource]


class ArgumentResponse(BaseModel):
    argument: str
    legal_category: str
    sources: List[ArgumentSource]