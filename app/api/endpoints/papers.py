from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import Integer, or_
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import shutil
import os
import uuid
import math
from qdrant_client.http import models

from app.core.config import settings
from app.core.database import get_db
from app.models.paper import Paper
from app.models.citation import UserCitation
from app.schemas.paper import (
    PaperResponse, SearchResult, PaperUpdate, CitationStatus, 
    ViewCountResponse, UploadPreviewResponse, UploadConfirm, PagePreview,
    PaginatedSearchResults
)
from app.services.ocr_service import ocr_service
from app.services.embedding_service import embedding_service
from app.services.vector_db import vector_db
from app.services.imrad_service import imrad_service
from app.services.imrad_summary_service import imrad_summary_service
from app.services.imrad_structure_service import imrad_structure_service
from app.services.ml_service import expand_query, rerank_with_cross_encoder
from app.utils.citation_gen import CitationGenerator
from pypdf import PdfReader
from app.api.deps import admin_required, faculty_or_admin_required, get_current_user
from app.core.hash import encode_id, decode_id
from app.models.activity_log import ActivityLog
from app.services.imrad_structure_service import imrad_structure_service
from app.core.task_manager import task_manager

router = APIRouter()

UPLOAD_DIR = "uploads"
TEMP_UPLOAD_DIR = "uploads/temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

@router.get("/upload/status/{session_id}")
async def upload_status(session_id: str):
    """
    Step 1b: Stream real-time progress for a specific upload session.
    """
    return StreamingResponse(
        task_manager.subscribe(session_id),
        media_type="text/event-stream"
    )

