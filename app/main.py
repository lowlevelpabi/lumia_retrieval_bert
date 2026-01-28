from fastapi import FastAPI
from app.core.config import settings
from app.api.endpoints import papers
from app.core.database import init_db

app = FastAPI(title=settings.PROJECT_NAME)

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/")
def read_root():
    return {"message": "Welcome to Smart Research API"}

app.include_router(papers.router, prefix="/api/v1/papers", tags=["papers"])
