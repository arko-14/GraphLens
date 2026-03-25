from fastapi import APIRouter
from pydantic import BaseModel
from app.services.hybrid_retrieval_service import hybrid_retrieval_service

router = APIRouter()

from typing import List, Dict, Optional

class SearchRequest(BaseModel):
    query: str
    history: Optional[List[Dict[str, str]]] = []

class SearchResponse(BaseModel):
    answer: str
    nodes: Optional[List[dict]] = []

@router.post("/", response_model=SearchResponse)
async def perform_search(request: SearchRequest):
    result = hybrid_retrieval_service.handle_search(request.query, request.history)
    return SearchResponse(answer=result["answer"], nodes=result["nodes"])
