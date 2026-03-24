from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.api.deps import faculty_or_admin_required
from app.models.activity_log import ActivityLog

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