@router.post("/preview", response_model=UploadPreviewResponse, dependencies=[Depends(faculty_or_admin_required)])
async def upload_preview(
    session_id: Optional[str] = None,
    file: UploadFile = File(...),
    auto_extract: bool = True,
    db: Session = Depends(get_db)
):
    """
    Step 1: Upload a PDF and get metadata + page thumbnails for review.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Guard rail: check for empty document
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="The document is empty (0 bytes).")
    
    try:
        from io import BytesIO
        reader = PdfReader(BytesIO(contents))
        if len(reader.pages) == 0:
            raise HTTPException(status_code=400, detail="The PDF has no pages.")
        
        # Check if at least one page has extractable text or is not completely empty
        # This is basic, but helps catch completely corrupted or blank PDFs.
        has_content = False
        for p in reader.pages[:min(5, len(reader.pages))]:
            if p.extract_text().strip():
                has_content = True
                break
        
        if not has_content:
            raise HTTPException(
                status_code=400, 
                detail="Empty Document: No readable text found in the first 5 pages. "
                       "If this is a scanned document, please ensure it has sufficient resolution."
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read PDF: {str(e)}")

    # Reset file pointer for subsequent processing
    await file.seek(0)

    if not session_id:
        session_id = str(uuid.uuid4())
    temp_path = os.path.join(TEMP_UPLOAD_DIR, f"{session_id}_{file.filename}")
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 1. Quick Duplicate Check (Instant Termination Phase)
    # Uses fast pypdf only to extract Title/Author/Year in milliseconds.
    if settings.STRICT_DUPLICATE_CHECK:
        task_manager.update_task(session_id, 2, "Checking for duplicates...")
        quick_meta = ocr_service.quick_metadata_sync(temp_path)
        q_title = quick_meta.get("title", "").strip()
        q_author = quick_meta.get("author", "").strip()
        q_year = quick_meta.get("year", "").strip()

        if q_title:
            existing = db.query(Paper).filter(
                Paper.title.ilike(q_title),
                Paper.deleted_at.is_(None)
            ).first()

            if existing:
                # Check for year/author overlap for a definitive match
                same_year = existing.year == q_year
                same_author = False
                if q_author != "Unknown" and existing.author:
                    a1 = set(q_author.lower().replace(",", " ").split())
                    a2 = set(existing.author.lower().replace(",", " ").split())
                    if len(a1.intersection(a2)) >= 1:
                        same_author = True

                if same_year and same_author:
                    from app.core.hash import encode_id
                    eid = encode_id(existing.id)
                    raise HTTPException(
                        status_code=400,
                        detail=f"Upload Terminated: This study is already indexed in the repository (ID: {eid})."
                    )

    if auto_extract:
        import asyncio
        metadata = await asyncio.to_thread(ocr_service.extract_metadata_sync, temp_path, session_id)
        
        # Guard rail: check for non-imrad format (must have at least 3 out of 5 core sections)
        sections = metadata.get("sections", {})
        core_keys = ["introduction", "methods", "results", "discussion", "references"]
        found_keys = [k for k in core_keys if k in sections and sections[k] and len(sections[k].strip()) > 50]
        
        if len(found_keys) < 3:
            # Cleanup temp file on failure
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            raise HTTPException(
                status_code=400,
                detail=f"Non-IMRAD Format Detected: Only {len(found_keys)}/5 core research sections were found. "
                       "Ensure the document has clear headings (e.g., Introduction, Methodology, Results, etc.)."
            )
    else:
        # Default metadata for manual review
        metadata = {
            "title": file.filename.replace(".pdf", ""),
            "author": "The system couldn't confidently detect any authors. Please click '+ Add Another Author' below to enter them manually.",
            "year": "N/A",
            "abstract": "The author of this study doesn't provide any abstract, or it perhaps it is still in manuscript phase or incomplete study.",
            "department": "N/A",
            "keywords": "",
            "degree_program": "N/A",
            "project_type": "Thesis",
            "citation_count": 0
        }

    # 3. Final Duplicate Check (Backup check for OCR-only successes)
    # If the quick check missed it but the slow extraction found a match.
    if settings.STRICT_DUPLICATE_CHECK and metadata.get("title"):
        title = metadata["title"].strip()
        author = metadata.get("author", "").strip()
        year = metadata.get("year", "").strip()
        
        # Exact title match (case-insensitive)
        existing = db.query(Paper).filter(
            Paper.title.ilike(title),
            Paper.deleted_at.is_(None)
        ).first()
        
        if existing:
            same_year = existing.year == year
            same_author = False
            if author and existing.author:
                a1 = set(author.lower().replace(",", " ").split())
                a2 = set(existing.author.lower().replace(",", " ").split())
                if len(a1.intersection(a2)) >= 1:
                    same_author = True
            
            if same_year and same_author:
                from app.core.hash import encode_id
                eid = encode_id(existing.id)
                raise HTTPException(
                    status_code=400, 
                    detail=f"Upload Terminated: This study is already indexed in the repository (ID: {eid})."
                )


    # 2. Determine document completeness and pick which pages to preview.
    #
    # A 'manuscript' is any uploaded PDF where IMRAD extraction found no
    # section headings — incomplete/in-progress or too non-standard to detect.
    #
    # Behaviour:
    #   Complete doc → imrad_pages carries the short per-section preview list
    #                  → only those thumbnails are rendered (fast, focused)
    #   Manuscript   → imrad_pages is empty → show first MAX_MANUSCRIPT_PREVIEW
    #                  pages so the admin still sees something useful
    #   Manual mode  → always show first MAX_MANUSCRIPT_PREVIEW pages
    MAX_MANUSCRIPT_PREVIEW = 10

    imrad_pages: list = metadata.pop("imrad_pages", [])
    is_manuscript: bool = auto_extract and len(imrad_pages) == 0

    # ── Prepare IMRAD raw text for preview ───────────────────────────────────
    # This runs synchronously before returning so the Step-2 review screen
    # already shows extracted raw text. Wrapped in try/except so a failure
    # never breaks the upload flow.
    if auto_extract and not is_manuscript:
        extracted_sections: dict = metadata.get("sections") or {}
        if extracted_sections and any(extracted_sections.values()):
            try:
                import asyncio
                preview_summaries = await asyncio.to_thread(
                    imrad_summary_service.summarise_all, extracted_sections
                )
                # Only store non-None results
                metadata["sections_summary"] = {
                    k: v for k, v in preview_summaries.items() if v
                }
                print(f"[Preview] Prepared raw text for sections: "
                      f"{list(metadata['sections_summary'].keys())}")
            except Exception as sum_err:
                print(f"[Preview] Summary pre-generation failed (non-fatal): {sum_err}")
                metadata.setdefault("sections_summary", {})

    if auto_extract and imrad_pages:
        # Normal path: smart IMRAD-filtered thumbnails
        import asyncio
        pages = await asyncio.to_thread(ocr_service.extract_page_previews_sync, temp_path, imrad_pages, session_id)
    else:
        # Manuscript or manual path: show only the first N pages, not the whole doc
        try:
            _num_pages = len(PdfReader(temp_path).pages)
        except Exception:
            _num_pages = MAX_MANUSCRIPT_PREVIEW
        preview_range = list(range(1, min(_num_pages, MAX_MANUSCRIPT_PREVIEW) + 1))
        import asyncio
        pages = await asyncio.to_thread(ocr_service.extract_page_previews_sync, temp_path, preview_range, session_id)

    # Attach manuscript flag so the frontend can show a specific notice
    metadata["is_manuscript"] = is_manuscript
    
    task_manager.update_task(session_id, 100, "Extraction complete", status="completed")

    return {
        "session_id": session_id,
        "metadata": metadata,
        "pages": pages,
        "sections": metadata.get("sections", {}),
        "sections_summary": metadata.get("sections_summary", {}),
        "section_pages": metadata.get("section_pages", {}),
        "media": metadata.get("media", {}),
    }

@router.post("/confirm-upload", response_model=PaperResponse, dependencies=[Depends(faculty_or_admin_required)])
async def confirm_upload(data: UploadConfirm, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    Step 2: Finalize upload with corrected metadata and selected pages.
    """
    print(f"[confirm_upload] current_user = {current_user}")
    print(f"[confirm_upload] username = {getattr(current_user, 'username', None)}")
    print(f"[confirm_upload] full_name = {getattr(current_user, 'full_name', None)}")
    
    # Find the temp file
    temp_files = [f for f in os.listdir(TEMP_UPLOAD_DIR) if f.startswith(data.session_id)]
    if not temp_files:
        raise HTTPException(status_code=404, detail="Session expired or file not found")
    
    temp_path = os.path.join(TEMP_UPLOAD_DIR, temp_files[0])
    original_filename = temp_files[0].replace(f"{data.session_id}_", "")
    final_path = os.path.join(UPLOAD_DIR, f"{data.session_id}_{original_filename}")

    # Move to permanent storage
    shutil.move(temp_path, final_path)

    # Extract text FROM SELECTED PAGES ONLY
    selected_content = ""
    try:
        reader = PdfReader(final_path)
        for page_idx in data.selected_pages:
            if 1 <= page_idx <= len(reader.pages):
                page_text = reader.pages[page_idx - 1].extract_text()
                if page_text:
                    selected_content += page_text + "\n\n"
    except Exception as e:
        print(f"Error extracting selected content: {e}")

    # Create paper record
    db_paper = Paper(
        title=data.metadata.get("title", "Untitled"),
        author=data.metadata.get("author", "Unknown"),
        year=data.metadata.get("year", "N/A"),
        abstract=data.metadata.get("abstract", ""),
        department=data.metadata.get("department", "N/A"),
        keywords=data.metadata.get("keywords", ""),
        project_type=data.metadata.get("project_type", "N/A"),
        degree_program=data.metadata.get("degree_program", "N/A"),
        citation_count=data.metadata.get("citation_count", 0),
        file_path=final_path,
        uploaded_by=current_user.full_name or current_user.username,
        uploader_role=current_user.role,

        # Save IMRAD sections (manual overrides or defaults)
        introduction=data.introduction,
        methods=data.methods,
        results=data.results,
        discussion=data.discussion,
        references=data.references,

        # Save pre-generated raw text from preview (if available)
        introduction_summary=data.sections_summary.get("introduction") if data.sections_summary else None,
        methods_summary=data.sections_summary.get("methods") if data.sections_summary else None,
        results_summary=data.sections_summary.get("results") if data.sections_summary else None,
        discussion_summary=data.sections_summary.get("discussion") if data.sections_summary else None,

        # Save visual snippets (base64 images)
        media=data.media
    )
    db.add(db_paper)
    db.commit()
    db.refresh(db_paper)
    
    if db_paper.media:
        print(f"[confirm_upload] Saved {len(db_paper.media)} visual table snippets.")

    db.add(ActivityLog(
        action="Upload",
        paper_title=db_paper.title,
        performed_by=current_user.full_name or current_user.username,
        performed_by_role=current_user.role,
    ))
    db.commit()

    # Use provided IMRAD sections or fallback to extraction if not provided
    imrad_sections = {
        "introduction": data.introduction,
        "methods": data.methods,
        "results": data.results,
        "discussion": data.discussion
    }
    # Filter out None values and fill gaps with re-extraction from selected pages
    if not all(imrad_sections.values()):
        # Build a page-keyed dict from the selected pages so extract_sections
        # receives the format it now expects (Dict[int, str])
        try:
            reader_for_fill = PdfReader(final_path)
            selected_page_map: dict = {}
            for pg_num in data.selected_pages:
                if 1 <= pg_num <= len(reader_for_fill.pages):
                    txt = reader_for_fill.pages[pg_num - 1].extract_text()
                    if txt:
                        selected_page_map[pg_num] = txt
        except Exception as e:
            print(f"Re-extraction page read error: {e}")
            selected_page_map = {}

        if selected_page_map:
            extracted_result = imrad_service.extract_sections(selected_page_map)
            extracted = extracted_result.get("sections", {})
            for key, val in extracted.items():
                if not imrad_sections.get(key):
                    imrad_sections[key] = val
                    setattr(db_paper, key, val)
            
            # Handle references fallback
            if not db_paper.references:
                db_paper.references = extracted_result.get("references")
            
            db.commit()

    # ── IMRAD Raw Text ────────────────────────────────────────────────────
    # Raw texts were prepared during preview and saved to db_paper above.
    # Only re-run if they're still missing (e.g. manuscript path
    # where auto_extract=False was used and no preview texts exist).
    summaries_already_saved = any([
        db_paper.introduction_summary,
        db_paper.methods_summary,
        db_paper.results_summary,
        db_paper.discussion_summary,
    ])
    if not summaries_already_saved:
        try:
            summaries = imrad_summary_service.summarise_all(imrad_sections)
            db_paper.introduction_summary = summaries.get("introduction")
            db_paper.methods_summary      = summaries.get("methods")
            db_paper.results_summary      = summaries.get("results")
            db_paper.discussion_summary   = summaries.get("discussion")
            db.commit()
            print(f"[IMRADRawText] Fallback raw text saved for paper {db_paper.id}: "
                  f"{[k for k, v in summaries.items() if v]}")
        except Exception as summary_err:
            print(f"[IMRADSummary] Non-fatal error: {summary_err}")
    else:
        print(f"[IMRADRawText] Using pre-generated raw text from preview for paper {db_paper.id}")

    # Build the full vector dict: title + abstract (if enabled) + any detected IMRAD sections
    content_for_abstract = selected_content.strip() if selected_content.strip() else db_paper.abstract
    all_vectors = imrad_service.build_vectors(
        title=db_paper.title,
        sections=imrad_sections,
        abstract=content_for_abstract
    )

    vector_db.upsert_paper(
        paper_id=db_paper.id,
        vectors=all_vectors,
        metadata={
            "title": db_paper.title,
            "author": db_paper.author,
            "year": db_paper.year,
            "abstract": db_paper.abstract,
            "department": db_paper.department,
            "keywords": db_paper.keywords,
            "project_type": db_paper.project_type,
            "degree_program": db_paper.degree_program,
            "citation_count": db_paper.citation_count,
            "view_count": db_paper.view_count,
            "uploaded_by": db_paper.uploaded_by,
            "uploader_role": db_paper.uploader_role,
            "created_at": db_paper.created_at.isoformat() if db_paper.created_at else None
        }
    )

    # Build structured IMRAD blocks for the immediate response
    db_paper.__dict__["imrad_structured"] = imrad_structure_service.build(db_paper)
    return db_paper

