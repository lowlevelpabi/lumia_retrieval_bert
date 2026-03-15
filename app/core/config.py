import os
from pydantic_settings import BaseSettings

from pydantic import model_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Research API"
    DATABASE_URL: str = "sqlite:///./thesis.db"
    
    QDRANT_PATH: str = "./qdrant_storage"
    COLLECTION_NAME: str = "thesis_papers"
    
    SECRET_KEY: str = "SUPER_SECRET_KEY_REPLACE_THIS_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    @model_validator(mode='after')
    def validate_database_url(self) -> 'Settings':
        if self.DATABASE_URL.startswith("postgres://"):
            self.DATABASE_URL = self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return self

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()