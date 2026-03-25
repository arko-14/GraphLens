from pydantic import BaseModel

class SearchQuery(BaseModel):
    query: str
    top_k: int = 5

class EntityLookupQuery(BaseModel):
    entity_id: str
    entity_type: str
