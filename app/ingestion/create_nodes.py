from app.db.neo4j_client import neo4j_client
from typing import List, Dict, Any
import logging
import time

logger = logging.getLogger(__name__)

def create_nodes(label: str, nodes: List[Dict[str, Any]], batch_size: int = 100):
    """Batch creates nodes of a specific label with retry logic for Aura."""
    if not nodes:
        return
    
    query = f"""
    UNWIND $nodes AS row
    MERGE (n:{label} {{id: row.id}})
    SET n += row
    """
    
    for i in range(0, len(nodes), batch_size):
        batch = nodes[i : i + batch_size]
        success = False
        retries = 3
        
        while not success and retries > 0:
            try:
                neo4j_client.execute_write(query, {"nodes": batch})
                success = True
                logger.info(f"Loaded batch {i//batch_size + 1} ({len(batch)} nodes) of {label}.")
            except Exception as e:
                retries -= 1
                logger.warning(f"Error loading {label} batch (retrying in 2s): {e}")
                time.sleep(2)
        
        if not success:
            logger.error(f"FAILED to load {label} batch after retries.")
        
        # Small sleep between batches to avoid overwhelming Aura free tier
        time.sleep(0.5)
