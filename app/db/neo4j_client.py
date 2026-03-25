from neo4j import GraphDatabase
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class Neo4jClient:
    def __init__(self):
        # Ultra-conservative settings for Aura Free tier stability
        try:
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
                max_connection_pool_size=5,  # Minimized pool for Aura Free
                max_connection_lifetime=60,   # Cycle connections before Aura idle timeout (90s)
                connection_timeout=60,       # Wait up to 60s for initial connect
                keep_alive=True               # Keep the TCP pipe warm
            )
            # Verify connectivity immediately
            self.driver.verify_connectivity()
            logger.info("Neo4j Driver initialized and verified for Aura Cloud.")
        except Exception as e:
            logger.error(f"Neo4j Driver initialization FAILED: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def execute_query(self, query, parameters=None):
        if not self.driver:
            raise Exception("Neo4j Driver not initialized.")
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]

    def execute_write(self, query, parameters=None):
        """Used for write operations with built-in retry logic."""
        if not self.driver:
            raise Exception("Neo4j Driver not initialized.")
        with self.driver.session() as session:
            # Aura requires session.execute_write for managed transactions/retries
            return session.execute_write(lambda tx: tx.run(query, parameters or {}).consume())

neo4j_client = Neo4jClient()