@router.get("/trash", response_model=List[PaperResponse], dependencies=[Depends(faculty_or_admin_required)])
async def list_trash(db: Session = Depends(get_db)):
    """
    Returns all soft-deleted papers (deleted_at IS NOT NULL), newest deletion first.
    Visible to Admin and Faculty only.
    Enforces expiration check on-demand.
    """
    from app.services.cleanup_service import perform_purge
    perform_purge(db)

    return (
        db.query(Paper)
        .filter(Paper.deleted_at.isnot(None))
        .order_by(Paper.deleted_at.desc())
        .all()
    )


@router.get("/", response_model=List[PaperResponse])
async def list_papers(db: Session = Depends(get_db)):
    """Returns only active (non-trashed) papers."""
    return db.query(Paper).filter(Paper.deleted_at.is_(None)).all()

# ── Sample Documents (System Evaluation Feature) ─────────────────────────────
# These endpoints are only active when ENABLE_SAMPLE_DOCS=true in .env.
# To disable the feature after evaluation, set ENABLE_SAMPLE_DOCS=false and
# restart the backend — no code changes required.

# Safe mapping: slug → filename (prevents path traversal)
_SAMPLE_DOCS: list[dict] = [
    {"id": "sample-1",          "filename": "BORROWED_THESIS_DOCUMENT_OK1.pdf",   "name": "THESIS_DOCUMENT_OK1"},
    {"id": "sample-2",          "filename": "BORROWED_THESIS_DOCUMENT_OK2.pdf",   "name": "THESIS_DOCUMENT_OK2"},
    {"id": "sample-3",          "filename": "BORROWED_THESIS_DOCUMENT_OK3.pdf",   "name": "THESIS_DOCUMENT_OK3"},
    {"id": "sample-4",          "filename": "BORROWED_CAPSTONE_DOCUMENT_OK1.pdf", "name": "CAPSTONE_DOCUMENT_OK1"},
    {"id": "sample-fail-empty", "filename": "EMPTY_DOCUMENT_FAIL.pdf",            "name": "[FAIL] Empty Document Case"},
    {"id": "sample-fail-imrad", "filename": "NON_IMRAD_DOCUMENT_FAIL.pdf",        "name": "[FAIL] Non-IMRAD Format Case"},
]

