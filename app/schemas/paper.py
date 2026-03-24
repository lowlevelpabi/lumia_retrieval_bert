from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict
from datetime import datetime
from app.core.hash import encode_id


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
    uploaded_by: Optional[str] = None
    uploader_role: Optional[str] = None

    # Full extracted text (regular view)
    introduction: Optional[str] = None
    methods: Optional[str] = None
    results: Optional[str] = None
    discussion: Optional[str] = None

    # AI summaries (IMRAD 2-column view)
    introduction_summary: Optional[str] = None
    methods_summary: Optional[str] = None
    results_summary: Optional[str] = None
    discussion_summary: Optional[str] = None


class PaperCreate(PaperBase):
    file_path: str


class PaperResponse(PaperBase):
    id: str  # Encoded string ID
    created_at: datetime

    @field_validator('id', mode='before')
    def encode_db_id(cls, v):
        if isinstance(v, int):
            return encode_id(v)
        return v

    class Config:
        from_attributes = True


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

    # Full text sections (editable)
    introduction: Optional[str] = None
    methods: Optional[str] = None
    results: Optional[str] = None
    discussion: Optional[str] = None

    # Summaries (editable / regeneratable)
    introduction_summary: Optional[str] = None
    methods_summary: Optional[str] = None
    results_summary: Optional[str] = None
    discussion_summary: Optional[str] = None


# ── IMRAD View ────────────────────────────────────────────────────────────────

class IMRADSectionContent(BaseModel):
    """
    Content for one IMRAD section in the 2-column view.
    `summary` is the AI-generated shortened version.
    `full_text` is the original extracted text (shown if summary is unavailable).
    `summary_ready` tells the frontend whether to show the summarised or raw text.
    """
    summary: Optional[str] = None
    full_text: Optional[str] = None
    summary_ready: bool = False


class IMRADViewResponse(BaseModel):
    """
    Response shape for the 2-column IMRAD view endpoint.
    Each section has both the summary and the full text available.
    """
    paper_id: str
    title: str
    author: Optional[str] = None
    year: Optional[str] = None

    introduction: IMRADSectionContent = IMRADSectionContent()
    methods: IMRADSectionContent = IMRADSectionContent()
    results: IMRADSectionContent = IMRADSectionContent()
    discussion: IMRADSectionContent = IMRADSectionContent()

    @classmethod
    def from_paper(cls, paper) -> "IMRADViewResponse":
        """
        Build IMRADViewResponse from a Paper ORM object.
        Uses *_summary if available, otherwise falls back to full section text.
        """
        def _section(full: Optional[str], summary: Optional[str]) -> IMRADSectionContent:
            return IMRADSectionContent(
                full_text=full,
                summary=summary,
                summary_ready=bool(summary and summary.strip()),
            )

        paper_id = encode_id(paper.id) if isinstance(paper.id, int) else paper.id

        return cls(
            paper_id=paper_id,
            title=paper.title,
            author=paper.author,
            year=paper.year,
            introduction=_section(paper.introduction, paper.introduction_summary),
            methods=_section(paper.methods, paper.methods_summary),
            results=_section(paper.results, paper.results_summary),
            discussion=_section(paper.discussion, paper.discussion_summary),
        )


# ── Upload flow ───────────────────────────────────────────────────────────────

class SearchResult(BaseModel):
    id: str
    score: float
    payload: dict

    @field_validator('id', mode='before')
    def encode_db_id(cls, v):
        if isinstance(v, int):
            return encode_id(v)
        return v


class CitationStatus(BaseModel):
    has_cited: bool
    citation_count: int


class ViewCountResponse(BaseModel):
    view_count: int


class PagePreview(BaseModel):
    page_num: int
    thumbnail: str  # base64
    preview_text: str


class UploadPreviewResponse(BaseModel):
    session_id: str
    metadata: dict
    pages: List[PagePreview]
    sections: Optional[Dict[str, Optional[str]]] = None             # Extracted IMRAD full text
    sections_summary: Optional[Dict[str, Optional[str]]] = None     # Pre-generated summaries
    section_pages: Optional[Dict[str, List[int]]] = None            # Section → page numbers


class UploadConfirm(BaseModel):
    session_id: str
    metadata: dict
    selected_pages: List[int]

    # Optional manual IMRAD overrides from the review step
    introduction: Optional[str] = None
    methods: Optional[str] = None
    results: Optional[str] = None
    discussion: Optional[str] = None

    # Pre-generated summaries from the preview step — saved directly to DB
    sections_summary: Optional[Dict[str, Optional[str]]] = None