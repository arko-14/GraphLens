from app.db.neo4j_client import neo4j_client
from typing import List

class VectorSearchService:
    def search_similar(self, embedding: List[float], top_k: int = 5):
        query = """
        CALL db.index.vector.queryNodes('product_embedding_idx', $top_k, $embedding)
        YIELD node, score
        RETURN node.id AS id, score
        """
        return neo4j_client.execute_query(query, {"embedding": embedding, "top_k": top_k})

vector_search_service = VectorSearchService()
