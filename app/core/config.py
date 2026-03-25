import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_USERNAME: str = ""          # Aura uses this key — aliased below
    NEO4J_PASSWORD: str = "password"
    GROQ_API_KEY: str = ""

    @property
    def neo4j_user(self) -> str:
        """Return whichever key is set — Aura uses NEO4J_USERNAME, local uses NEO4J_USER."""
        return self.NEO4J_USERNAME or self.NEO4J_USER

    class Config:
        env_file = ".env"
        extra = "ignore"   # silently ignore unknown keys like AURA_INSTANCEID etc.

settings = Settings()
