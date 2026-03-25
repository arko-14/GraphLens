from app.db.neo4j_client import neo4j_client

class ReasoningService:
    def check_flow_integrity(self, sales_order_id: str):
        # verifies if order has delivery and billing
        query = """
        MATCH (so:SalesOrder {id: $id})
        OPTIONAL MATCH (so)-[:HAS_ITEM]->(soi)-[:SHIPPED_IN]->(di)
        OPTIONAL MATCH (di)-[:BILLED_IN]->(bi)
        RETURN count(soi) as items, count(di) as deliveries, count(bi) as bills
        """
        return neo4j_client.execute_query(query, {"id": sales_order_id})

reasoning_service = ReasoningService()
