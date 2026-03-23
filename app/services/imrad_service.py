import re
from typing import Dict, List, Optional, Union
from difflib import SequenceMatcher

# ─────────────────────────────────────────────────────────────────────────────
# IMRAD Configuration
# ─────────────────────────────────────────────────────────────────────────────

INCLUDE_ABSTRACT_VECTOR: bool = True
IMRAD_SECTION_KEYS: List[str] = ["introduction", "methods", "results", "discussion"]

# Raised MAX_SECTION_CHARS to allow multi-page Introduction sections.-
# 20000 chars ≈ ~3 dense pages; adjust higher if needed.
MAX_SECTION_CHARS: int  = 20000
MIN_SECTION_CHARS: int  = 100

# Number of pages shown in the frontend preview per section.
PREVIEW_PAGES_PER_SECTION: int = 3

FUZZY_THRESHOLD: float        = 0.60
EARLY_ACCEPT_THRESHOLD: float = 0.88
FIRST_CANDIDATE_MIN_SCORE: float = 0.80
MIN_HEADING_CHARS: int = 6

HEADING_KEYWORDS: Dict[str, List[str]] = {
    "introduction": [
        # Current format
        "INTRODUCTION", "I. INTRODUCTION", "1. INTRODUCTION",
        # Legacy chapter-only headings
        "CHAPTER I", "CHAPTER 1", "CHAPTER ONE",
        # Legacy numbered headings (standalone on a line)
        "I.",
        # Legacy section labels
        "THE PROBLEM AND ITS BACKGROUND",
        "THE PROBLEM AND ITS SETTING",
        "PROBLEM AND ITS BACKGROUND",
        "BACKGROUND OF THE STUDY",
        "INTRODUCTION AND BACKGROUND",
    ],
    "methods": [
        # Current format
        "METHODOLOGY", "METHODS", "RESEARCH METHODOLOGY",
        "MATERIALS AND METHODS", "III. METHODOLOGY", "3. METHODOLOGY",
        # Legacy chapter-only headings
        "CHAPTER III", "CHAPTER 3", "CHAPTER THREE",
        # Legacy numbered headings
        "III.",
        # Legacy section labels
        "RESEARCH DESIGN AND METHODOLOGY",
        "RESEARCH METHOD",
        "METHOD OF RESEARCH",
        "METHODS AND PROCEDURES",
        "RESEARCH PROCEDURES",
        "DESIGN AND METHODOLOGY",
    ],
    "results": [
        # Current format
        "RESULTS", "FINDINGS", "IV. RESULTS", "4. RESULTS",
        # Legacy chapter-only headings
        "CHAPTER IV", "CHAPTER 4", "CHAPTER FOUR",
        # Legacy numbered headings
        "IV.",
        # Legacy section labels
        "PRESENTATION OF DATA",
        "PRESENTATION AND ANALYSIS OF DATA",
        "ANALYSIS AND INTERPRETATION",
        "DATA PRESENTATION",
        "ANALYSIS AND DISCUSSION OF RESULTS",
        "PRESENTATION, ANALYSIS AND INTERPRETATION",
        "DATA ANALYSIS AND INTERPRETATION",
    ],
    "results_and_discussion": [
        "RESULTS AND DISCUSSION", "RESULTS AND DISCUSSIONS",
        "CHAPTER IV RESULTS AND DISCUSSION",
        "IV. RESULTS AND DISCUSSION", "4. RESULTS AND DISCUSSION",
        # Legacy combined labels
        "PRESENTATION, ANALYSIS AND INTERPRETATION OF DATA",
        "ANALYSIS AND INTERPRETATION OF DATA",
    ],
    "discussion": [
        # Current format
        "CONCLUSION", "CONCLUSIONS", "CONCLUSIONS AND RECOMMENDATIONS",
        "CONCLUSION AND RECOMMENDATION",
        "SUMMARY CONCLUSIONS AND RECOMMENDATIONS",
        "V. CONCLUSION", "5. CONCLUSION",
        # Legacy chapter-only headings
        "CHAPTER V", "CHAPTER 5", "CHAPTER FIVE",
        # Legacy numbered headings
        "V.",
        # Legacy section labels
        "SUMMARY, CONCLUSIONS AND RECOMMENDATIONS",
        "SUMMARY AND CONCLUSIONS",
        "SUMMARY, FINDINGS, CONCLUSIONS AND RECOMMENDATIONS",
        "SUMMARY OF FINDINGS",
        "IMPLICATIONS AND RECOMMENDATIONS",
        "SUMMARY AND RECOMMENDATION",
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
    "RESEARCH GAP",
    "CRITERIA", "RUBRIC", "EVALUATION", "RATING", "SCORE", "SUITABILITY",
    "REVIEW OF RELATED LITERATURE AND STUDIES",
    "REVIEW OF LITERATURE",
    "CHAPTER II", "CHAPTER 2", "CHAPTER TWO", "II.",
    "PROJECT CONTEXT", "CONTEXT OF THE STUDY", "CONTEXT OF THE PROJECT",
    "PURPOSE OF THE STUDY", "PURPOSE OF THE PROJECT",
    "RELATED WORKS", "RELATED WORK",
]

BACK_MATTER_PAGE_PATTERNS: List[str] = [
    r"\bREFERENCES\b",
    r"\bBIBLIOGRAPHY\b",
    r"\bACKNOWLEDGMENTS?\b",
    r"\bAPPENDI(?:X|CES)\b",
    r"\bANNEX\b",
    r"\bCURRICULUM\s+VITAE\b",
    r"\bABOUT\s+THE\s+AUTHOR\b",
]

INTRO_SUBSECTION_PATTERNS: List[str] = [
    r"^\s*Background\s+of\s+the\s+Study\b",
    r"^\s*Statement\s+of\s+the\s+Problem\b",
    r"^\s*Research\s+(?:Objectives?|Questions?)\b",
    r"^\s*Objectives?\s+of\s+the\s+Study\b",
    r"^\s*Significance\s+of\s+the\s+Study\b",
    r"^\s*Scope\s+and\s+(?:Delimitation|Limitation)\b",
    r"^\s*Definition\s+of\s+Terms\b",
    r"^\s*Conceptual\s+Framework\b",
    r"^\s*Theoretical\s+Framework\b",
    r"^\s*Review\s+of\s+(?:Related\s+)?Literature\b",
    r"^\s*Hypothes[ie]s\b",
    # Legacy sub-section starts that clearly open a new section page
    r"^\s*Scope\s+and\s+Delimitation\b",
    r"^\s*Research\s+Locale\b",
    # Project context / related works sub-sections
    r"^\s*Project\s+Context\b",
    r"^\s*Context\s+of\s+the\s+(?:Study|Project)\b",
    r"^\s*Purpose\s+of\s+the\s+(?:Study|Project)\b",
    r"^\s*Related\s+(?:Works?|Studies|Literature)\b",
]

MAX_INTRO_PAGES: int = 3

# TOC / rubric page skip patterns
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

# Methodology sub-heading checklist
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
    r"Adviser\s*:",
    r"^\s*Department of [A-Za-z\s]+$",
    r"^\s*College of [A-Za-z\s]+$",
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
    """
    ALL_SECTION_HEADINGS = sorted(
        [kw for kws in HEADING_KEYWORDS.values() for kw in kws]
        + ["INTRODUCTION", "METHODOLOGY", "METHODS", "RESULTS", "DISCUSSION",
           "CONCLUSION", "FINDINGS"],
        key=len, reverse=True
    )

    upper_text = text.upper()

    earliest_pos = -1
    earliest_len = 0
    for heading in ALL_SECTION_HEADINGS:
        pos = upper_text.find(heading.upper())
        if pos != -1 and (earliest_pos == -1 or pos < earliest_pos):
            earliest_pos = pos
            earliest_len = len(heading)

    if earliest_pos != -1:
        result = text[earliest_pos + earliest_len:].strip()
        print(f"[IMRAD][strip] Cut header at pos {earliest_pos}, "
              f"heading='{text[earliest_pos:earliest_pos+earliest_len]}', "
              f"body starts: {repr(result[:60])}")
        return result

    print("[IMRAD][strip] No heading anchor found — falling back to phrase stripping")
    result = text

    if title and title not in ("N/A", ""):
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
    True when the first 300 characters of a page contain a back-matter heading.
    """
    top = _normalize_text(text)[:300]
    for pat in BACK_MATTER_PAGE_PATTERNS:
        if re.search(pat, top, re.IGNORECASE):
            return True
    return False


def _find_back_matter_start(page_text_map: Dict[int, str], after_page: int) -> Optional[int]:
    """
    Return the first page number (at or after `after_page`) whose top content
    matches a back-matter heading.
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
    updated behaviour:
    1. Only stop when a sub-section heading appears in the FIRST 150 chars of a
       page (i.e., it IS the page heading, not just mentioned in body text).
    2. Also enforce MAX_INTRO_PAGES as a hard cap so intros never bleed too far.
    3. Start scanning from intro_start + 1 as before.
    """
    hard_cap = min(intro_start + MAX_INTRO_PAGES, next_section_start - 1)

    for pg in range(intro_start + 1, next_section_start):
        if pg > hard_cap:
            print(f"[IMRAD] Introduction capped at page {hard_cap} "
                  f"(MAX_INTRO_PAGES={MAX_INTRO_PAGES})")
            return hard_cap

        text = page_text_map.get(pg, "")
        # Check only the very top of the page (first 150 chars) for a standalone
        # sub-section heading. This avoids false-cuts when body text mentions
        # "Background of the Study" in passing.
        top = _normalize_text(text)[:150]
        if any(re.search(pat, top, re.IGNORECASE | re.MULTILINE) for pat in INTRO_SUBSECTION_PATTERNS):
            print(f"[IMRAD] Introduction ends at page {pg - 1} "
                  f"(sub-section heading detected at top of page {pg})")
            return pg - 1

    return hard_cap


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
# IMRAD Summary Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_intro_subsections(text: str) -> Dict[str, str]:
    """
    Extract named sub-sections from Introduction body text.
    Returns a dict keyed by sub-section label (e.g. 'background', 'objectives').
    Used by the AI summariser to give context-aware prompts per sub-section.
    """
    INTRO_LABELS = {
        "background":   [r"Background\s+of\s+the\s+Study", r"Introduction\s+Background"],
        "objectives":   [r"Objectives?\s+of\s+the\s+Study", r"Research\s+Objectives?",
                         r"Aims?\s+(?:and\s+Objectives?|of\s+the\s+Study)"],
        "problem":      [r"Statement\s+of\s+the\s+Problem", r"Research\s+(?:Questions?|Problem)"],
        "significance": [r"Significance\s+of\s+the\s+Study"],
        "scope":        [r"Scope\s+and\s+(?:Delimitation|Limitation)"],
    }
    splits: Dict[str, int] = {}
    for key, patterns in INTRO_LABELS.items():
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                splits[key] = m.start()
                break

    if not splits:
        return {"full": text}

    order = sorted(splits.items(), key=lambda x: x[1])
    result: Dict[str, str] = {}
    for idx, (key, start) in enumerate(order):
        end = order[idx + 1][1] if idx + 1 < len(order) else len(text)
        result[key] = text[start:end].strip()

    return result

'''
def build_imrad_summary_prompt(section_key: str, content: str) -> str:

    # Truncate to 8000 chars (well within Claude's context) for efficiency
    content_truncated = content[:8000]

    if section_key == "introduction":
        return f"""You are summarising the Introduction section of a Filipino undergraduate thesis for display in a 2-column IMRAD layout on an academic repository website.

The Introduction may contain multiple sub-sections such as: Background of the Study, Statement of the Problem, Research Objectives, Significance of the Study, Scope and Delimitation, etc.

Instructions:
- Identify each sub-section present in the text.
- For each sub-section, write a concise summary in 2–4 sentences.
- Use clear headings for each sub-section (e.g., "Background of the Study", "Objectives", "Statement of the Problem").
- Keep the total summary under 400 words.
- Write in plain academic prose. No bullet lists.
- Do not include content from outside the Introduction.

Introduction text:
---
{content_truncated}
---

Respond with the structured summary only. No preamble."""

    elif section_key == "methods":
        return f"""You are summarising the Methodology section of a Filipino undergraduate thesis for a 2-column IMRAD display on an academic repository website.

The Methodology section may contain sub-headings such as: Research Design, Research Setting, Participants/Respondents, Research Instruments, Data Collection, Data Analysis, Ethical Considerations, Development Model, etc.

Instructions:
- Identify all sub-headings present in the text.
- For each sub-heading, write a concise 2–3 sentence summary.
- Use the original sub-heading as the label.
- Keep the total summary under 450 words.
- Write in plain academic prose.

Methodology text:
---
{content_truncated}
---

Respond with the structured summary only. No preamble."""

    elif section_key == "results":
        return f"""You are summarising the Results/Findings section of a Filipino undergraduate thesis for a 2-column IMRAD display on an academic repository website.

Instructions:
- Write a concise 3–5 sentence paragraph summarising the key findings.
- Mention the most significant results or data points.
- Do not include methodology details or recommendations.
- Keep the summary under 200 words.
- Write in plain academic prose.

Results text:
---
{content_truncated}
---

Respond with the summary paragraph only. No preamble."""

    elif section_key == "discussion":
        return f"""You are summarising the Conclusions and Recommendations section of a Filipino undergraduate thesis for a 2-column IMRAD display on an academic repository website.

Instructions:
- Write a concise 3–5 sentence paragraph covering: the main conclusions and any recommendations.
- If both conclusions and recommendations are present, address each briefly.
- Keep the summary under 200 words.
- Write in plain academic prose.

Conclusions/Discussion text:
---
{content_truncated}
---

Respond with the summary paragraph only. No preamble."""

    else:
        return f"Summarise the following academic text in 3–5 sentences:\n\n{content_truncated}"
'''

# ─────────────────────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────────────────────

class IMRADService:

    def extract_sections(self, page_input: Union[str, Dict[int, str]], title: str = "", authors: str = "") -> Dict[str, any]:
        """
        Detect IMRAD section headings and extract content per section.

        Returns:
            {
              'sections':           {section_key: full_text},
              'section_pages':      {section_key: [preview page numbers]},
              'full_section_pages': {section_key: [all page numbers]},
              'imrad_pages':        sorted flat list of preview pages only
            }
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

            end_pg = last_valid_page
            next_section_pg = last_valid_page + 1
            for j in range(i + 1, len(sorted_items)):
                next_pg = sorted_items[j][1]
                if next_pg != start_pg:
                    end_pg = min(next_pg - 1, last_valid_page)
                    next_section_pg = next_pg
                    break

            # FIX #3: Use revised _find_intro_end_page with MAX_INTRO_PAGES cap
            if section_key == "introduction":
                end_pg = _find_intro_end_page(
                    page_text_map,
                    intro_start=start_pg,
                    next_section_start=next_section_pg,
                )

            section_page_nums = [p for p in all_pages if start_pg <= p <= end_pg]

            # Build per-page cleaned text so we can prune pages after inline trim
            page_cleaned_chars: List[int] = []  # cumulative char count after each page
            cleaned_lines = []
            running_chars = 0
            for idx_pg, pg in enumerate(section_page_nums):
                page_text = _normalize_text(page_text_map.get(pg, ""))
                if idx_pg == 0:
                    page_text = _strip_page_header(page_text, title=title, authors=authors)
                pg_lines = []
                for line in page_text.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    if any(re.search(bp, line, re.IGNORECASE) for bp in all_boilerplate):
                        continue
                    if re.fullmatch(r'[\divxIVX]+', line):
                        continue
                    pg_lines.append(line)
                if pg_lines:
                    pg_text_joined = " ".join(pg_lines)
                    if cleaned_lines:
                        running_chars += 1  # space separator between pages
                    cleaned_lines.extend(pg_lines)
                    running_chars += len(pg_text_joined)
                page_cleaned_chars.append(running_chars)

            final_content = " ".join(cleaned_lines)

            # ── Inline intro truncation ───────────────────────────────────────
            # Page-level detection only fires when a heading is at the TOP of a
            # new page. When sub-section labels appear mid-paragraph (e.g. OCR
            # runs them inline), cut at the first heading that follows a sentence
            # boundary — not on phrases that appear naturally mid-sentence.
            if section_key == "introduction":
                INTRO_INLINE_CUT = [
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Background\s+of\s+the\s+Study\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Project\s+Context\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Context\s+of\s+the\s+(?:Study|Project)\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Purpose\s+of\s+the\s+(?:Study|Project)\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Statement\s+of\s+the\s+Problem\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Objectives?\s+of\s+the\s+Study\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Research\s+Objectives?\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Significance\s+of\s+the\s+Study\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Scope\s+and\s+(?:Delimitation|Limitation)\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Definition\s+of\s+Terms\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Conceptual\s+Framework\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Theoretical\s+Framework\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Review\s+of\s+(?:Related\s+)?Literature\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Related\s+(?:Works?|Studies)\s+(?:and\s+Literature\s+)?(?:show|discuss|suggest|indicate|reveal|demonstrate|present|provide|highlight|support|confirm|include)\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Hypothes[ie]s\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Research\s+Locale\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Research\s+Questions?\b",
                ]
                cut_pos = len(final_content)
                for pat in INTRO_INLINE_CUT:
                    m = re.search(pat, final_content, re.IGNORECASE | re.MULTILINE)
                    if m:
                        heading_start = next(
                            (ci for ci in range(m.start(), m.end()) if final_content[ci].isalpha()),
                            m.start(),
                        )
                        if heading_start < cut_pos:
                            cut_pos = heading_start
                if cut_pos < len(final_content):
                    trimmed = final_content[:cut_pos].rstrip(" .,;")
                    print(f"[IMRAD] Introduction inline-trimmed at pos {cut_pos} "
                          f"('{final_content[cut_pos:cut_pos+40].strip()}')")
                    final_content = trimmed
                    # Prune section_page_nums to only pages whose content
                    # falls within the kept portion of text.
                    kept_pages = []
                    prev = 0
                    for pi, pg in enumerate(section_page_nums):
                        page_end = page_cleaned_chars[pi] if pi < len(page_cleaned_chars) else len(final_content)
                        if prev < cut_pos:
                            kept_pages.append(pg)
                        prev = page_end
                    if kept_pages:
                        section_page_nums = kept_pages
                        print(f"[IMRAD] Introduction pages pruned to {section_page_nums} after inline trim")

            if len(final_content) >= MIN_SECTION_CHARS:
                # FIX #1: Store full content (up to MAX_SECTION_CHARS = 20000)
                result_sections[section_key] = final_content[:MAX_SECTION_CHARS]
                result_pages[section_key]    = section_page_nums
                print(f"[IMRAD] '{section_key}' → pages {section_page_nums}, "
                      f"{len(final_content)} chars (stored {min(len(final_content), MAX_SECTION_CHARS)})")

        # ── 4. Build preview structures ───────────────────────────────────────
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
            "sections":           result_sections,
            "section_pages":      preview_sec_pages,
            "full_section_pages": result_pages,
            "imrad_pages":        preview_pages,
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

    def get_summary_prompts(self, sections: Dict[str, str]) -> Dict[str, str]:
        """
        FIX #4: Returns a dict of {section_key: prompt_string} for each available
        section. These prompts are ready to send to Claude API to generate
        shortened summaries for the 2-column IMRAD view.

        Usage (in your router or background task):
            prompts = imrad_service.get_summary_prompts(paper.sections)
            for key, prompt in prompts.items():
                summary = await call_claude_api(prompt)
                paper.imrad_summaries[key] = summary
        """
        prompts: Dict[str, str] = {}
        for key in IMRAD_SECTION_KEYS:
            content = sections.get(key, "")
            if content and len(content.strip()) >= MIN_SECTION_CHARS:
                prompts[key] = build_imrad_summary_prompt(key, content)
        return prompts


# Singleton instance
imrad_service = IMRADService()