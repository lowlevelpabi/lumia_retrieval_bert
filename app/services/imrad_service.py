import re
from typing import Dict, List, Optional, Union
from difflib import SequenceMatcher

# ─────────────────────────────────────────────────────────────────────────────
# IMRAD Configuration
# ─────────────────────────────────────────────────────────────────────────────

INCLUDE_ABSTRACT_VECTOR: bool = True
IMRAD_SECTION_KEYS: List[str] = ["introduction", "methods", "results", "discussion"]
MAX_SECTION_CHARS: int  = 5000
MIN_SECTION_CHARS: int  = 100

# Number of pages shown in the frontend preview per section.
# The review screen only needs to show the heading page + a few body pages —
# not every single page of a 90-page Results section.
PREVIEW_PAGES_PER_SECTION: int = 3

FUZZY_THRESHOLD: float        = 0.60
EARLY_ACCEPT_THRESHOLD: float = 0.88

# A 'first candidate' (score between FUZZY_THRESHOLD and EARLY_ACCEPT_THRESHOLD)
# must score at least this high to be accepted. This prevents single body words
# like 'institutions' (score 0.67) from winning just because they appear first.
FIRST_CANDIDATE_MIN_SCORE: float = 0.80

# Heading lines shorter than this are almost certainly body words, not headings.
# 'INTRODUCTION' is 12 chars, 'METHODOLOGY' is 11, 'RESULTS' is 7.
MIN_HEADING_CHARS: int = 6

# ── Canonical heading vocabulary ─────────────────────────────────────────────
HEADING_KEYWORDS: Dict[str, List[str]] = {
    "introduction": [
        "INTRODUCTION", "CHAPTER I", "CHAPTER 1",
        "I. INTRODUCTION", "1. INTRODUCTION",
    ],
    "methods": [
        "METHODOLOGY", "METHODS", "RESEARCH METHODOLOGY",
        "MATERIALS AND METHODS", "CHAPTER III", "CHAPTER 3",
        "III. METHODOLOGY", "3. METHODOLOGY",
    ],
    "results": [
        "RESULTS", "FINDINGS", "CHAPTER IV", "CHAPTER 4",
        "IV. RESULTS", "4. RESULTS",
    ],
    "results_and_discussion": [
        "RESULTS AND DISCUSSION", "RESULTS AND DISCUSSIONS",
        "CHAPTER IV RESULTS AND DISCUSSION",
        "IV. RESULTS AND DISCUSSION", "4. RESULTS AND DISCUSSION",
    ],
    "discussion": [
        "CONCLUSION", "CONCLUSIONS", "CONCLUSIONS AND RECOMMENDATIONS",
        "CONCLUSION AND RECOMMENDATION",
        "SUMMARY CONCLUSIONS AND RECOMMENDATIONS",
        "CHAPTER V", "CHAPTER 5", "V. CONCLUSION", "5. CONCLUSION",
    ],
}

FALSE_POSITIVE_KEYWORDS: List[str] = [
    "REVIEW OF RELATED LITERATURE", "REVIEW OF RELATED STUDIES",
    "RELATED LITERATURE AND STUDIES", "RELATED LITERATURE", "RELATED STUDIES",
    "FOREIGN LITERATURE", "LOCAL LITERATURE", "FOREIGN STUDIES", "LOCAL STUDIES",
    "CONCEPTUAL FRAMEWORK", "THEORETICAL FRAMEWORK", "SCOPE AND DELIMITATION",
    "SIGNIFICANCE OF THE STUDY", "STATEMENT OF THE PROBLEM",
    "RESEARCH QUESTIONS", "HYPOTHESIS", "OBJECTIVES",
    "ACKNOWLEDGMENT", "ACKNOWLEDGMENTS", "REFERENCES", "BIBLIOGRAPHY",
    "APPENDIX", "APPENDICES", "LIST OF TABLES", "LIST OF FIGURES",
    "LIST OF APPENDICES", "TABLE OF CONTENTS", "ABSTRACT", "SYNTHESIS",
    "RESEARCH GAP", "BACKGROUND OF THE STUDY",
    "CRITERIA", "RUBRIC", "EVALUATION", "RATING", "SCORE", "SUITABILITY",
]

