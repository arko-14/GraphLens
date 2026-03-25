from app.db.neo4j_client import neo4j_client
import logging

logging.basicConfig(level=logging.INFO)

def test_queries():
    # 1. Check total node counts
    count_query = "MATCH (n) RETURN count(n) as total_nodes"
    res = neo4j_client.execute_query(count_query)
    logging.info(f"Total Nodes: {res[0]['total_nodes']}")
    
    # 2. Trace flow test
    flow = """
    MATCH path = (s:SalesOrder)-[*..4]-(b:BillingDocument)
    RETURN length(path) as hops LIMIT 1
    """
    flow_res = neo4j_client.execute_query(flow)
    logging.info(f"Test Flow Query Hops Result: {flow_res}")

if __name__ == "__main__":
    test_queries()
