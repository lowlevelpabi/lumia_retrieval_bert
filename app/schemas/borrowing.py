from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class BorrowRecordBase(BaseModel):
    paper_id: int
    user_id: int
    due_date: datetime

class BorrowRecordCreate(BorrowRecordBase):
    pass

class BorrowRecordResponse(BorrowRecordBase):
    id: int
    borrow_date: datetime
    return_date: Optional[datetime] = None
    status: str

    class Config:
        from_attributes = True

class PenaltyBase(BaseModel):
    user_id: int
    borrow_record_id: int
    amount: float
    reason: str

class PenaltyCreate(PenaltyBase):
    pass

class PenaltyResponse(PenaltyBase):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_papers: int
    total_theses: int
    total_capstone: int
    active_borrows: int
    total_penalties: float
