from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timezone
from app.models.paper import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id           = Column(Integer, primary_key=True, index=True)
    action       = Column(String, nullable=False)          # "Upload" | "Edit" | "Delete" | "Restore" | "Purge"
    paper_title  = Column(String, nullable=False)
    performed_by = Column(String, nullable=False)          # username
    performed_by_role = Column(String, nullable=True)
    performed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))