from qdrant_client import QdrantClient
from pydantic import BaseSettings

class Settings(BaseSettings):
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

settings = Settings()

def get_qdrant_client():
    return QdrantClient(url=f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
