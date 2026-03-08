from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy import Integer
from sqlalchemy.orm import Session
from typing import List, Optional
import shutil
import os
import uuid
from qdrant_client.http import models

from app.core.database import get_db
from app.models.paper import Paper
from app.models.citation import UserCitation
from app.schemas.paper import (
    PaperResponse, SearchResult, PaperUpdate, CitationStatus, 
    ViewCountResponse, UploadPreviewResponse, UploadConfirm, PagePreview
)
from app.services.ocr_service import ocr_service
from app.services.embedding_service import embedding_service
from app.services.vector_db import vector_db
from app.services.imrad_service import imrad_service
from pypdf import PdfReader
from app.api.deps import admin_required, faculty_or_admin_required, get_current_user

router = APIRouter()

UPLOAD_DIR = "uploads"
TEMP_UPLOAD_DIR = "uploads/temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

@router.post("/preview", response_model=UploadPreviewResponse, dependencies=[Depends(faculty_or_admin_required)])
async def upload_preview(
    file: UploadFile = File(...),
    auto_extract: bool = True
):
    """
    Step 1: Upload a PDF and get metadata + page thumbnails for review.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    session_id = str(uuid.uuid4())
    temp_path = os.path.join(TEMP_UPLOAD_DIR, f"{session_id}_{file.filename}")
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 1. Extract Metadata (Only if requested)
    if auto_extract:
        metadata = await ocr_service.extract_metadata(temp_path)
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

    if auto_extract and imrad_pages:
        # Normal path: smart IMRAD-filtered thumbnails
        pages = await ocr_service.extract_page_previews(temp_path, imrad_pages=imrad_pages)
    else:
        # Manuscript or manual path: show only the first N pages, not the whole doc
        try:
            _num_pages = len(PdfReader(temp_path).pages)
        except Exception:
            _num_pages = MAX_MANUSCRIPT_PREVIEW
        preview_range = list(range(1, min(_num_pages, MAX_MANUSCRIPT_PREVIEW) + 1))
        pages = await ocr_service.extract_page_previews(temp_path, imrad_pages=preview_range)

    # Attach manuscript flag so the frontend can show a specific notice
    metadata["is_manuscript"] = is_manuscript

    return {
        "session_id": session_id,
        "metadata": metadata,
        "pages": pages,
        "sections": metadata.get("sections", {}),
        "section_pages": metadata.get("section_pages", {})
    }

@router.post("/confirm-upload", response_model=PaperResponse, dependencies=[Depends(faculty_or_admin_required)])
async def confirm_upload(data: UploadConfirm, db: Session = Depends(get_db)):
    """
    Step 2: Finalize upload with corrected metadata and selected pages.
    """
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
        
        # Save IMRAD sections (manual overrides or defaults)
        introduction=data.introduction,
        methods=data.methods,
        results=data.results,
        discussion=data.discussion
    )
    db.add(db_paper)
    db.commit()
    db.refresh(db_paper)

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
            db.commit()

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
            "citation_count": db_paper.citation_count
        }
    )

    return db_paper

@router.get("/", response_model=List[PaperResponse])
async def list_papers(db: Session = Depends(get_db)):
    return db.query(Paper).all()

@router.get("/search", response_model=List[SearchResult])
async def search_papers(
    query: str, 
    threshold: float = 0.2, 
    author: Optional[str] = None,
    year: Optional[str] = None,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    department: Optional[str] = None,
    project_type: Optional[str] = None,
    degree_program: Optional[str] = None,
    section: Optional[str] = None,  # IMRAD section targeting: 'introduction','methods','results','discussion'
    db: Session = Depends(get_db)
):
    try:
        print(f"--- Search started for query: '{query}' (Threshold: {threshold}) ---")
        
        # 1. Construct Metadata Filter for Qdrant
        qdrant_filter = None
        filter_conditions = []
        if author:
            filter_conditions.append(models.FieldCondition(key="author", match=models.MatchValue(value=author)))
        if year:
            filter_conditions.append(models.FieldCondition(key="year", match=models.MatchValue(value=year)))
        if min_year:
            # Qdrant supports range filtering on numeric fields, but year is currently a string in our metadata.
            # For simplicity in this prototype, we'll convert to int if possible in Qdrant or use SQL filtering primarily.
            # Let's assume the user mostly cares about the SQL side for year ranges in this prototype.
            pass
        if department:
            filter_conditions.append(models.FieldCondition(key="department", match=models.MatchValue(value=department)))
        if project_type:
            filter_conditions.append(models.FieldCondition(key="project_type", match=models.MatchValue(value=project_type)))
        if degree_program:
            filter_conditions.append(models.FieldCondition(key="degree_program", match=models.MatchValue(value=degree_program)))
        
        if filter_conditions:
            qdrant_filter = models.Filter(must=filter_conditions)

        # 2. Keyword search (Exact Match in SQLite)
        # 2. Perform keyword search in DB (Metadata match)
        print("Performing metadata keyword search...")
        sql_query = db.query(Paper).filter(
            (Paper.title.ilike(f"%{query}%")) | 
            (Paper.abstract.ilike(f"%{query}%"))
        )
        
        # Apply filters
        if author: sql_query = sql_query.filter(Paper.author.ilike(f"%{author}%"))
        if year: sql_query = sql_query.filter(Paper.year == year)
        if min_year: sql_query = sql_query.filter(Paper.year.cast(Integer) >= min_year)
        if max_year: sql_query = sql_query.filter(Paper.year.cast(Integer) <= max_year)
        if department: sql_query = sql_query.filter(Paper.department == department)
        if project_type: sql_query = sql_query.filter(Paper.project_type == project_type)
        if degree_program: sql_query = sql_query.filter(Paper.degree_program == degree_program)
        
        keyword_matches = {p.id: p for p in sql_query.all()}
        
        # 3. Generate query embedding for semantic search
        print("Generating query embedding for semantic search...")
        query_vector = embedding_service.get_embedding(query)
        
        # 4. Search in Qdrant (IMRAD multi-vector max-score, with optional section targeting)
        print(f"Searching across IMRAD vectors in Qdrant (section={section})...")
        semantic_results = vector_db.search_max(query_vector, filter_obj=qdrant_filter, section=section)
        
        combined_results = {}
        
        # Process Semantic Results first (detailed scores)
        for hit in semantic_results:
            paper_id = hit.id
            bert_score = hit.score
            
            # Weighted Blend: 85% Semantic, 15% Metadata Bonus
            is_keyword_match = paper_id in keyword_matches
            metadata_bonus = 0.15 if is_keyword_match else 0.0
            
            final_score = (bert_score * 0.85) + metadata_bonus
            
            combined_results[paper_id] = SearchResult(
                id=paper_id,
                score=min(final_score, 1.0),
                payload=hit.payload
            )
            
            # Mark as processed if it was in keyword matches
            if is_keyword_match:
                del keyword_matches[paper_id]

        # Add remaining keyword-only matches (rare cases)
        for paper_id, paper in keyword_matches.items():
            # Fallback score for keyword-only matches
            combined_results[paper_id] = SearchResult(
                id=paper_id,
                score=0.75, 
                payload={
                    "title": paper.title,
                    "author": paper.author,
                    "year": paper.year,
                    "abstract": paper.abstract,
                    "department": paper.department,
                    "project_type": paper.project_type,
                    "degree_program": paper.degree_program,
                    "citation_count": paper.citation_count
                }
            )

        # Convert to list and filter by threshold
        search_results = [res for res in combined_results.values() if res.score >= threshold]
        
        # Sort by score descending
        search_results.sort(key=lambda x: x.score, reverse=True)
        
        print(f"Search completed. Found {len(search_results)} relevant results.")
        return search_results
    except Exception as e:
        import traceback
        print(f"SEARCH ERROR: {type(e).__name__} - {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/{paper_id}/recommendations", response_model=List[SearchResult])
async def get_paper_recommendations(
    paper_id: int, 
    limit: int = 5,
    author: Optional[str] = None,
    year: Optional[str] = None,
    department: Optional[str] = None
):
    try:
        print(f"--- Recommendations requested for Paper ID: {paper_id} ---")
        
        # Construct Metadata Filter for Qdrant (Narrow Down)
        qdrant_filter = models.Filter(
            must_not=[models.HasIdCondition(has_id=[paper_id])]
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

        results = vector_db.recommend(paper_id, limit=limit, filter_obj=qdrant_filter)
        
        search_results = []
        for hit in results:
            search_results.append(SearchResult(
                id=hit.id,
                score=hit.score,
                payload=hit.payload
            ))
            
        print(f"Returned {len(search_results)} recommendations.")
        return search_results
    except Exception as e:
        import traceback
        print(f"RECOMMENDATION ERROR: {type(e).__name__} - {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))



@router.delete("/{paper_id}", dependencies=[Depends(admin_required)])
async def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    db_paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not db_paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # 1. Delete from Qdrant
    try:
        vector_db.delete_paper(paper_id)
    except Exception as e:
        print(f"Error deleting from Qdrant: {e}")

    # 2. Delete physical file
    if os.path.exists(db_paper.file_path):
        try:
            os.remove(db_paper.file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")

    # 3. Delete from PostgreSQL/SQLite
    db.delete(db_paper)
    db.commit()

    return {"message": f"Paper {paper_id} deleted successfully"}

@router.put("/{paper_id}", response_model=PaperResponse, dependencies=[Depends(faculty_or_admin_required)])
async def update_paper(paper_id: int, updates: PaperUpdate, db: Session = Depends(get_db)):
    db_paper = db.query(Paper).filter(Paper.id == paper_id).first()
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
        "discussion": db_paper.discussion
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
            "citation_count": db_paper.citation_count
        }
    )

    return db_paper



@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(paper_id: int, db: Session = Depends(get_db)):
    """Fetch a single paper by its ID."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.post("/{paper_id}/view", response_model=ViewCountResponse)