# ── Back-matter heading patterns ─────────────────────────────────────────────
# When ANY of these appear at the TOP of a page (first 300 chars), that page
# marks the start of back-matter. Sections never extend past this boundary.
# This is what stops Results/Discussion from running all the way to page 132.
BACK_MATTER_PAGE_PATTERNS: List[str] = [
    r"\bREFERENCES\b",
    r"\bBIBLIOGRAPHY\b",
    r"\bACKNOWLEDGMENTS?\b",
    r"\bAPPENDI(?:X|CES)\b",
    r"\bANNEX\b",
    r"\bCURRICULUM\s+VITAE\b",
    r"\bABOUT\s+THE\s+AUTHOR\b",
]

# ── Chapter I sub-section heading patterns ──────────────────────────────────
# In Filipino thesis format, Chapter I (Introduction) contains many sub-sections
# like Background of the Study, SOP, Objectives, etc. When any of these appear
# at the TOP of a page (first 400 chars), that page is the end of the pure
# Introduction body — we stop the intro's page range there.
# This means Introduction gets exactly 1 page (or however many pages its own
# body text spans) rather than bleeding into all 25 pages of Chapter I.
INTRO_SUBSECTION_PATTERNS: List[str] = [
    r"\bBackground\s+of\s+the\s+Study\b",
    r"\bStatement\s+of\s+the\s+Problem\b",
    r"\bResearch\s+(?:Objectives?|Questions?)\b",
    r"\bObjectives?\s+of\s+the\s+Study\b",
    r"\bSignificance\s+of\s+the\s+Study\b",
    r"\bScope\s+and\s+(?:Delimitation|Limitation)\b",
    r"\bDefinition\s+of\s+Terms\b",
    r"\bConceptual\s+Framework\b",
    r"\bTheoretical\s+Framework\b",
    r"\bReview\s+of\s+(?:Related\s+)?Literature\b",
    r"\bHypothes[ie]s\b",
]

# ── TOC / rubric page skip patterns ──────────────────────────────────────────
# Require multiple co-occurring signals to avoid skipping body pages.
SKIP_PAGE_PATTERNS: List[str] = [
    r"\.{4,}",
    r"\bTable\s+of\s+Contents\b",
    r"\bList\s+of\s+(?:Tables|Figures|Appendices)\b",
    r"\bAppendi(?:x|ces)\b",
    r"\bBibliography\b",
    r"\bAcknowledgment",
    r"(?=.*\bRubric\b)(?=.*\bCriteria\b)",
    r"(?=.*\bCriteria\b)(?=.*\bScore\b)",
    r"(?=.*\bSuitability\s+of\b)(?=.*\bTotal\s+Score\b)",
]

# ── Methodology sub-heading checklist ────────────────────────────────────────
METHODOLOGY_SUBHEADINGS: List[Dict] = [
    {"label": "Research Design",            "patterns": [r"Research\s+Design"]},
    {"label": "Research Approach",          "patterns": [r"Research\s+Approach"]},
    {"label": "Research Settings",          "patterns": [r"Research\s+Setting"]},
    {"label": "Participants / Respondents", "patterns": [r"Participants?", r"Respondents?"]},
    {"label": "Research Instruments",       "patterns": [r"Research\s+Instruments?"]},
    {"label": "Data Collection Procedure",  "patterns": [r"Data\s+Collection"]},
    {"label": "Data Analysis Techniques",   "patterns": [r"Data\s+Analy(?:sis|tical)(?:\s+Techni(?:que|cal)?)?",
                                                          r"Data\s+Analysis"]},
    {"label": "Ethical Considerations",     "patterns": [r"Ethical\s+Considerations?"]},
    {"label": "Development Model",          "patterns": [r"Development\s+Model"]},
]

BOILERPLATE_PATTERNS: List[str] = [
    r"Cavite State University", r"CvSU", r"Imus Campus",
    r"Bachelor of Science", r"in partial fulfillment",
    r"requirements for the degree", r"prepared under the supervision",
    r"Adviser\s*:", r"Department of ", r"College of ",
    r"Undergraduate Thesis", r"undergraduate thesis",
    r"submitted to the faculty", r"An undergraduate thesis",
    r"Contribution No\.",
    r"^\s*\d+\s*$",
    r"^\s*[ivxIVX]+\s*$",
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_text(text: str) -> str:
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'-\n\s*', '', text)
    text = re.sub(r'([a-z\.,])([A-Z]{2,})', r'\1\n\2', text)
    text = re.sub(r'[^\S\n]+', ' ', text)
    return text


