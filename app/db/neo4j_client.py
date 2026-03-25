from neo4j import GraphDatabase
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class Neo4jClient:
    def __init__(self):
        # Optimized for Aura free tier (prevent pool exhaustion)
        self._driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.neo4j_user, settings.NEO4J_PASSWORD),
            max_connection_pool_size=10, 
            connection_timeout=60.0
        )

    def close(self):
        self._driver.close()

    def verify_connectivity(self):
        try:
            self._driver.verify_connectivity()
            logger.info("Connected to Neo4j successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False

    def execute_query(self, query: str, parameters=None):
        if parameters is None:
            parameters = {}
        with self._driver.session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]

    def execute_write(self, query: str, parameters=None):
        if parameters is None:
            parameters = {}
        with self._driver.session() as session:
            # execute_write has built-in retry logic
            result = session.execute_write(lambda tx: list(tx.run(query, parameters)))
            return result

neo4j_client = Neo4jClient()
