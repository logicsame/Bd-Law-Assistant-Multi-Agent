
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ConflictResponse(BaseModel):
    conflicts_detected: bool
    explanation: str
    entities_found: List[str]
    conflicts: List[Dict[str, Any]]
    trace_url: Optional[str] = None
    case_title: Optional[str] = None
