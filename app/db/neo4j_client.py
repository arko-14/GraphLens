from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class Neo4jClient:
    def __init__(self):
        # Optimized for Aura free tier stability
        try:
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
                max_connection_pool_size=5,  # Minimized pool for Aura Free
                max_connection_lifetime=60,   # Cycle connections before Aura idle timeout (90s)
                connection_timeout=60,       # Wait up to 60s for initial connect
                keep_alive=True               # Keep the TCP pipe warm
            )
            # We don't call verify_connectivity() here to avoid blocking Render's boot
            # if Aura is still waking up. The first query will handle it via retries.
            logger.info("Neo4j Driver initialized (Aura-optimized).")
        except Exception as e:
            logger.error(f"Neo4j Driver initialization error: {e}")
            # We keep the driver object if it exists, or None only if it failed to even create
            if not hasattr(self, 'driver'):
                self.driver = None

    def close(self):
        if hasattr(self, 'driver') and self.driver:
            self.driver.close()

    def execute_query(self, query, parameters=None):
        if not hasattr(self, 'driver') or not self.driver:
            raise ServiceUnavailable("Neo4j Driver not initialized.")
        
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]

    def execute_write(self, query, parameters=None):
        """Used for write operations with built-in retry logic."""
        if not hasattr(self, 'driver') or not self.driver:
            raise ServiceUnavailable("Neo4j Driver not initialized.")
        
        with self.driver.session() as session:
            # Aura requires session.execute_write for managed transactions/retries
            return session.execute_write(lambda tx: tx.run(query, parameters or {}).consume())

neo4j_client = Neo4jClient()
