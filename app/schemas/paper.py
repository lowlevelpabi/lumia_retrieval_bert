from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class PaperBase(BaseModel):
    title: str
    author: Optional[str] = None
    year: Optional[str] = None
    abstract: Optional[str] = None
    department: Optional[str] = "N/A"
    keywords: Optional[str] = ""
    project_type: Optional[str] = "N/A"
    degree_program: Optional[str] = "N/A"
    citation_count: Optional[int] = 0
    view_count: Optional[int] = 0

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

class CitationStatus(BaseModel):
    has_cited: bool
    citation_count: int

class ViewCountResponse(BaseModel):
    view_count: int

class PaperUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[str] = None
    abstract: Optional[str] = None
    department: Optional[str] = None
    keywords: Optional[str] = None
    project_type: Optional[str] = None
    degree_program: Optional[str] = None
    citation_count: Optional[int] = None

class PagePreview(BaseModel):
    page_num: int
    thumbnail: str  # base64
    preview_text: str

class UploadPreviewResponse(BaseModel):
    session_id: str
    metadata: dict
    pages: List[PagePreview]

class UploadConfirm(BaseModel):
    session_id: str
    metadata: dict
    selected_pages: List[int]