def _strip_page_header(
    text: str,
    title: str = "",
    authors: str = "",
) -> str:
    """
    Remove the cover-page header block from the first page of a section.

    Core strategy: find the IMRAD section heading word in the text and cut
    everything UP TO AND INCLUDING that heading word. What remains is the
    actual body text. This handles the common pypdf layout where the entire
    page is one long string:
      "SMART RESEARCH: AN AI-POWERED... INTRODUCTION The growing number..."
    After cut: "The growing number..."

    Fallback: if no heading word is found, strip known boilerplate phrases
    from the first 800 characters individually.
    """
    ALL_SECTION_HEADINGS = sorted(
        [kw for kws in HEADING_KEYWORDS.values() for kw in kws]
        + ["INTRODUCTION", "METHODOLOGY", "METHODS", "RESULTS", "DISCUSSION",
           "CONCLUSION", "FINDINGS"],
        key=len, reverse=True  # longest first so "RESULTS AND DISCUSSION" beats "RESULTS"
    )

    upper_text = text.upper()

    # Find the earliest heading word in the text and cut everything before + including it
    earliest_pos = -1
    earliest_len = 0
    for heading in ALL_SECTION_HEADINGS:
        pos = upper_text.find(heading.upper())
        if pos != -1 and (earliest_pos == -1 or pos < earliest_pos):
            earliest_pos = pos
            earliest_len = len(heading)

    if earliest_pos != -1:
        # Everything after the heading word is the body
        result = text[earliest_pos + earliest_len:].strip()
        print(f"[IMRAD][strip] Cut header at pos {earliest_pos}, "
              f"heading='{text[earliest_pos:earliest_pos+earliest_len]}', "
              f"body starts: {repr(result[:60])}")
        return result

    # ── Fallback: heading not found, strip boilerplate phrases individually ──
    print("[IMRAD][strip] No heading anchor found — falling back to phrase stripping")
    result = text

    if title and title not in ("N/A", ""):
        # Collapse whitespace in title before matching (pypdf inserts random spaces)
        title_normalized = re.sub(r"\s+", r"\s+", re.escape(title.strip()))
        result = re.sub(title_normalized, " ", result[:800], flags=re.IGNORECASE) + result[800:]

    if authors and authors not in ("N/A", ""):
        for author in authors.split("|"):
            author = author.strip()
            if author:
                result = re.sub(re.escape(author), " ", result[:800], flags=re.IGNORECASE) + result[800:]

    HEADER_PHRASES = [
        r"Cavite\s+State\s+University[^\n.]*",
        r"CvSU[^\n.]*",
        r"Bachelor\s+of\s+Science[^\n.]*",
        r"in\s+partial\s+fulfillment[^\n.]*",
        r"submitted\s+to\s+the\s+faculty[^\n.]*",
        r"Prepared\s+under\s+the\s+supervision[^\n.]*",
        r"Adviser\s*:[^\n.]*",
        r"Department\s+of\s+[A-Za-z\s]{3,40}",
        r"College\s+of\s+[A-Za-z\s]{3,40}",
        r"supervision\s+of\s*[-–—]?\s*",
        r"\bB\.?S\.?\s+in\s+[A-Za-z\s]{3,40}",
    ]
    top = result[:800]
    for phrase in HEADER_PHRASES:
        top = re.sub(phrase, " ", top, flags=re.IGNORECASE)
    result = top + result[800:]

    result = re.sub(r"[ \t]{2,}", " ", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def _clean_heading_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r'\s+\d{1,3}\s*$', '', line)
    line = re.sub(r'^(?:CHAPTER\s+)?(?:[IVXLC]+|\d+)[\.\s]+', '', line, flags=re.IGNORECASE)
    return line.strip()


def _fuzzy_score(a: str, b: str) -> float:
    return SequenceMatcher(None, a.upper(), b.upper()).ratio()


