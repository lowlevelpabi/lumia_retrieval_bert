from pydantic import BaseModel
from typing import Optional, List, Dict
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
    
    # IMRAD sections
    introduction: Optional[str] = None
    methods: Optional[str] = None
    results: Optional[str] = None
    discussion: Optional[str] = None

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
    
    # IMRAD sections
    introduction: Optional[str] = None
    methods: Optional[str] = None
    results: Optional[str] = None
    discussion: Optional[str] = None

class PagePreview(BaseModel):
    page_num: int
    thumbnail: str  # base64
    preview_text: str

class UploadPreviewResponse(BaseModel):
    session_id: str
    metadata: dict
    pages: List[PagePreview]
    sections: Optional[Dict[str, str]] = None  # Extracted IMRAD text
    section_pages: Optional[Dict[str, List[int]]] = None  # Mapping of section to page numbers

class UploadConfirm(BaseModel):
    session_id: str
    metadata: dict
    selected_pages: List[int]
    
    # Optional manual IMRAD overrides from the review step
    introduction: Optional[str] = None
    methods: Optional[str] = None
    results: Optional[str] = None
    discussion: Optional[str] = None

