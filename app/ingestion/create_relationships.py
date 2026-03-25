from app.db.neo4j_client import neo4j_client
from typing import List, Dict, Any
import logging
import time

logger = logging.getLogger(__name__)

def create_relationships(rel_type: str, from_label: str, to_label: str, edges: List[Dict[str, Any]], batch_size: int = 100):
    """Batch creates relationships with retry logic for Aura."""
    if not edges:
        return
        
    query = f"""
    UNWIND $edges AS row
    MATCH (a:{from_label} {{id: row.from_id}})
    MATCH (b:{to_label} {{id: row.to_id}})
    MERGE (a)-[r:{rel_type}]->(b)
    SET r += row.properties
    """
    
    # Pre-process edges to ensure properties field exists
    for edge in edges:
        if "properties" not in edge:
            edge["properties"] = {}

    for i in range(0, len(edges), batch_size):
        batch = edges[i : i + batch_size]
        success = False
        retries = 3
        
        while not success and retries > 0:
            try:
                neo4j_client.execute_write(query, {"edges": batch})
                success = True
                logger.info(f"Loaded batch {i//batch_size + 1} ({len(batch)} edges) of {rel_type}.")
            except Exception as e:
                retries -= 1
                logger.warning(f"Error loading {rel_type} batch (retrying in 2s): {e}")
                time.sleep(2)
        
        if not success:
            logger.error(f"FAILED to load {rel_type} batch after retries.")
            
        time.sleep(0.5)
