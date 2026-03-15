from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.api.endpoints import papers, auth, users, borrowing
from app.core.database import init_db, engine

app = FastAPI(title=settings.PROJECT_NAME)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; refine for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# @app.on_event("startup")
# def startup_event():
#     init_db()

@app.get("/")
def read_root():
    return {"message": "Welcome to Smart Research API"}

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(papers.router, prefix="/api/v1/papers", tags=["papers"])
app.include_router(borrowing.router, prefix="/api/v1/borrowing", tags=["borrowing"])