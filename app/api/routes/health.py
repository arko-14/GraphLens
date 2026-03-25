from fastapi import APIRouter
from app.db.neo4j_client import neo4j_client
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/")
async def health_check():
    neo4j_status = "error"
    try:
        # Simple query to keep-alive Aura and verify connection
        neo4j_client.execute_query("MATCH (n) RETURN count(n) LIMIT 1")
        neo4j_status = "online"
    except Exception as e:
        logger.error(f"Health check Neo4j ping failed: {e}")
    
    return {
        "status": "ok",
        "database": neo4j_status,
        "mode": "production"
    }