def _is_candidate_line(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 100 or len(line) < MIN_HEADING_CHARS:
        return False
    if re.fullmatch(r'[\d\s\.\-\,\(\)]+', line):
        return False
    if any(re.search(bp, line, re.IGNORECASE) for bp in BOILERPLATE_PATTERNS):
        return False
    return True


def _is_skip_page(text: str) -> bool:
    """True only for TOC / appendix / rubric pages — NOT normal body pages."""
    for pat in SKIP_PAGE_PATTERNS:
        if re.search(pat, text, re.IGNORECASE | re.DOTALL):
            return True
    return False


def _is_back_matter_page(text: str) -> bool:
    """
    True when the first 300 characters of a page contain a back-matter heading
    (References, Bibliography, Appendix, etc.).
    Checking only the top of the page means a body page that *mentions*
    references in passing won't be treated as a boundary.
    """
    top = _normalize_text(text)[:300]
    for pat in BACK_MATTER_PAGE_PATTERNS:
        if re.search(pat, top, re.IGNORECASE):
            return True
    return False


def _find_back_matter_start(page_text_map: Dict[int, str], after_page: int) -> Optional[int]:
    """
    Return the first page number (at or after `after_page`) whose top content
    matches a back-matter heading.  Returns None if no such page is found.
    """
    for pg in sorted(page_text_map.keys()):
        if pg < after_page:
            continue
        if _is_back_matter_page(page_text_map[pg]):
            return pg
    return None


def _find_intro_end_page(
    page_text_map: Dict[int, str],
    intro_start: int,
    next_section_start: int,
) -> int:
    """
    For Introduction specifically: scan pages from intro_start+1 up to
    next_section_start-1. Return the page BEFORE the first page whose top
    400 chars contain a Chapter I sub-section heading (Background, SOP, etc.).
    If no sub-section heading is found, return next_section_start - 1 as normal.
    """
    for pg in range(intro_start + 1, next_section_start):
        text = page_text_map.get(pg, "")
        top  = _normalize_text(text)[:400]
        if any(re.search(pat, top, re.IGNORECASE) for pat in INTRO_SUBSECTION_PATTERNS):
            print(f"[IMRAD] Introduction ends at page {pg - 1} "
                  f"(sub-section heading found on page {pg})")
            return pg - 1
    return next_section_start - 1


# ─────────────────────────────────────────────────────────────────────────────
# Core scorer
# ─────────────────────────────────────────────────────────────────────────────

def _find_section_page(
    section_key: str,
    page_text_map: Dict[int, str],
    min_page: int = 1,
) -> Optional[int]:
    keywords = HEADING_KEYWORDS.get(section_key, [])
    if not keywords:
        return None

    first_candidate_page  : Optional[int] = None
    first_candidate_score : float         = 0.0
    first_candidate_line  : str           = ""

    print(f"\n[IMRAD][score] ── Scoring pages for '{section_key}' (min_page={min_page}) ──")

    for page_num in sorted(page_text_map.keys()):
        if page_num < min_page:
            continue

        raw_text   = page_text_map[page_num]
        normalized = _normalize_text(raw_text)

        if _is_skip_page(normalized):
            print(f"  page {page_num:>3} │ [SKIPPED — TOC/appendix/rubric page]")
            continue

        for line in normalized.split('\n'):
            if not _is_candidate_line(line):
                continue
            clean = _clean_heading_line(line)
            if not clean:
                continue

            target_score = max(
                max(_fuzzy_score(clean, kw) for kw in keywords),
                max(_fuzzy_score(line.strip(), kw) for kw in keywords),
            )
            if target_score < FUZZY_THRESHOLD:
                continue

            fp_score  = max(
                (_fuzzy_score(clean, fp) for fp in FALSE_POSITIVE_KEYWORDS),
                default=0.0,
            )
            penalised = target_score
            if fp_score >= target_score:
                penalised = target_score * 0.25
            elif fp_score >= FUZZY_THRESHOLD:
                penalised = target_score * 0.55

            if penalised < FUZZY_THRESHOLD:
                continue

            print(f"  page {page_num:>3} │ {repr(clean):<45} "
                  f"target={target_score:.2f} fp={fp_score:.2f} → {penalised:.2f}")

            if penalised >= EARLY_ACCEPT_THRESHOLD:
                print(f"[IMRAD][score] '{section_key}' → page {page_num} "
                      f"(early accept, score={penalised:.2f})\n")
                return page_num

            # Only record as first candidate if score clears the higher bar.
            # This stops weak body-word matches (e.g. 'institutions' 0.67)
            # from winning just by appearing before the real heading.
            if first_candidate_page is None and penalised >= FIRST_CANDIDATE_MIN_SCORE:
                first_candidate_page  = page_num
                first_candidate_score = penalised
                first_candidate_line  = clean

    if first_candidate_page is not None:
        print(f"[IMRAD][score] '{section_key}' → page {first_candidate_page} "
              f"(first candidate, score={first_candidate_score:.2f})\n")
        return first_candidate_page

    print(f"[IMRAD][score] '{section_key}' → NOT FOUND\n")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────────────────────

class IMRADService:

    def extract_sections(self, page_input: Union[str, Dict[int, str]], title: str = "", authors: str = "") -> Dict[str, any]:
        """
        Detect IMRAD section headings and extract content per section.

        Returns:
            {
              'sections':      {section_key: text},
              'section_pages': {section_key: [all page numbers in section]},
              'imrad_pages':   sorted flat list of PREVIEW pages only
                               (start_page + up to PREVIEW_PAGES_PER_SECTION per section)
            }

        NOTE: 'section_pages' contains ALL pages for embedding/search purposes.
              'imrad_pages'   contains only the first few pages per section
              for the frontend review thumbnail display.
        """
        if not page_input:
            return {"sections": {}, "section_pages": {}, "imrad_pages": []}

        if isinstance(page_input, str):
            page_text_map = {1: page_input}
        else:
            page_text_map = dict(page_input)

        all_pages = sorted(page_text_map.keys())

        # ── 1. Detect section start pages ────────────────────────────────────
        already_claimed: Dict[int, str] = {}

        combined_page = _find_section_page(
            "results_and_discussion", page_text_map, min_page=1
        )

        section_start_pages: Dict[str, int] = {}
        min_page = 1

        for section_key in IMRAD_SECTION_KEYS:
            if combined_page is not None and section_key in ("results", "discussion"):
                if combined_page >= min_page:
                    section_start_pages[section_key] = combined_page
                continue
            pg = _find_section_page(section_key, page_text_map, min_page=min_page)
            if pg is not None:
                section_start_pages[section_key] = pg
                already_claimed[pg] = section_key
                min_page = pg + 1

        if not section_start_pages:
            print("[IMRAD] ⚠️  No sections detected.")
            return {"sections": {}, "section_pages": {}, "imrad_pages": []}

        print(f"[IMRAD] Final section pages: {section_start_pages}")

        # ── 2. Find the back-matter boundary ─────────────────────────────────
        # Determine the earliest page that starts References/Appendix/etc.
        # No section may extend past this page.
        first_imrad_page = min(section_start_pages.values())
        back_matter_start = _find_back_matter_start(
            page_text_map, after_page=first_imrad_page + 1
        )
        if back_matter_start:
            print(f"[IMRAD] Back-matter boundary detected at page {back_matter_start}")
        last_valid_page = (back_matter_start - 1) if back_matter_start else all_pages[-1]

        # ── 3. Extract text per section ───────────────────────────────────────
        result_sections: Dict[str, str]       = {}
        result_pages:    Dict[str, List[int]] = {}

        # Dynamic per-paper strip patterns — title fragments and author names.
        # These prevent the cover page header from leaking into section text.
        dynamic_strip: List[str] = []
        if title and title not in ("N/A", ""):
            dynamic_strip.append(re.escape(title.strip()))
            for fragment in title.split():
                if len(fragment) > 8:
                    dynamic_strip.append(r'^' + re.escape(fragment) + r'$')
        if authors and authors not in ("N/A", ""):
            for author in authors.split('|'):
                author = author.strip()
                if author:
                    dynamic_strip.append(re.escape(author))
        all_boilerplate = BOILERPLATE_PATTERNS + dynamic_strip

        sorted_items = sorted(section_start_pages.items(), key=lambda x: x[1])

        for i, (section_key, start_pg) in enumerate(sorted_items):

            # End page = page before next section, capped at last_valid_page
            end_pg = last_valid_page
            next_section_pg = last_valid_page + 1  # default: no next section
            for j in range(i + 1, len(sorted_items)):
                next_pg = sorted_items[j][1]
                if next_pg != start_pg:
                    end_pg = min(next_pg - 1, last_valid_page)
                    next_section_pg = next_pg
                    break

            # For Introduction: stop at the first Chapter I sub-section heading
            # (Background of the Study, SOP, etc.) so it doesn't bleed into
            # all 25 pages of Chapter I.
            if section_key == "introduction":
                end_pg = _find_intro_end_page(
                    page_text_map,
                    intro_start=start_pg,
                    next_section_start=next_section_pg,
                )

            section_page_nums = [p for p in all_pages if start_pg <= p <= end_pg]

            raw_content = ""
            for idx_pg, pg in enumerate(section_page_nums):
                page_text = _normalize_text(page_text_map.get(pg, ""))
                # Only strip header material from the FIRST page of the section —
                # subsequent pages won't have the cover/title block.
                if idx_pg == 0:
                    page_text = _strip_page_header(page_text, title=title, authors=authors)
                raw_content += page_text + "\n\n"

            cleaned_lines = []
            for line in raw_content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                if any(re.search(bp, line, re.IGNORECASE) for bp in all_boilerplate):
                    continue
                if re.fullmatch(r'[\divxIVX]+', line):
                    continue
                cleaned_lines.append(line)

            final_content = " ".join(cleaned_lines)

            if len(final_content) >= MIN_SECTION_CHARS:
                result_sections[section_key] = final_content[:MAX_SECTION_CHARS]
                result_pages[section_key]    = section_page_nums
                print(f"[IMRAD] '{section_key}' → pages {section_page_nums}, "
                      f"{len(final_content)} chars")

        # ── 4. Build preview structures ───────────────────────────────────────
        # result_pages      = full page range per section → used for embedding
        # preview_pages     = flat sorted list of thumbnail page numbers
        # preview_sec_pages = section_pages capped to PREVIEW_PAGES_PER_SECTION
        #                     → sent to frontend so badges only appear on the
        #                       heading page(s), not on Background/SOP/etc.
        preview_sec_pages: Dict[str, List[int]] = {
            key: pages_list[:PREVIEW_PAGES_PER_SECTION]
            for key, pages_list in result_pages.items()
        }

        preview_pages: List[int] = sorted(set(
            pg
            for pages_list in preview_sec_pages.values()
            for pg in pages_list
        ))

        print(f"[IMRAD] Preview pages for frontend: {preview_pages}")

        return {
            "sections":      result_sections,
            "section_pages": preview_sec_pages,  # capped — frontend badges only
            "full_section_pages": result_pages,  # full range — for internal use
            "imrad_pages":   preview_pages,
        }

    # ─────────────────────────────────────────────────────────────────────────

    def detect_subheadings(
        self,
        page_text_map: Dict[int, str],
        methods_pages: List[int],
    ) -> List[str]:
        """Detect Methodology sub-headings using only the methods section pages."""
        if not methods_pages:
            print("[IMRAD][sub] No methods pages supplied — skipping.")
            return []

        search_text = ""
        for pg in sorted(methods_pages):
            search_text += _normalize_text(page_text_map.get(pg, "")) + "\n\n"

        print(f"[IMRAD][sub] Scanning {len(search_text)} chars across "
              f"{len(methods_pages)} methods pages.")

        detected: List[str] = []
        for entry in METHODOLOGY_SUBHEADINGS:
            for pat in entry["patterns"]:
                if re.search(r"\b" + pat + r"\b", search_text, re.IGNORECASE):
                    detected.append(entry["label"])
                    print(f"[IMRAD][sub] Found: {entry['label']}")
                    break

        return detected

    # ─────────────────────────────────────────────────────────────────────────

    def get_all_subheading_labels(self) -> List[str]:
        return [entry["label"] for entry in METHODOLOGY_SUBHEADINGS]

    def get_all_vector_names(self) -> List[str]:
        names = ["title"]
        if INCLUDE_ABSTRACT_VECTOR:
            names.append("abstract")
        names.extend(IMRAD_SECTION_KEYS)
        return names

    def get_qdrant_vector_config(self):
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
        abstract: str = "",
    ) -> Dict[str, List[float]]:
        from app.services.embedding_service import embedding_service

        vectors: Dict[str, List[float]] = {}

        if title and title.strip():
            vectors["title"] = embedding_service.get_embedding(title[:512])

        if INCLUDE_ABSTRACT_VECTOR and abstract and abstract.strip():
            vectors["abstract"] = embedding_service.get_embedding(abstract[:4000])

        for section_key, content in sections.items():
            if (
                section_key in IMRAD_SECTION_KEYS
                and content
                and len(content.strip()) >= MIN_SECTION_CHARS
            ):
                vectors[section_key] = embedding_service.get_embedding(content)

        print(f"[IMRAD] Built vectors for: {list(vectors.keys())}")
        return vectors


# Singleton instance
imrad_service = IMRADService()