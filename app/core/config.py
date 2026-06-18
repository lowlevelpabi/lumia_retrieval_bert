import os
import secrets
from pydantic_settings import BaseSettings
from pydantic import model_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Research API"
    DATABASE_URL: str = "sqlite:///./thesis.db"
    
    QDRANT_PATH: str = "./qdrant_storage"
    QDRANT_URL: str = ""  # Set to http://service:6333 for server mode
    UPLOAD_DIR: str = "uploads"
    COLLECTION_NAME: str = "thesis_papers"
    DEFAULT_SEARCH_THRESHOLD: float = 0.15
    RECOMMENDATION_THRESHOLD: float = 0.25

    # ── Evaluation Guard Rails ────────────────────────────────────────────────
    # Controls the instant termination of duplicate uploads (Title, Author, Year).
    # Set to False during evaluation week to allow multiple evaluators to upload 
    # the same document for pipeline testing.
    STRICT_DUPLICATE_CHECK: bool = True

    # ── Sample Documents (System Evaluation Feature) ──────────────────────────
    # Set to True only during system evaluation. When False, the sample document
    # endpoints return empty/404 and the UI panel is hidden automatically.
    ENABLE_SAMPLE_DOCS: bool = False
    SAMPLE_DOCS_DIR: str = "sample_documents"
    
    # SECRET_KEY must be set in .env for production.
    # Falls back to a random key for local dev (tokens won't survive restarts).
    SECRET_KEY: str = secrets.token_hex(32)
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