from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.api.deps import faculty_or_admin_required
from app.models.activity_log import ActivityLog
from app.services.logging_service import LOG_FILE
import os

router = APIRouter()


class ActivityLogResponse(BaseModel):
    id:           int
    action:       str
    paper_title:  str
    performed_by: str
    performed_by_role: Optional[str] = None
    performed_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=List[ActivityLogResponse], dependencies=[Depends(faculty_or_admin_required)])
def get_logs(db: Session = Depends(get_db)):
    """Return all activity log entries, newest first."""
    return db.query(ActivityLog).order_by(ActivityLog.performed_at.desc()).all()


@router.get("/system", dependencies=[Depends(faculty_or_admin_required)])
def get_system_logs(lines: int = 500):
    """
    Returns the last N lines of the system_logs.txt file.
    Allows remote monitoring of server activity via the web dash.
    """
    if not os.path.exists(LOG_FILE):
        return {"logs": "System log file not found."}
    
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            # Efficiently read the last N lines
            all_lines = f.readlines()
            last_lines = all_lines[-lines:]
            return {"logs": "".join(last_lines)}
    except Exception as e:
        return {"logs": f"Error reading logs: {str(e)}"}