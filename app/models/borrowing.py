from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.models.paper import Base
from datetime import datetime

class BorrowRecord(Base):
    __tablename__ = "borrow_records"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    borrow_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime)
    return_date = Column(DateTime, nullable=True)
    status = Column(String, default="Borrowed") # Borrowed, Returned, Overdue

    paper = relationship("Paper")
    user = relationship("User")

class Penalty(Base):
    __tablename__ = "penalties"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    borrow_record_id = Column(Integer, ForeignKey("borrow_records.id"))
    amount = Column(Float, default=0.0)
    reason = Column(String)
    status = Column(String, default="Unpaid") # Unpaid, Paid
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    borrow_record = relationship("BorrowRecord")
