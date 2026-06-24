from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.endpoints import papers, auth, users
from app.api.endpoints import logs
from app.core.database import init_db, engine
from app.models import activity_log  # ensure table is created by init_db
from app.services.cleanup_service import start_cleanup_loop
import asyncio


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    # Launch the 15-day trash cleanup as a fire-and-forget background task.
    # It runs an immediate purge pass, then loops every 24 hours.
    asyncio.create_task(start_cleanup_loop())
    yield
    # ── Shutdown (nothing to clean up) ───────────────────────────────────────


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; refine for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Lumia Smart Research API"}

@app.get("/api/v1/system/info")
def get_system_info():
    return {
        "version": "1.2.0",
        "academic_year": "2025-2026",
        "release_date": "2026-06-24",
        "department": "Department of Computer Studies",
        "changelog": [
            {
                "version": "1.2.0",
                "date": "2026-06-24",
                "title": "Turnover Release & Documentation Integration",
                "changes": [
                    "Implemented dynamic system metadata and versioning API endpoints for UI synchronization",
                    "Optimized institutional repository landing layout and metadata displays for turnover compliance",
                    "Added compressed archive exclusions (*.rar, *.zip) to global repository ignore rules",
                    "Restructured environment configuration tracking and decoupled active runtime system logging"
                ]
            },
            {
                "version": "1.1.1",
                "date": "2026-04-15",
                "title": "Oral Defense Stable Build",
                "changes": [
                    "Resolved minor panel evaluation feedback on text trimming thresholds",
                    "Stabilized database connection polling rate for local deployment",
                    "Optimized PDF page rendering pipeline speeds"
                ]
            },
            {
                "version": "1.1.0",
                "date": "2026-03-10",
                "title": "UI/UX Layout Overhaul",
                "changes": [
                    "Implemented 3-step document upload flow with thumbnail previews",
                    "Redesigned filter sidebar and exploration portals",
                    "Added dark/light theme syncing across components"
                ]
            },
            {
                "version": "1.0.0",
                "date": "2026-02-25",
                "title": "Defended System Baseline",
                "changes": [
                    "First stable integration of BERT-NLP embeddings and Qdrant database",
                    "Completed User Privilege Matrix and RBAC gatekeepers",
                    "Setup multi-vector IMRAD structural segmenting"
                ]
            }
        ]
    }

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(papers.router, prefix="/api/v1/papers", tags=["papers"])
app.include_router(logs.router, prefix="/api/v1/logs", tags=["logs"])