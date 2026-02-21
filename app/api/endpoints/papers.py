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
from app.schemas.paper import PaperResponse, SearchResult, PaperUpdate
from app.services.ocr_service import ocr_service
from app.services.embedding_service import embedding_service
from app.services.vector_db import vector_db
from app.api.deps import admin_required, faculty_or_admin_required

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=PaperResponse, dependencies=[Depends(faculty_or_admin_required)])
async def upload_paper(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 1. Extract Metadata using OCR
    metadata = await ocr_service.extract_metadata(file_path)

    # 2. Save to SQLite
    db_paper = Paper(
        title=metadata["title"],
        author=metadata["author"],
        year=metadata["year"],
        abstract=metadata["abstract"],
        department=metadata["department"],
        keywords=metadata["keywords"],
        citation_count=metadata["citation_count"],
        file_path=file_path
    )
    db.add(db_paper)
    db.commit()
    db.refresh(db_paper)

    # 3. Generate Multi-Vectors and Save to Qdrant
    title_vector = embedding_service.get_embedding(db_paper.title)
    abstract_vector = embedding_service.get_embedding(db_paper.abstract)
    
    vector_db.upsert_paper(
        paper_id=db_paper.id,
        vectors={
            "title": title_vector,
            "abstract": abstract_vector
        },
        metadata={
            "title": db_paper.title,
            "author": db_paper.author,
            "year": db_paper.year,
            "abstract": db_paper.abstract,
            "department": db_paper.department,
            "keywords": db_paper.keywords,
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
    department: Optional[str] = None,
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
        if department: sql_query = sql_query.filter(Paper.department == department)
        
        keyword_matches = {p.id: p for p in sql_query.all()}
        
        # 3. Generate query embedding for semantic search
        print("Generating query embedding for semantic search...")
        query_vector = embedding_service.get_embedding(query)
        
        # 4. Search in Qdrant (Max of Title or Abstract)
        print("Searching across Titles and Abstracts in Qdrant...")
        semantic_results = vector_db.search_max(query_vector, filter_obj=qdrant_filter)
        
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

    # Update Qdrant Multi-Vectors
    title_vector = embedding_service.get_embedding(db_paper.title)
    abstract_vector = embedding_service.get_embedding(db_paper.abstract)
    
    vector_db.upsert_paper(
        paper_id=db_paper.id,
        vectors={
            "title": title_vector,
            "abstract": abstract_vector
        },
        metadata={
            "title": db_paper.title,
            "author": db_paper.author,
            "year": db_paper.year,
            "abstract": db_paper.abstract,
            "department": db_paper.department,
            "keywords": db_paper.keywords,
            "citation_count": db_paper.citation_count
        }
    )

    return db_paper



