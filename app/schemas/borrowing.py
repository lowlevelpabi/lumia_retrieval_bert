from app.core.hash import encode_id
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime

class BorrowRecordBase(BaseModel):
    paper_id: str
    user_id: int
    due_date: datetime

class BorrowRecordCreate(BorrowRecordBase):
    pass

class BorrowRecordResponse(BorrowRecordBase):
    id: int
    paper_id: str
    borrow_date: datetime
    return_date: Optional[datetime] = None
    status: str

    @field_validator('paper_id', mode='before')
    def encode_db_paper_id(cls, v):
        if isinstance(v, int):
            return encode_id(v)
        return v

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
