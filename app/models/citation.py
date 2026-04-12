from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, DateTime, String
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.models.paper import Base


class UserCitation(Base):
    __tablename__ = "user_citations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now)

    __table_args__ = (
        UniqueConstraint("user_id", "paper_id", name="unique_user_paper_citation"),
    )
