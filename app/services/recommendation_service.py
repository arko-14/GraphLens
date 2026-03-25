from app.db.neo4j_client import neo4j_client

class RecommendationService:
    def recommend_products(self, customer_id: str):
        # find products bought by others who bought similar things
        query = """
        MATCH (c:Customer {id: $customer_id})-[:PLACED_ORDER]->()-[:HAS_ITEM]->()-[:REQUESTS_PRODUCT]->(p:Product)
        MATCH (p)<-[:REQUESTS_PRODUCT]-()<-[:HAS_ITEM]-()<-[:PLACED_ORDER]-(other:Customer)-[:PLACED_ORDER]->()-[:HAS_ITEM]->()-[:REQUESTS_PRODUCT]->(rec:Product)
        WHERE NOT (c)-[:PLACED_ORDER]->()-[:HAS_ITEM]->()-[:REQUESTS_PRODUCT]->(rec)
        RETURN rec.id AS id, rec.description AS description, count(*) AS score
        ORDER BY score DESC LIMIT 5
        """
        return neo4j_client.execute_query(query, {"customer_id": customer_id})

recommendation_service = RecommendationService()