@router.get("/sample-documents", dependencies=[Depends(faculty_or_admin_required)])
async def list_sample_documents():
    """
    Returns the list of pre-stored sample documents available for drag-and-drop
    upload testing. Only active when ENABLE_SAMPLE_DOCS=true.

    Returns name, id (slug), and size only — no file bytes are included.
    """
    if not settings.ENABLE_SAMPLE_DOCS:
        return []  # Feature disabled — UI panel will hide itself

    docs_dir = settings.SAMPLE_DOCS_DIR
    result = []
    for doc in _SAMPLE_DOCS:
        path = os.path.join(docs_dir, doc["filename"])
        if os.path.isfile(path):
            result.append({
                "id":         doc["id"],
                "name":       doc["name"],
                "size_bytes": os.path.getsize(path),
            })
    return result


@router.get("/sample-documents/{doc_id}/fetch", dependencies=[Depends(faculty_or_admin_required)])
async def fetch_sample_document(doc_id: str):
    """
    Streams a pre-stored sample document as raw bytes (application/octet-stream).
    Used exclusively by the frontend drag-and-drop handler to create an in-memory
    File object — the bytes are never persisted to the browser.

    Privacy guarantees:
    - No Content-Disposition: attachment header (no download prompt)
    - Only accessible to authenticated faculty/admin
    - Only active when ENABLE_SAMPLE_DOCS=true
    """
    if not settings.ENABLE_SAMPLE_DOCS:
        raise HTTPException(status_code=404, detail="Sample documents are not available.")

    # Resolve slug → filename via the safe static map (no path traversal possible)
    doc_meta = next((d for d in _SAMPLE_DOCS if d["id"] == doc_id), None)
    if not doc_meta:
        raise HTTPException(status_code=404, detail="Sample document not found.")

    file_path = os.path.join(settings.SAMPLE_DOCS_DIR, doc_meta["filename"])
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Sample document file is missing on the server.")

    def iter_file():
        with open(file_path, "rb") as f:
            while chunk := f.read(64 * 1024):  # 64 KB chunks
                yield chunk

    return StreamingResponse(
        iter_file(),
        media_type="application/octet-stream",
        # Intentionally NO Content-Disposition header — prevents download dialog
        headers={"X-Filename": doc_meta["filename"]},
    )

