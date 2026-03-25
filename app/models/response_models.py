from pydantic import BaseModel
from typing import List, Dict, Any

class SearchResult(BaseModel):
    answer: str
    context_used: List[Dict[str, Any]] = []

class EntityDetails(BaseModel):
    properties: Dict[str, Any]
    relationships: List[Dict[str, Any]]
