import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Research API"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./thesis.db")
    # Fix for Railway/PostgreSQL: replace postgres:// with postgresql:// if needed
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    QDRANT_PATH: str = "./qdrant_storage"
    COLLECTION_NAME: str = "thesis_papers"
    
    SECRET_KEY: str = "SUPER_SECRET_KEY_REPLACE_THIS_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()