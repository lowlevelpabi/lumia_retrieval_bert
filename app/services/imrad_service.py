import re
from typing import Dict, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# IMRAD Configuration
# ─────────────────────────────────────────────────────────────────────────────

# Set to False to exclude the abstract vector from all Qdrant prefetch queries.
# This allows easy removal of abstract-based search without touching other files.
INCLUDE_ABSTRACT_VECTOR: bool = True

# Ordered list of IMRAD section keys (order determines slice boundaries)
IMRAD_SECTION_KEYS: List[str] = ["introduction", "methods", "results", "discussion"]

# Heading detection patterns: supports both IMRAD-style and CvSU Chapter-style headings
IMRAD_PATTERNS: Dict[str, List[str]] = {
    "introduction": [
        r"\bINTRODUCTION\b",
        r"\bCHAPTER\s+I\b",
        r"\bCHAPTER\s+1\b",
    ],
    "methods": [
        r"\bMETHODOLOGY\b",
        r"\bMETHODS\b",
        r"\bMATERIALS\s+AND\s+METHODS\b",
        r"\bRESEARCH\s+DESIGN\b",
        r"\bCHAPTER\s+II\b",
        r"\bCHAPTER\s+2\b",
        r"\bCHAPTER\s+III\b",
        r"\bCHAPTER\s+3\b",
    ],
    "results": [
        r"\bRESULTS\b",
        r"\bFINDINGS\b",
        r"\bRESULTS\s+AND\s+DISCUSSION\b",
        r"\bCHAPTER\s+IV\b",
        r"\bCHAPTER\s+4\b",
    ],
    "discussion": [
        r"\bDISCUSSION\b",
        r"\bCONCLUSION\b",
        r"\bCONCLUSIONS\s+AND\s+RECOMMENDATIONS\b",
        r"\bCHAPTER\s+V\b",
        r"\bCHAPTER\s+5\b",
    ],
}

# Maximum characters to extract per section (keeps embeddings focused)
MAX_SECTION_CHARS: int = 4000

# Minimum characters for a section to be considered valid (avoids empty/noise)
MIN_SECTION_CHARS: int = 80


# ─────────────────────────────────────────────────────────────────────────────
# IMRAD Service
# ─────────────────────────────────────────────────────────────────────────────

class IMRADService:

    def extract_sections(self, full_text: str) -> Dict[str, str]:
        """
        Detects IMRAD section headings in full_text and extracts each
        section's content as a text slice.

        Supports both IMRAD-style headings (INTRODUCTION, METHODOLOGY, etc.)
        and CvSU Chapter-style headings (CHAPTER I, CHAPTER II, etc.).

        Returns a dict of {section_key: content_text} for only those sections
        that were successfully detected and contain enough content.
        """
        if not full_text or len(full_text.strip()) < 100:
            print("[IMRAD] Text too short for section detection.")
            return {}

        # Step 1: Find the earliest match position for each section key
        anchors: Dict[str, int] = {}
        for section_key, patterns in IMRAD_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    # Use the END of the matched heading as the content start
                    anchors[section_key] = match.end()
                    break  # First pattern match wins; stop checking others

        if not anchors:
            print("[IMRAD] No structural headings detected in document.")
            return {}

        # Step 2: Sort anchors by their position in the text
        sorted_anchors = sorted(anchors.items(), key=lambda x: x[1])
        found_keys = [k for k, _ in sorted_anchors]
        print(f"[IMRAD] Detected sections: {found_keys}")

        # Step 3: Extract text slice between each anchor and the next
        sections: Dict[str, str] = {}
        for i, (section_key, start_pos) in enumerate(sorted_anchors):
            # Content ends at the next section's heading start (or +MAX_SECTION_CHARS)
            if i + 1 < len(sorted_anchors):
                # Find the start of the NEXT heading (before its content)
                next_section_key = sorted_anchors[i + 1][0]
                next_pattern_list = IMRAD_PATTERNS[next_section_key]
                end_pos = start_pos + MAX_SECTION_CHARS  # default
                for pat in next_pattern_list:
                    m = re.search(pat, full_text[start_pos:], re.IGNORECASE)
                    if m:
                        end_pos = start_pos + m.start()
                        break
            else:
                end_pos = start_pos + MAX_SECTION_CHARS

            raw_content = full_text[start_pos:end_pos].strip()

            # Clean up: remove standalone page numbers and blank lines
            lines = raw_content.split('\n')
            cleaned = [
                line.strip() for line in lines
                if line.strip() and not re.fullmatch(r'[\divxIVX]+', line.strip())
            ]
            content = " ".join(cleaned)

            if len(content) >= MIN_SECTION_CHARS:
                sections[section_key] = content[:MAX_SECTION_CHARS]
            else:
                print(f"[IMRAD] Section '{section_key}' too short ({len(content)} chars), skipping.")

        return sections

    def get_all_vector_names(self) -> List[str]:
        """
        Returns the full list of vector names that should participate in search.
        Dynamically includes/excludes 'abstract' based on INCLUDE_ABSTRACT_VECTOR.
        Used by vector_db.py to build the Qdrant prefetch list without hardcoding.
        """
        names = ["title"]
        if INCLUDE_ABSTRACT_VECTOR:
            names.append("abstract")
        names.extend(IMRAD_SECTION_KEYS)
        return names

    def get_qdrant_vector_config(self):
        """
        Returns the full named-vector config dict for Qdrant collection creation.
        All 6 vectors are always registered in Qdrant (sparse is fine).
        INCLUDE_ABSTRACT_VECTOR only controls search, not collection schema.
        """
        from qdrant_client.http import models
        return {
            "title":        models.VectorParams(size=384, distance=models.Distance.COSINE),
            "abstract":     models.VectorParams(size=384, distance=models.Distance.COSINE),
            "introduction": models.VectorParams(size=384, distance=models.Distance.COSINE),
            "methods":      models.VectorParams(size=384, distance=models.Distance.COSINE),
            "results":      models.VectorParams(size=384, distance=models.Distance.COSINE),
            "discussion":   models.VectorParams(size=384, distance=models.Distance.COSINE),
        }

    def build_vectors(
        self,
        title: str,
        sections: Dict[str, str],
        abstract: str = ""
    ) -> Dict[str, List[float]]:
        """
        Builds the full vector dict for a paper to upsert into Qdrant.
        Always includes 'title'. Includes 'abstract' if INCLUDE_ABSTRACT_VECTOR is True.
        Only includes IMRAD section vectors that were actually detected.
        """
        # Import here to avoid circular imports at module level
        from app.services.embedding_service import embedding_service

        vectors: Dict[str, List[float]] = {}

        # Title vector — always present
        if title and title.strip():
            vectors["title"] = embedding_service.get_embedding(title[:512])

        # Abstract vector — controlled by flag
        if INCLUDE_ABSTRACT_VECTOR and abstract and abstract.strip():
            vectors["abstract"] = embedding_service.get_embedding(abstract[:4000])

        # IMRAD section vectors — only for detected sections
        for section_key, content in sections.items():
            if section_key in IMRAD_SECTION_KEYS and content and len(content.strip()) >= MIN_SECTION_CHARS:
                vectors[section_key] = embedding_service.get_embedding(content)

        detected = list(vectors.keys())
        print(f"[IMRAD] Built vectors for: {detected}")
        return vectors


# Singleton instance
imrad_service = IMRADService()
