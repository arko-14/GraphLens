from app.db.neo4j_client import neo4j_client

class GraphSearchService:
    def get_neighbors(self, node_id: str, hops: int = 1):
        query = f"MATCH (n {{id: $node_id}})-[*1..{hops}]-(m) RETURN DISTINCT m.id AS id, labels(m)[0] AS label"
        return neo4j_client.execute_query(query, {"node_id": node_id})

graph_search_service = GraphSearchService()
