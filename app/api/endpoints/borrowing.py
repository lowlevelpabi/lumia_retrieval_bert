from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.borrowing import BorrowRecord, Penalty
from app.models.paper import Paper
from app.schemas.borrowing import (
    BorrowRecordCreate, BorrowRecordResponse,
    PenaltyCreate, PenaltyResponse, DashboardStats
)
from app.api.deps import admin_required, faculty_or_admin_required, get_current_user

router = APIRouter()

# ── Borrow Records ────────────────────────────────────────────────

@router.post("/", response_model=BorrowRecordResponse, dependencies=[Depends(faculty_or_admin_required)])
async def create_borrow_record(data: BorrowRecordCreate, db: Session = Depends(get_db)):
    # Check if paper exists
    paper = db.query(Paper).filter(Paper.id == data.paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    db_record = BorrowRecord(
        paper_id=data.paper_id,
        user_id=data.user_id,
        due_date=data.due_date,
        status="Borrowed"
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record

@router.get("/", response_model=List[BorrowRecordResponse], dependencies=[Depends(faculty_or_admin_required)])
async def list_borrow_records(db: Session = Depends(get_db)):
    return db.query(BorrowRecord).all()

@router.put("/{record_id}/return", response_model=BorrowRecordResponse, dependencies=[Depends(faculty_or_admin_required)])
async def return_book(record_id: int, db: Session = Depends(get_db)):
    db_record = db.query(BorrowRecord).filter(BorrowRecord.id == record_id).first()
    if not db_record:
        raise HTTPException(status_code=404, detail="Borrow record not found")
    
    db_record.return_date = datetime.utcnow()
    db_record.status = "Returned"
    db.commit()
    db.refresh(db_record)
    return db_record

# ── Penalties ─────────────────────────────────────────────────────

@router.post("/penalties", response_model=PenaltyResponse, dependencies=[Depends(faculty_or_admin_required)])
async def create_penalty(data: PenaltyCreate, db: Session = Depends(get_db)):
    db_penalty = Penalty(
        user_id=data.user_id,
        borrow_record_id=data.borrow_record_id,
        amount=data.amount,
        reason=data.reason,
        status="Unpaid"
    )
    db.add(db_penalty)
    db.commit()
    db.refresh(db_penalty)
    return db_penalty

@router.get("/penalties", response_model=List[PenaltyResponse], dependencies=[Depends(faculty_or_admin_required)])
async def list_penalties(db: Session = Depends(get_db)):
    return db.query(Penalty).all()

@router.put("/penalties/{penalty_id}/pay", response_model=PenaltyResponse, dependencies=[Depends(faculty_or_admin_required)])
async def pay_penalty(penalty_id: int, db: Session = Depends(get_db)):
    db_penalty = db.query(Penalty).filter(Penalty.id == penalty_id).first()
    if not db_penalty:
        raise HTTPException(status_code=404, detail="Penalty not found")
    
    db_penalty.status = "Paid"
    db.commit()
    db.refresh(db_penalty)
    return db_penalty

# ── Dashboard Stats ───────────────────────────────────────────────

@router.get("/dashboard/stats", response_model=DashboardStats, dependencies=[Depends(faculty_or_admin_required)])
async def get_dashboard_stats(db: Session = Depends(get_db)):
    total_papers = db.query(Paper).count()
    total_theses = db.query(Paper).filter(Paper.project_type == "Thesis").count()
    total_capstone = db.query(Paper).filter(Paper.project_type == "Capstone Project").count()
    active_borrows = db.query(BorrowRecord).filter(BorrowRecord.status == "Borrowed").count()
    total_penalties = db.query(func.sum(Penalty.amount)).filter(Penalty.status == "Unpaid").scalar() or 0.0
    
    return {
        "total_papers": total_papers,
        "total_theses": total_theses,
        "total_capstone": total_capstone,
        "active_borrows": active_borrows,
        "total_penalties": total_penalties
    }
