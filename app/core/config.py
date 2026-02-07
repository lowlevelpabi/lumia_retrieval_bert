from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Research API"
    DATABASE_URL: str = "sqlite:///./thesis.db"
    QDRANT_PATH: str = "./qdrant_storage"
    COLLECTION_NAME: str = "thesis_papers"
    
    # Security
    SECRET_KEY: str = "SUPER_SECRET_KEY_REPLACE_THIS_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours
    
    class Config:
        env_file = ".env"

settings = Settings()
