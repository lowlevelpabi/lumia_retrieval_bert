from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any
import time

from app.services.embedding_service import embedding_service
from app.services.vector_db import vector_db
from app.services.ocr_service import ocr_service

router = APIRouter()

class HealthStatus(BaseModel):
    status: str
    details: Dict[str, Any]

@router.get("/health", response_model=Dict[str, HealthStatus])
async def get_health():
    health = {}
    
    # 1. BERT NLP Health
    start_time = time.time()
    try:
        # Simple check: can it generate a small embedding?
        embedding_service.get_embedding("health check")
        latency = (time.time() - start_time) * 1000
        health["bert"] = {
            "status": "online",
            "details": {
                "model": "multi-qa-MiniLM-L6-cos-v1",
                "latency_ms": round(latency, 2),
                "message": "Optimal"
            }
        }
    except Exception as e:
        health["bert"] = {
            "status": "offline",
            "details": {"error": str(e), "message": "Model Error"}
        }

    # 2. Qdrant Vector DB Health
    try:
        info = vector_db.client.get_collection(vector_db.collection_name)
        health["qdrant"] = {
            "status": "online",
            "details": {
                "collection": vector_db.collection_name,
                "points_count": info.points_count,
                "message": "Connected"
            }
        }
    except Exception as e:
        health["qdrant"] = {
            "status": "offline",
            "details": {"error": str(e), "message": "Disconnected"}
        }

    # 3. OCR Service Health
    if ocr_service.tesseract_available:
        health["ocr"] = {
            "status": "online",
            "details": {
                "engine": "Tesseract",
                "message": "Active"
            }
        }
    else:
        health["ocr"] = {
            "status": "offline",
            "details": {"message": "Tesseract Not Found"}
        }

    return health
