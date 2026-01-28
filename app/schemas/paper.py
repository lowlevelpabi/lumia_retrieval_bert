from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class PaperBase(BaseModel):
    title: str
    author: Optional[str] = None
    year: Optional[str] = None
    abstract: Optional[str] = None

class PaperCreate(PaperBase):
    file_path: str

class PaperResponse(PaperBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class SearchResult(BaseModel):
    id: int
    score: float
    payload: dict

class PaperUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[str] = None
    abstract: Optional[str] = None

