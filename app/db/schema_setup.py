from app.db.neo4j_client import neo4j_client
import logging

logger = logging.getLogger(__name__)

def setup_constraints():
    labels = ["Customer", "Product", "SalesOrder", "SalesOrderItem", "Delivery", "DeliveryItem", "BillingDocument", "BillingDocumentItem", "JournalEntry", "Payment", "Plant"]
    for label in labels:
        query = f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE"
        try:
            neo4j_client.execute_write(query)
            logger.info(f"Constraint ensured for {label}.id")
        except Exception as e:
            logger.warning(f"Error setting constraint for {label}: {e}")

def create_indexes():
    # Attempt to create full text indexes
    queries = [
        "CREATE FULLTEXT INDEX productDescription IF NOT EXISTS FOR (n:Product) ON EACH [n.description]",
        "CREATE FULLTEXT INDEX customerName IF NOT EXISTS FOR (n:Customer) ON EACH [n.name]"
    ]
    for q in queries:
        try:
            neo4j_client.execute_write(q)
            logger.info(f"Index created/ensured: {q}")
        except Exception as e:
            logger.warning(f"Error setting index: {e}")

if __name__ == "__main__":
    setup_constraints()
    create_indexes()
