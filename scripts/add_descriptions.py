import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from app.db.neo4j_client import neo4j_client
from app.ingestion.parse_dataset import iter_jsonl_folder
from app.ingestion.clean_data import clean_dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join("data", "raw", "sap-order-to-cash-dataset", "sap-o2c-data")

def ingest_descriptions():
    updates = []
    for row in iter_jsonl_folder(DATA_DIR, "product_descriptions"):
        cleaned = clean_dict(row)
        if cleaned.get("language") == "EN" and cleaned.get("productDescription"):
            updates.append({
                "id": cleaned.get("product"),
                "description": cleaned.get("productDescription")
            })
            
    if updates:
        query = """
        UNWIND $updates AS row
        MATCH (p:Product {id: row.id})
        SET p.description = row.description
        """
        neo4j_client.execute_write(query, {"updates": updates})
        logger.info(f"Loaded descriptions for {len(updates)} products.")

if __name__ == "__main__":
    ingest_descriptions()
