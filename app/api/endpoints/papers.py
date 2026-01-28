from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import shutil
import os
import uuid

from app.core.database import get_db
from app.models.paper import Paper
from app.schemas.paper import PaperResponse, SearchResult, PaperUpdate
from app.services.ocr_service import ocr_service
from app.services.embedding_service import embedding_service
from app.services.vector_db import vector_db

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=PaperResponse)
async def upload_paper(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 1. Extract Metadata using OCR
    metadata = await ocr_service.extract_metadata(file_path)

    # 2. Save to PostgreSQL
    db_paper = Paper(
        title=metadata["title"],
        author=metadata["author"],
        year=metadata["year"],
        abstract=metadata["abstract"],
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
            "abstract": db_paper.abstract
        }
    )

    return db_paper

@router.get("/", response_model=List[PaperResponse])
async def list_papers(db: Session = Depends(get_db)):
    return db.query(Paper).all()

@router.get("/search", response_model=List[SearchResult])
async def search_papers(query: str, threshold: float = 0.4):
    try:
        print(f"--- Search started for query: '{query}' (Threshold: {threshold}) ---")
        
        # 1. Generate query embedding
        print("Generating query embedding...")
        query_vector = embedding_service.get_embedding(query)
        
        # 2. Search in Qdrant (Max of Title or Abstract)
        print("Searching across Titles and Abstracts...")
        results = vector_db.search_max(query_vector)
        print(f"Raw Qdrant found {len(results)} matches.")
        
        search_results = []
        for hit in results:
            print(f" -> RAW MATCH: ID={hit.id}, Score={hit.score:.4f}, Title='{hit.payload.get('title')}'")
            if hit.score >= threshold:
                search_results.append(SearchResult(
                    id=hit.id,
                    score=hit.score,
                    payload=hit.payload
                ))
            else:
                print(f"    (Skipping above match - score below {threshold} threshold)")

        
        print(f"Search completed. Found {len(search_results)} relevant results.")
        return search_results
    except Exception as e:
        import traceback
        print(f"SEARCH ERROR: {type(e).__name__} - {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))



@router.delete("/{paper_id}")
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

@router.put("/{paper_id}", response_model=PaperResponse)
async def update_paper(paper_id: int, updates: PaperUpdate, db: Session = Depends(get_db)):
    db_paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not db_paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # Update SQLite database fields
    update_data = updates.dict(exclude_unset=True)
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
            "abstract": db_paper.abstract
        }
    )

    return db_paper



