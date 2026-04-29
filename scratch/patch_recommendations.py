"""
Patch script: replaces the old get_paper_recommendations endpoint body
with the new context-aware version that passes full IMRAD text to vector_db.recommend().
"""
import re

target_file = r"c:\Users\SIBIYA GAMING\Documents\Undergraduate Thesis System\lumia_retrieval_bert\app\api\endpoints\papers.py"

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

# Find the exact start marker (the decorator + function signature)
START_MARKER = '@router.get("/{paper_id}/recommendations", response_model=List[SearchResult])'
# Find the end: the next @router or end of file (the double newline after raise)
END_MARKER = '\n\n\n@router.'

start_idx = content.find(START_MARKER)
if start_idx == -1:
    print("ERROR: Could not find start marker in file!")
    exit(1)

end_idx = content.find(END_MARKER, start_idx)
if end_idx == -1:
    print("ERROR: Could not find end marker in file!")
    exit(1)

# What to replace: from START_MARKER to (but not including) END_MARKER
old_block = content[start_idx:end_idx]
print(f"Found block to replace ({len(old_block)} chars, lines {content[:start_idx].count(chr(10))+1} to {content[:end_idx].count(chr(10))+1})")

NEW_FUNCTION = '''@router.get("/{paper_id}/recommendations", response_model=List[SearchResult])
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
        print(f"--- [Smart Recommendations] Paper ID: {real_id} ---")
        
        # ── Step A: Load Source Paper from SQLite ──────────────────────────────
        # We need the full IMRAD text from SQLite (not just the short abstract
        # payload stored in Qdrant) to build per-section context embeddings.
        source_paper = db.query(Paper).filter(Paper.id == real_id).first()
        if not source_paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        # Build a section-keyed dict of the source paper\'s actual full text.
        # Methods + Results are the strongest academic similarity signals.
        # Prefer full extracted text; fall back to pre-generated summaries.
        source_texts: dict = {
            "title":        (source_paper.title or "").strip(),
            "abstract":     (source_paper.abstract or "").strip(),
            "introduction": (source_paper.introduction or source_paper.introduction_summary or "").strip(),
            "methods":      (source_paper.methods or source_paper.methods_summary or "").strip(),
            "results":      (source_paper.results or source_paper.results_summary or "").strip(),
            "discussion":   (source_paper.discussion or source_paper.discussion_summary or "").strip(),
        }
        # Drop empty keys — vector_db.recommend() will fall back gracefully
        source_texts = {k: v for k, v in source_texts.items() if v}
        print(f"[Smart Recommendations] Source sections available: {list(source_texts.keys())}")

        # ── Step B: Qdrant Filter (exclude source + optional metadata) ─────────
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

        # ── Step C: Context-Aware Vector Search ───────────────────────────────
        # vector_db.recommend() embeds each source section as a live query vector
        # and searches the matching IMRAD slot in Qdrant.  This means we find papers
        # that are semantically similar in *what they did and found*, not just
        # geometrically close to the source point in vector space.
        results = vector_db.recommend(
            real_id,
            limit=60,               # generous pool; cross-encoder will refine
            filter_obj=qdrant_filter,
            source_texts=source_texts,
        )
        
        if not results:
            return []

        # ── Step D: Cross-Encoder Re-ranking with Rich Context ────────────────
        # Build a compound context string: title + abstract + methodology + results.
        # This gives the CE a full academic picture of the source paper — not just
        # its topic, but what it studied and how.
        ce_parts = [source_paper.title or ""]
        if source_paper.abstract:
            ce_parts.append(source_paper.abstract[:400])
        methods_txt = source_paper.methods_summary or source_paper.methods or ""
        if methods_txt:
            ce_parts.append(methods_txt[:300])
        results_txt = source_paper.results_summary or source_paper.results or ""
        if results_txt:
            ce_parts.append(results_txt[:200])
        ce_query = " | ".join(p for p in ce_parts if p.strip())[:1000]

        re_rank_candidates = []
        for hit in results:
            if hit.payload.get("title") == source_paper.title:
                continue
            cand_title    = hit.payload.get("title") or ""
            cand_abstract = hit.payload.get("abstract") or ""
            cand_text     = f"{cand_title} | {cand_abstract[:500]}"
            re_rank_candidates.append({
                "id":      hit.id,
                "score":   hit.score,
                "text":    cand_text,
                "payload": hit.payload
            })

        reranked = rerank_with_cross_encoder(
            query=ce_query,
            candidates=re_rank_candidates,
            top_k=limit
        )

        # ── Step E: Score Fusion + Human-Readable Reason Generation ──────────
        search_results = []
        source_kws = set(k.strip().lower() for k in (source_paper.keywords or "").split(",") if k.strip())
        
        for c in reranked:
            ce_score = c.get("rerank_score", 0.0)
            # Normalize ms-marco cross-encoder range (~-10..+10) to 0–1
            norm_ce = max(0.0, min(1.0, (ce_score + 5) / 10))
            # 35% multi-section vector similarity + 65% cross-encoder deep context
            final_score = (c["score"] * 0.35) + (norm_ce * 0.65)

            if final_score < settings.RECOMMENDATION_THRESHOLD:
                continue

            reasons = []
            cand_payload  = c["payload"]
            match_section = cand_payload.get("_match_section", "abstract")
            
            # 1. Keyword/concept overlap — most tangible signal for the reader
            cand_kws = set(k.strip().lower() for k in (cand_payload.get("keywords") or "").split(",") if k.strip())
            overlap = source_kws & cand_kws
            if overlap:
                reasons.append(f"Shares key concepts: {\', \'.join(list(overlap)[:3])}")
            
            # 2. IMRAD section alignment — explains *why* it is similar
            section_reason_map = {
                "methods":      "Uses closely aligned research methodology",
                "results":      "Reports similar findings and outcomes",
                "discussion":   "Shares interpretive conclusions and implications",
                "abstract":     "Addresses the same core research problem",
                "introduction": "Investigates the same research domain",
                "title":        "Closely related research topic",
            }
            section_reason = section_reason_map.get(match_section)
            if section_reason:
                reasons.append(section_reason)
            
            # 3. Semantic verdict fallback
            if not reasons:
                if norm_ce > 0.88:
                    reasons.append("High semantic overlap in research objectives")
                elif norm_ce > 0.72:
                    reasons.append("Significant overlap in research problem and approach")
                else:
                    reasons.append("Contextually complementary research study")

            final_reason = " • ".join(reasons[:2])

            search_results.append(SearchResult(
                id=encode_id(c["id"]),
                score=round(final_score, 4),
                recommendation_reason=final_reason,
                payload=cand_payload
            ))
            
        print(f"[Smart Recommendations] Returning {len(search_results)} context-aware recommendations.")
        return search_results
    except Exception as e:
        import traceback
        print(f"RECOMMENDATION ERROR: {type(e).__name__} - {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))'''

new_content = content[:start_idx] + NEW_FUNCTION + content[end_idx:]

with open(target_file, "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"✅ Successfully patched {target_file}")
print(f"   Old block: {len(old_block)} chars")
print(f"   New block: {len(NEW_FUNCTION)} chars")
