from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Research API"
    DATABASE_URL: str = "sqlite:///./thesis.db"
    QDRANT_PATH: str = "./qdrant_storage"
    COLLECTION_NAME: str = "thesis_papers"
    
    class Config:
        env_file = ".env"

settings = Settings()