async def record_view(paper_id: int, db: Session = Depends(get_db)):
    """Increment view count. Public endpoint — any visit counts."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    paper.view_count = (paper.view_count or 0) + 1
    db.commit()
    db.refresh(paper)
    return {"view_count": paper.view_count}


@router.get("/{paper_id}/section-pages/{section}", dependencies=[])
async def get_section_pages(
    paper_id: int,
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

    paper = db.query(Paper).filter(Paper.id == paper_id).first()
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

        thumbnails = await ocr_service.extract_page_previews(
            paper.file_path,
            imrad_pages=pages_for_section,
        )
        return {"pages": thumbnails, "section": section}

    except Exception as e:
        print(f"[section-pages] Error for paper {paper_id}/{section}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to render section pages: {str(e)}")


@router.get("/{paper_id}/cite-status", response_model=CitationStatus)
async def get_cite_status(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Check whether the authenticated user has already cited this paper."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    has_cited = db.query(UserCitation).filter(
        UserCitation.user_id == current_user.id,
        UserCitation.paper_id == paper_id
    ).first() is not None
    return {"has_cited": has_cited, "citation_count": paper.citation_count}


@router.post("/{paper_id}/cite", response_model=CitationStatus)
async def cite_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Allow a registered user to cite/vouch for a paper (once per user)."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    already_cited = db.query(UserCitation).filter(
        UserCitation.user_id == current_user.id,
        UserCitation.paper_id == paper_id
    ).first()

    if already_cited:
        raise HTTPException(status_code=409, detail="You have already cited this paper")

    citation = UserCitation(user_id=current_user.id, paper_id=paper_id)
    db.add(citation)
    paper.citation_count = (paper.citation_count or 0) + 1
    db.commit()
    db.refresh(paper)
    return {"has_cited": True, "citation_count": paper.citation_count}