# ─────────────────────────────────────────────────────────────────────────────

@router.get("/search/config")
async def get_search_config():
    """Return the default search configuration (threshold, etc.) to the frontend."""
    return {
        "default_threshold": settings.DEFAULT_SEARCH_THRESHOLD
    }

@router.get("/search", response_model=PaginatedSearchResults)
async def search_papers(
    db: Session = Depends(get_db),
    query: Optional[str] = None, 
    threshold: Optional[float] = None, 
    author: Optional[str] = None,
    year: Optional[str] = None,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    department: Optional[str] = None,
    project_type: Optional[str] = None,
    degree_program: Optional[str] = None,
    section: Optional[str] = None,
    sort: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
):
    """
    Unified search: handles both metadata filtering (Browse) and BERT-NLP semantic search.
    - Uses SQL first to filter papers by metadata (author, year range, etc.).
    - If query is provided, uses Qdrant to find semantic matches within the filtered IDs.
    - If no query is provided, returns the filtered papers directly (Browse Mode).
    """
    try:
        print(f"--- [Search] Unified search started ---")
        print(f"    Query: '{query}'")
        print(f"    Filters: min_yr={min_year}, max_yr={max_year}, dept={department}, type={project_type}")
        
        # 1. SQL Metadata-Only Filter (active papers only — exclude soft-deleted)
        sql_query = db.query(Paper).filter(Paper.deleted_at.is_(None))
        
        if author: sql_query = sql_query.filter(Paper.author.ilike(f"%{author}%"))
        if year: sql_query = sql_query.filter(Paper.year == year)
        
        # Numeric Year Range Filter (CAST string column to Integer for the range check)
        if min_year is not None:
            sql_query = sql_query.filter(Paper.year.cast(Integer) >= min_year)
        if max_year is not None:
            sql_query = sql_query.filter(Paper.year.cast(Integer) <= max_year)
            
        if department: sql_query = sql_query.filter(Paper.department == department)
        if project_type: sql_query = sql_query.filter(Paper.project_type == project_type)
        if degree_program: sql_query = sql_query.filter(Paper.degree_program == degree_program)
        
        # Get Candidate Paper IDs
        candidate_papers = sql_query.all()
        candidate_ids = [p.id for p in candidate_papers]
        
        print(f"[Search] SQL Pre-filter found {len(candidate_ids)} candidates: {candidate_ids[:10]}...")

        # 2. Handle Search Mode (Semantic vs Browse)
        if query and query.strip():
            # ── SEMANTIC SEARCH (Original Core Logic) ──
            if not candidate_ids:
                return []  # Metadata filters already narrowed to zero

            print(f"Generating query embedding for BERT search: '{query}'...")
            query_vector = embedding_service.get_embedding(query)

            # Constrain search to paper IDs matching metadata filters
            qdrant_filter = models.Filter(
                must=[models.HasIdCondition(has_id=candidate_ids)]
            )

            print(f"Searching across IMRAD vectors in Qdrant (constrained to {len(candidate_ids)} papers)...")
            semantic_results = vector_db.search_max(query_vector, filter_obj=qdrant_filter, section=section, limit=100)

            effective_threshold = threshold if threshold is not None else settings.DEFAULT_SEARCH_THRESHOLD

            # Build a paper-id lookup for metadata comparison
            candidate_map = {p.id: p for p in candidate_papers}
            query_words = set(query.lower().split())

            # ── LINEAR HYBRID FUSION (Semantic + Keyword) ──
            search_results = []
            for hit in semantic_results:
                vector_score = hit.score
                paper = candidate_map.get(hit.id)
                
                # Calculate Keyword Match Score (0 to 1)
                keyword_score = 0.0
                if paper and query_words:
                    title_words = set((paper.title or "").lower().split())
                    abs_words   = set((paper.abstract or "").lower().split())
                    kw_words    = set((paper.keywords or "").lower().replace(",", " ").split())
                    
                    # Priority 1: Title (80% of keyword weight)
                    title_overlap = len(query_words & title_words) / len(query_words)
                    # Priority 2: Abstract/Keywords (20% of keyword weight)
                    content_overlap = len(query_words & (abs_words | kw_words)) / len(query_words)
                    
                    keyword_score = (title_overlap * 0.8) + (content_overlap * 0.2)
                
                # COMBINE: 60% Semantic meaning + 40% Literal keyword matching
                # This ensures "Mobile" in title always ranks higher than "Desktop" for a "Mobile" search.
                final_score = (vector_score * 0.6) + (keyword_score * 0.4)
                
                if final_score >= effective_threshold:
                    search_results.append(SearchResult(
                        id=encode_id(hit.id),
                        score=final_score,
                        payload=hit.payload
                    ))

            # Final sort
            if sort == "newest":
                search_results.sort(key=lambda x: x.payload.get("year", ""), reverse=True)
            elif sort == "oldest":
                search_results.sort(key=lambda x: x.payload.get("year", ""), reverse=False)
            elif sort == "cited":
                search_results.sort(key=lambda x: x.payload.get("citation_count", 0), reverse=True)
            else:
                # Default for keyword search: Relevancy Score
                search_results.sort(key=lambda x: x.score, reverse=True)

            print(f"Search completed. Found {len(search_results)} relevant results using linear hybrid fusion.")
            
            total = len(search_results)
            start = (page - 1) * page_size
            end = start + page_size
            
            return PaginatedSearchResults(
                results=search_results[start:end],
                total=total,
                page=page,
                page_size=page_size
            )


        else:
            # -- BROWSE MODE (Metadata Filtering Only) --
            # Return current candidate list as high-score matches
            print(f"[Search] Returning {len(candidate_papers)} results for browse mode.")
            browse_results = []
            for paper in candidate_papers:
                browse_results.append(SearchResult(
                    id=encode_id(paper.id),
                    score=1.0,  # Browsing result -- treat as perfect metadata match
                    payload={
                        "title":          paper.title,
                        "author":         paper.author,
                        "year":           paper.year,
                        "abstract":       paper.abstract,
                        "department":     paper.department,
                        "project_type":   paper.project_type,
                        "degree_program": paper.degree_program,
                        "citation_count": paper.citation_count,
                        "view_count":     paper.view_count,
                        "uploaded_by":    paper.uploaded_by,
                        "uploader_role":  paper.uploader_role,
                        "created_at":     paper.created_at.isoformat() if paper.created_at else None
                    }
                ))
            # Final sort for Browse
            if sort == "newest":
                browse_results.sort(key=lambda x: x.payload.get("year", ""), reverse=True)
            elif sort == "oldest":
                browse_results.sort(key=lambda x: x.payload.get("year", ""), reverse=False)
            elif sort == "cited":
                browse_results.sort(key=lambda x: x.payload.get("citation_count", 0), reverse=True)
            else:
                # Default for Browse: Newest Year first
                browse_results.sort(key=lambda x: x.payload.get("year", ""), reverse=True)
            
            total = len(browse_results)
            start = (page - 1) * page_size
            end = start + page_size
            
            return PaginatedSearchResults(
                results=browse_results[start:end],
                total=total,
                page=page,
                page_size=page_size
            )

    except Exception as e:
        import traceback
        print(f"SEARCH ERROR: {type(e).__name__} - {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/{paper_id}/recommendations", response_model=List[SearchResult])
