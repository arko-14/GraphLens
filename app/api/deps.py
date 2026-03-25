from fastapi import Depends
from app.db.neo4j_client import Neo4jClient, neo4j_client

# Fastapi Dependency for Neo4j Client
def get_neo4j_client() -> Neo4jClient:
    return neo4j_client
