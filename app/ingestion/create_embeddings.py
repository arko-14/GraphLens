import os
import sys
import logging
import time
from typing import List, Dict, Any

# Ensure we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.neo4j_client import neo4j_client

try:
    from fastembed import TextEmbedding
except ImportError:
    TextEmbedding = None

logger = logging.getLogger(__name__)

def generate_embeddings():
    if TextEmbedding is None:
        logger.error("fastembed is not installed. Run 'pip install fastembed'")
        return

    logger.info("Loading embedding model...")
    model = TextEmbedding("BAAI/bge-small-en-v1.5")

    # Create Vector Index for Products FIRST to ensure it's ready
    index_query = """
    CREATE VECTOR INDEX product_embedding_idx IF NOT EXISTS
    FOR (p:Product) ON (p.embedding)
    OPTIONS {indexConfig: {
      `vector.dimensions`: 384,
      `vector.similarity_function`: 'cosine'
    }}
    """
    try:
        neo4j_client.execute_write(index_query)
        logger.info("Vector index created for Product embeddings (or already exists).")
    except Exception as e:
        logger.warning(f"Could not create vector index: {e}")

    # Fetch products to embed
    logger.info("Fetching products to embed...")
    query = "MATCH (p:Product) WHERE p.description IS NOT NULL AND p.embedding IS NULL RETURN p.id AS id, p.description AS text"
    
    products = []
    success = False
    retries = 5
    while not success and retries > 0:
        try:
            products = neo4j_client.execute_query(query)
            success = True
        except Exception as e:
            retries -= 1
            logger.warning(f"Error fetching products (retrying in 5s): {e}")
            time.sleep(5)
    
    if not success:
        logger.error("FAILED to fetch products after all retries.")
        return

    if not products:
        logger.info("No new products found that need embeddings.")
    else:
        logger.info(f"Generating embeddings for {len(products)} products...")
        texts = [p['text'] for p in products]
        embeddings = list(model.embed(texts))
        updates = [{"id": p['id'], "embedding": emb.tolist()} for p, emb in zip(products, embeddings)]
        
        update_query = """
        UNWIND $updates AS row
        MATCH (p:Product {id: row.id})
        SET p.embedding = row.embedding
        """
        
        # Write updates in small batches with large delay
        batch_size = 25
        for i in range(0, len(updates), batch_size):
            batch = updates[i : i + batch_size]
            success = False
            retries = 3
            while not success and retries > 0:
                try:
                    neo4j_client.execute_write(update_query, {"updates": batch})
                    success = True
                    logger.info(f"Updated batch {i//batch_size + 1} ({len(batch)} embeddings).")
                except Exception as e:
                    retries -= 1
                    logger.warning(f"Error updating embeddings (retrying in 5s): {e}")
                    time.sleep(5)
            
            if not success:
                logger.error(f"FAILED to update embedding batch {i//batch_size + 1} after retries.")
            
            # Larger sleep to stabilize connection
            time.sleep(2.0)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_embeddings()