async def get_paper_recommendations(
    paper_id: str, 
    limit: int = 5,
    author: Optional[str] = None,
    year: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db)
):
    real_id = decode_id(paper_id)
    if real_id is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    try:
        print(f"--- Recommendations requested for Paper ID: {real_id} ---")
        
        # Construct Metadata Filter for Qdrant (Narrow Down)
        qdrant_filter = models.Filter(
            must_not=[models.HasIdCondition(has_id=[real_id])]
        )
        
        filter_conditions = []
        if author:
            filter_conditions.append(models.FieldCondition(key="author", match=models.MatchValue(value=author)))
        if year:
            filter_conditions.append(models.FieldCondition(key="year", match=models.MatchValue(value=year)))
        if department:
            filter_conditions.append(models.FieldCondition(key="department", match=models.MatchValue(value=department)))
        
        if filter_conditions:
            qdrant_filter.must = filter_conditions

        # ── Step A: Get Context for Keyword Boosting ──
        # We use the source paper's title/keywords as a secondary signal
        source_paper = db.query(Paper).filter(Paper.id == real_id).first()
        source_words = set()
        if source_paper:
            source_words = set((source_paper.title or "").lower().split())

        # ── Step B: Fetch Vector Recommendations ──
        # results are already capped at 1.0 raw cosine by vector_db.py overhaul
        results = vector_db.recommend(real_id, limit=limit, filter_obj=qdrant_filter)
        
        # ── Step C: Linear Hybrid Fusion ──
        search_results = []
        for hit in results:
            vector_score = hit.score  # 0.0 to 1.0 from vector_db
            
            # Calculate Keyword Match Score (0 to 1) based on source paper metadata
            keyword_score = 0.0
            if source_words:
                cand_title_words = set(hit.payload.get("title", "").lower().split())
                cand_abs_words = set(hit.payload.get("abstract", "").lower().split())
                
                # Priority 1: Title match (80% of keyword weight)
                title_overlap = len(source_words & cand_title_words) / len(source_words)
                # Priority 2: Abstract match (20% of keyword weight)
                content_overlap = len(source_words & cand_abs_words) / len(source_words)
                
                keyword_score = (title_overlap * 0.8) + (content_overlap * 0.2)

            # COMBINE: 60% Semantic meaning + 40% Literal keyword matching
            final_score = (vector_score * 0.6) + (keyword_score * 0.4)

            # EXPLICIT FILTER: Do not recommend the same paper (by ID or Title)
            if int(hit.id) == int(real_id) or hit.payload.get("title") == source_paper.title:
                continue

            search_results.append(SearchResult(
                id=encode_id(hit.id),
                score=final_score,
                payload=hit.payload
            ))
            
        print(f"[Recommendations] Returning {len(search_results)} hybrid-scored recommendations.")
        return search_results
    except Exception as e:
        import traceback
        print(f"RECOMMENDATION ERROR: {type(e).__name__} - {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))



@router.delete("/{paper_id}", dependencies=[Depends(faculty_or_admin_required)])
async def delete_paper(paper_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    Soft-delete: moves the paper to Trash (sets deleted_at timestamp).
    Qdrant vectors are intentionally kept so restore is instant (no re-indexing).
    The cleanup_service will hard-purge after TRASH_RETENTION_DAYS (15) days.
    """
    real_id = decode_id(paper_id)
    if real_id is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    db_paper = db.query(Paper).filter(Paper.id == real_id, Paper.deleted_at.is_(None)).first()
    if not db_paper:
        raise HTTPException(status_code=404, detail="Paper not found or already in Trash")

    performer = current_user.full_name or current_user.username

    # Soft-delete: stamp deleted_at and record who did it (using local time for PC parity)
    db_paper.deleted_at = datetime.now()
    db_paper.deleted_by = performer

    # Log the action
    db.add(ActivityLog(
        action="Delete",
        paper_title=db_paper.title,
        performed_by=performer,
        performed_by_role=current_user.role,
    ))
    db.commit()

    return {"message": f"Paper '{db_paper.title}' moved to Trash. It will be permanently deleted in 15 days."}


@router.post("/{paper_id}/restore", dependencies=[Depends(faculty_or_admin_required)])
async def restore_paper(paper_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    Restore a soft-deleted paper: clears deleted_at so it reappears in normal lists.
    Qdrant vectors were never removed, so no re-indexing is needed.
    """
    real_id = decode_id(paper_id)
    if real_id is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    db_paper = db.query(Paper).filter(Paper.id == real_id, Paper.deleted_at.isnot(None)).first()
    if not db_paper:
        raise HTTPException(status_code=404, detail="Paper not found in Trash")

    performer = current_user.full_name or current_user.username
    db_paper.deleted_at = None
    db_paper.deleted_by = None

    db.add(ActivityLog(
        action="Restore",
        paper_title=db_paper.title,
        performed_by=performer,
        performed_by_role=current_user.role,
    ))
    db.commit()

    return {"message": f"Paper '{db_paper.title}' restored successfully."}


@router.delete("/{paper_id}/purge", dependencies=[Depends(admin_required)])
async def purge_paper(paper_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    Admin-only: force-purge a trashed paper before the 15-day window expires.
    Performs the full hard-delete: Qdrant + disk + DB.
    """
    real_id = decode_id(paper_id)
    if real_id is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    db_paper = db.query(Paper).filter(Paper.id == real_id, Paper.deleted_at.isnot(None)).first()
    if not db_paper:
        raise HTTPException(status_code=404, detail="Paper not found in Trash (may already be purged or still active)")

    title = db_paper.title
    performer = current_user.full_name or current_user.username

    # 1. Remove Qdrant vectors
    try:
        vector_db.delete_paper(real_id)
    except Exception as e:
        print(f"[Purge] Qdrant delete error for paper {real_id}: {e}")

    # 2. Remove physical PDF file
    if db_paper.file_path and os.path.exists(db_paper.file_path):
        try:
            os.remove(db_paper.file_path)
        except Exception as e:
            print(f"[Purge] File delete error for paper {real_id}: {e}")

    # 3. Log + delete DB record
    db.add(ActivityLog(
        action="Purge",
        paper_title=title,
        performed_by=performer,
        performed_by_role=current_user.role,
    ))
    db.delete(db_paper)
    db.commit()

    return {"message": f"Paper '{title}' permanently purged."}

@router.put("/{paper_id}", response_model=PaperResponse, dependencies=[Depends(faculty_or_admin_required)])
async def update_paper(paper_id: str, updates: PaperUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    real_id = decode_id(paper_id)
    if real_id is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    db_paper = db.query(Paper).filter(Paper.id == real_id).first()
    if not db_paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # Update SQLite database fields
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_paper, key, value)
    
    db.commit()
    db.refresh(db_paper)

    # Use persistent sections for vectorizing
    imrad_sections = {
        "introduction": db_paper.introduction,
        "methods": db_paper.methods,
        "results": db_paper.results,
        "discussion": db_paper.discussion,
        "references": db_paper.references
    }
    
    all_vectors = imrad_service.build_vectors(
        title=db_paper.title,
        sections=imrad_sections,
        abstract=db_paper.abstract
    )
    
    vector_db.upsert_paper(
        paper_id=db_paper.id,
        vectors=all_vectors,
        metadata={
            "title": db_paper.title,
            "author": db_paper.author,
            "year": db_paper.year,
            "abstract": db_paper.abstract,
            "department": db_paper.department,
            "keywords": db_paper.keywords,
            "project_type": db_paper.project_type,
            "degree_program": db_paper.degree_program,
            "citation_count": db_paper.citation_count,
            "view_count": db_paper.view_count,
            "uploaded_by": db_paper.uploaded_by,
            "uploader_role": db_paper.uploader_role
        }
    )

    db.add(ActivityLog(
        action="Edit",
        paper_title=db_paper.title,
        performed_by=current_user.full_name or current_user.username,
        performed_by_role=current_user.role,
    ))
    db.commit()

    return db_paper
@router.get("/{paper_id}/formatted-citations")
async def get_formatted_citations(
    paper_id: str,
    db: Session = Depends(get_db),
):
    """
    Returns a dictionary of structured citation strings (APA 6th, APA 7th,
    APA in-text, IEEE, MLA, BibTeX) for the given paper.

    How scholarly citation works:
    - In-text citation: A short marker placed in the body of the citing paper
      (e.g. APA: (Smith, 2023) or IEEE: [1]) that points the reader to the
      full reference entry at the end of the document.
    - Reference list entry: The full bibliographic record (author, title,
      institution, year, etc.) that appears in the References / Works Cited
      section of the citing paper.
    This endpoint returns both the in-text form (apa_intext) and the full
    reference-list strings (apa_6, apa_7, ieee, mla, bibtex) so the frontend
    can display either depending on what the reader needs to copy.
    """
    real_id = decode_id(paper_id)
    if real_id is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    paper = db.query(Paper).filter(Paper.id == real_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    return CitationGenerator.generate_all(
        title=paper.title,
        author_str=paper.author,
        year=paper.year,
        project_type=paper.project_type or "Thesis"
    )


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(paper_id: str, db: Session = Depends(get_db)):
    """Fetch a single paper by its ID."""
    real_id = decode_id(paper_id)
    if real_id is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    paper = db.query(Paper).filter(Paper.id == real_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # Build structured IMRAD blocks at response time — no DB writes needed.
    # The frontend receives pre-parsed typed blocks instead of flat strings,
    # eliminating the need for client-side regex parsing.
    paper.__dict__["imrad_structured"] = imrad_structure_service.build(paper)

    return paper


@router.post("/{paper_id}/view", response_model=ViewCountResponse)
async def record_view(paper_id: str, db: Session = Depends(get_db)):
    """Increment view count. Public endpoint — any visit counts."""
    real_id = decode_id(paper_id)
    if real_id is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    paper = db.query(Paper).filter(Paper.id == real_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    paper.view_count = (paper.view_count or 0) + 1
    db.commit()
    db.refresh(paper)
    return {"view_count": paper.view_count}


@router.get("/{paper_id}/section-pages/{section}", dependencies=[])
async def get_section_pages(
    paper_id: str,
    section: str,
    db: Session = Depends(get_db),
):
    """
    On-demand: return base64 thumbnails for the pages belonging to a specific
    IMRAD section of a paper.  Used by detail_win.vue when the user clicks
    "View Pages" on an IMRAD tab.

    Flow:
      1. Load paper record → get file_path
      2. Build page_text_map from the full PDF
      3. Re-run extract_sections() to get section_pages mapping
      4. Render only those pages as JPEG thumbnails via extract_page_previews()
    """
    VALID_SECTIONS = {"introduction", "methods", "results", "discussion"}
    if section not in VALID_SECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid section '{section}'")

    real_id = decode_id(paper_id)
    if real_id is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    paper = db.query(Paper).filter(Paper.id == real_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if not paper.file_path or not os.path.exists(paper.file_path):
        raise HTTPException(status_code=404, detail="PDF file not found on server")

    try:
        reader = PdfReader(paper.file_path)
        num_pages = len(reader.pages)

        # Build full page map for IMRAD detection
        page_text_map: dict = {}
        for i in range(num_pages):
            t = reader.pages[i].extract_text()
            if t:
                page_text_map[i + 1] = t

        # Re-detect section boundaries
        extracted = imrad_service.extract_sections(page_text_map)
        full_section_pages: dict = extracted.get("full_section_pages", {})
        section_pages_map: dict = full_section_pages or extracted.get("section_pages", {})

        pages_for_section = section_pages_map.get(section, [])
        if not pages_for_section:
            return {"pages": [], "message": f"No pages detected for section '{section}'"}

        import asyncio
        thumbnails = await asyncio.to_thread(
            ocr_service.extract_page_previews_sync,
            paper.file_path,
            pages_for_section,
        )
        return {"pages": thumbnails, "section": section}

    except Exception as e:
        print(f"[section-pages] Error for paper {paper_id}/{section}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to render section pages: {str(e)}")


@router.get("/{paper_id}/cite-status", response_model=CitationStatus)
async def get_cite_status(
    paper_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Check whether the authenticated user has already cited this paper."""
    real_id = decode_id(paper_id)
    if real_id is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    paper = db.query(Paper).filter(Paper.id == real_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    has_cited = db.query(UserCitation).filter(
        UserCitation.user_id == current_user.id,
        UserCitation.paper_id == real_id
    ).first() is not None
    return {"has_cited": has_cited, "citation_count": paper.citation_count}


@router.post("/{paper_id}/cite", response_model=CitationStatus)
async def cite_paper(
    paper_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Allow a registered user to cite/vouch for a paper (once per user)."""
    real_id = decode_id(paper_id)
    if real_id is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    paper = db.query(Paper).filter(Paper.id == real_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    already_cited = db.query(UserCitation).filter(
        UserCitation.user_id == current_user.id,
        UserCitation.paper_id == real_id
    ).first()

    if already_cited:
        raise HTTPException(status_code=409, detail="You have already cited this paper")

    citation = UserCitation(user_id=current_user.id, paper_id=real_id)
    db.add(citation)
    paper.citation_count = (paper.citation_count or 0) + 1
    db.commit()
    db.refresh(paper)
    return {"has_cited": True, "citation_count": paper.citation_count}


