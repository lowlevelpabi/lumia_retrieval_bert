import re
from typing import Dict, List, Optional, Union
from difflib import SequenceMatcher
from app.services.logging_service import log

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

# Patterns that signal the start of a Conclusions/Chapter V section.
# We use two tiers to balance detection vs false-positives:
# 1. STRICT: Must be standalone or at the start of a line (short markers).
# 2. FLEXIBLE: Can match anywhere in a line (long, unique phrases).
RAD_STOP_PATTERNS_STRICT: List[str] = [
    r"^\s*(?:CHAPTER\s+(?:V|5|FIVE))\s*$",
    r"^\s*V\.\s*$",
    r"^\s*RECOMMENDATIONS?\s*$",
    r"^\s*CONCLUSIONS?\s*$",
]

RAD_STOP_PATTERNS_FLEX: List[str] = [
    r"\bSUMMARY\W*CONCLUSIONS?\W*AND\W*RECOMMENDATIONS?\b",
    r"\bSUMMARY\s+AND\s+CONCLUSIONS?\b",
    r"\bCONCLUSIONS?\s+AND\s+RECOMMENDATIONS?\b",
    r"\bCONCLUSION\s+AND\s+RECOMMENDATION\b",
    r"\bIMPLICATIONS?\s+AND\s+RECOMMENDATIONS?\b",
    r"\bSUMMARY\s+OF\s+FINDINGS\b",
    r"\bSUMMARY\W*FINDINGS\W*CONCLUSIONS?\W*AND\W*RECOMMENDATIONS?\b",
    r"\bSUMMARY\s+AND\s+RECOMMENDATION\b",
    r"\bSUMMARY\s+OF\s+THE\s+STUDY\b",
]

INTRO_SUBSECTION_PATTERNS: List[str] = [
    r"^\s*(?:[IVXLC]+|\d+)[\.\s]*Background\s+of\s+the\s+Study\b",
    r"^\s*(?:[IVXLC]+|\d+)[\.\s]*Statement\s+of\s+the\s+Problem\b",
    r"^\s*(?:[IVXLC]+|\d+)[\.\s]*Research\s+(?:Objectives?|Questions?)\b",
    r"^\s*(?:[IVXLC]+|\d+)[\.\s]*Objectives?\s+of\s+the\s+Study\b",
    r"^\s*(?:[IVXLC]+|\d+)[\.\s]*Significance\s+of\s+the\s+Study\b",
    r"^\s*(?:[IVXLC]+|\d+)[\.\s]*Scope\s+and\s+(?:Delimitation|Limitation)\b",
    r"^\s*(?:[IVXLC]+|\d+)[\.\s]*Definition\s+of\s+Terms\b",
    r"^\s*(?:[IVXLC]+|\d+)[\.\s]*Conceptual\s+Framework\b",
    r"^\s*(?:[IVXLC]+|\d+)[\.\s]*Theoretical\s+Framework\b",
    r"^\s*(?:[IVXLC]+|\d+)[\.\s]*Review\s+of\s+(?:Related\s+)?Literature\b",
    r"^\s*(?:[IVXLC]+|\d+)[\.\s]*Hypothes[ie]s\b",
    r"^\s*(?:[IVXLC]+|\d+)[\.\s]*Scope\s+and\s+Delimitation\b",
    r"^\s*(?:[IVXLC]+|\d+)[\.\s]*Research\s+Locale\b",
    r"^\s*(?:[IVXLC]+|\d+)[\.\s]*Project\s+Context\b",
    r"^\s*(?:[IVXLC]+|\d+)[\.\s]*Context\s+of\s+the\s+(?:Study|Project)\b",
    r"^\s*(?:[IVXLC]+|\d+)[\.\s]*Purpose\s+of\s+the\s+(?:Study|Project)\b",
    r"^\s*(?:[IVXLC]+|\d+)[\.\s]*Related\s+(?:Works?|Studies|Literature)\b",
    # Original patterns without numbers
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
    r"^\s*Scope\s+and\s+Delimitation\b",
    r"^\s*Research\s+Locale\b",
    r"^\s*Project\s+Context\b",
    r"^\s*Context\s+of\s+the\s+(?:Study|Project)\b",
    r"^\s*Purpose\s+of\s+the\s+(?:Study|Project)\b",
    r"^\s*Related\s+(?:Works?|Studies|Literature)\b",
]

# RRL boundary patterns — content from here onward belongs to Chapter II, not
# the Introduction. Captured as a module-level constant so _find_intro_end_page
# and the extraction loop can both reference it.
RRL_BOUNDARY_PATTERNS: List[str] = [
    r"^\s*(?:[IVXLC]+|\d+)[\.]?\s*Review\s+of\s+(?:Related\s+)?Literature\b",
    r"^\s*Review\s+of\s+(?:Related\s+)?Literature\b",
    r"^\s*(?:[IVXLC]+|\d+)[\.]?\s*Review\s+of\s+Related\s+(?:Literature|Studies)\b",
    r"^\s*Review\s+of\s+Related\s+(?:Literature|Studies)\b",
    r"^\s*Related\s+(?:Works?|Literature|Studies)\b",
    r"^\s*(?:[IVXLC]+|\d+)[\.]?\s*Related\s+(?:Works?|Literature|Studies)\b",
]

MAX_INTRO_PAGES: int = 15

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
    {"label": "Research Design",                            "patterns": [r"Research\s+(?:Approach\s+(?:and\s+)?)?Design",
                                                                         r"Research\s+Design"]},
    {"label": "Research Approach",                          "patterns": [r"Research\s+Approach(?:\s+and\s+Design)?"]},
    {"label": "Research Settings",                          "patterns": [r"Research\s+Settings?"]},
    {"label": "Business Process",                           "patterns": [r"Business\s+Process"]},
    {"label": "Participants of the Study",                  "patterns": [r"Participants?\s+of\s+the\s+Study",
                                                                         r"Participants?", r"Respondents?"]},
    {"label": "Sampling Technique",                         "patterns": [r"Stratified\s+Sampl(?:ing|e)",
                                                                         r"Sampling\s+Technique"]},
    {"label": "Research Instruments",                       "patterns": [r"Research\s+Instruments?"]},
    {"label": "Data Collection, Instrument, and Procedure", "patterns": [r"Data\s+Collection,?\s+Instrument,?\s+and\s+Procedure",
                                                                         r"Data\s+Collection"]},
    {"label": "Sources of Data",                            "patterns": [r"Sources?\s+of\s+Data",
                                                                         r"Data\s+to\s+be\s+[Gg]athered"]},
    {"label": "Statistical Treatment of Data",              "patterns": [r"Statistical\s+Treatment\s+of\s+Data",
                                                                         r"Statistical\s+Treatment"]},
    {"label": "Data Analysis",                              "patterns": [r"Data\s+Analy(?:sis|tical)(?:\s+Techni(?:que|cal)?)?",
                                                                         r"Data\s+Analysis"]},
    {"label": "Ethical Considerations",                     "patterns": [r"Ethical\s+Considerations?"]},
    {"label": "Development Model",                          "patterns": [r"Development\s+Model"]},
    # Capstone-specific additions (Methodology)
    {"label": "Design Software, System, Product and/or Process", "patterns": [r"Design\s+Software,?\s+System,?\s+Product\s+and/or\s+Process"]},
    {"label": "Requirement Analysis",                       "patterns": [r"Requirement\s+Analysis"]},
    {"label": "Requirement Documentation",                  "patterns": [r"Requirement\s+Documentation"]},
    {"label": "System Development",                         "patterns": [r"System\s+Development"]},
    {"label": "System Evaluation",                          "patterns": [r"System\s+Evaluation"]},
    {"label": "Data Analysis Plan",                         "patterns": [r"Data\s+Analysis\s+Plan"]},
    {"label": "Implementation Plan",                        "patterns": [r"Implementation\s+Plan"]},
]

# Results / Results-and-Discussion sub-heading checklist
RESULTS_SUBHEADINGS: List[Dict] = [
    {"label": "Discussion of the Methodology Phases",       "patterns": [r"Discussion\s+of\s+(?:the\s+)?Methodology\s+Phases?"]},
    {"label": "Discussion of Findings",                     "patterns": [r"Discussion\s+of\s+(?:the\s+)?(?:Findings?|Results?)"]},
    {"label": "Participation in the Study",                 "patterns": [r"Participation\s+in\s+the\s+Study"]},
    {"label": "System Software Evaluation Results",         "patterns": [r"System\s+(?:Software\s+)?Evaluation\s+Results?",
                                                                         r"Software\s+Evaluation\s+Results?"]},
    {"label": "Functional Requirements",                    "patterns": [r"Functional\s+Requirements?"]},
    {"label": "Non-Functional Requirements",                "patterns": [r"Non[-\s]Functional\s+Requirements?"]},
    {"label": "System Testing",                             "patterns": [r"System\s+Testing"]},
    {"label": "User Acceptance Testing",                    "patterns": [r"User\s+Acceptance\s+(?:Testing|Test)",
                                                                         r"\bUAT\b"]},
    {"label": "Functionality",                              "patterns": [r"^Functionality$"]},
    {"label": "Reliability",                                "patterns": [r"^Reliability$"]},
    {"label": "Usability",                                  "patterns": [r"^Usability$"]},
    {"label": "Efficiency",                                 "patterns": [r"^Efficiency$"]},
    {"label": "Portability",                                "patterns": [r"^Portability$"]},
    {"label": "Maintainability",                            "patterns": [r"^Maintainability$"]},
    {"label": "Descriptive Statistics",                     "patterns": [r"Descriptive\s+Statistics"]},
    {"label": "Hypothesis Testing",                         "patterns": [r"Hypothesis\s+Testing",
                                                                         r"Test\s+of\s+(?:Significant\s+)?Difference"]},
    {"label": "Correlation Analysis",                       "patterns": [r"Correlation\s+Analysis"]},
    {"label": "Interpretation",                             "patterns": [r"^Interpretation$",
                                                                         r"Interpretation\s+of\s+(?:Data|Results?)"]},
    # Capstone-specific additions (Results)
    {"label": "System Design",                              "patterns": [r"System\s+Design"]},
    {"label": "System Development",                         "patterns": [r"System\s+Development"]},
    {"label": "System Testing",                             "patterns": [r"System\s+Testing"]},
    {"label": "System Evaluation",                          "patterns": [r"System\s+Evaluation"]},
    {"label": "Implementation Results",                     "patterns": [r"Implementation\s+Results?"]},
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

# Flat set of all IMRAD section heading strings (uppercased).
# Used during line-by-line extraction to skip lines that ARE the section
# heading itself — prevents "METHODOLOGY", "RESULTS AND DISCUSSION" etc.
# from appearing as the first line of the body text.
_SECTION_HEADING_LINES: set = {
    kw.upper()
    for kws in HEADING_KEYWORDS.values()
    for kw in kws
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_text(text: str) -> str:
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Rejoin hyphenated line-breaks (e.g. "meth-\nodology" → "methodology")
    text = re.sub(r'-\n\s*', '', text)
    # Fix pypdf spacing artefacts: uppercase words split by a stray space
    # e.g. "METHODOLOG Y" → "METHODOLOGY", "DISCUSSIO N" → "DISCUSSION"
    # narrowed to 1-2 char segments to avoid joining "RESULTS AND" → "RESULTSAND"
    text = re.sub(r'\b([A-Z]{3,})\s([A-Z]{1,2})\b', lambda m: m.group(1) + m.group(2), text)
    # Collapse multiple spaces/tabs on a single line — preserve newlines
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
        # Guard: only treat the match as a heading anchor when it sits on its
        # own short line. If the keyword is found inside a long body sentence
        # (e.g. "...examination of the proposal methodology is presented...")
        # slicing from there drops the start of the paragraph. That happens
        # when _find_section_page detected the heading on the last line of the
        # previous page and start_pg therefore begins with body text.
        match_line_start = text.rfind('\n', 0, earliest_pos) + 1   # 0 if no prior \n
        match_line_end   = text.find('\n', earliest_pos + earliest_len)
        if match_line_end == -1:
            match_line_end = len(text)
        match_line = text[match_line_start:match_line_end].strip()

        heading_is_standalone = (
            len(match_line) <= 80
            and (earliest_len / max(len(match_line), 1)) >= 0.50
        )

        if heading_is_standalone:
            # Slice off the heading line; body starts on the very next line.
            result = text[match_line_end:].strip()
            log.regex("Header stripped (standalone heading)",
                      pos=earliest_pos,
                      heading=match_line,
                      body_start=repr(result[:50]))
            return result
        else:
            log.regex(
                "Heading anchor rejected — keyword inside body text, "
                "falling through to phrase-stripping fallback",
                match_line=repr(match_line[:60]),
            )
    # falls through to phrase-stripping fallback below

    log.regex("No heading anchor — using phrase stripping fallback")
    result = text

    if title and title not in ("N/A", ""):
        # re.escape turns spaces into '\ ' (escaped space). Replace each of
        # those with \s+ so the pattern flexibly matches any whitespace run.
        # Do NOT use re.sub(r"\s+", r"\s+", escaped) — that injects a raw
        # '\s+' string which Python 3.12+ rejects as a bad escape sequence.
        title_escaped    = re.escape(title.strip())
        title_normalized = re.sub(r'\\ ', r'\\s+', title_escaped)
        try:
            result = re.sub(title_normalized, " ", result[:800], flags=re.IGNORECASE) + result[800:]
        except re.error:
            result = result.replace(title.strip(), " ", 1)

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
    Returns the last page of the Introduction section.
    Uses next_section_start as the hard boundary (the IMRAD methods page),
    capped at MAX_INTRO_PAGES from the intro start so very long Chapter I
    sections don't consume the entire document.
    Sub-section headings (Background, Objectives, etc.) are intentionally
    included — they are part of Chapter I and should be captured.
    """
    hard_cap = min(intro_start + MAX_INTRO_PAGES, next_section_start - 1)
    if hard_cap < intro_start + MAX_INTRO_PAGES:
        pass  # capped by next section
    else:
        log.regex("Introduction capped at MAX_INTRO_PAGES", page=hard_cap, cap=MAX_INTRO_PAGES)
    return hard_cap


# ─────────────────────────────────────────────────────────────────────────────
# Core scorer
# ─────────────────────────────────────────────────────────────────────────────

def _find_section_page(
    section_key: str,
    page_text_map: Dict[int, str],
    min_page: int = 1,
) -> Optional[int]:
    """
    Two-phase heading detection:

    Phase 1 — Regex hunter
        Scans every line on every page using fuzzy keyword matching.
        Produces a shortlist of (page, line, score) nominees that cleared
        the fuzzy threshold. Does NOT make the final call.

    Phase 2 — NLI judge
        Receives every nominee from Phase 1 and classifies it semantically
        using the fine-tuned IMRAD model. Confirms or rejects each nominee.
        The first nominee the NLI agrees with becomes the section page.
        If NLI is unavailable, falls back to the highest-scoring regex nominee.
    """
    from app.services.ml_service import classify_heading

    keywords = HEADING_KEYWORDS.get(section_key, [])
    if not keywords:
        return None

    # ── Phase 1: Regex hunts for nominees ────────────────────────────────────
    log.subsection(f"Phase 1 · Regex hunting '{section_key}'  (min_page={min_page})")

    nominees: list = []   # [(page_num, clean_line, penalised_score)]

    for page_num in sorted(page_text_map.keys()):
        if page_num < min_page:
            continue

        raw_text   = page_text_map[page_num]
        normalized = _normalize_text(raw_text)

        if _is_skip_page(normalized):
            log.regex_skip(page_num, "TOC / appendix / rubric")
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

            log.regex_hit(page_num, clean, target_score, fp_score, penalised)
            nominees.append((page_num, clean, penalised))

    if not nominees:
        log.regex_not_found(section_key)
        return None

    log.regex(f"Nominated {len(nominees)} candidate(s) for NLI review",
              section=section_key)

    # ── Phase 2: ML Judging ──────────────────────────────────────────────────
    log.subsection(f"Phase 2 · ML Judging '{section_key}' nominees")

    best_fallback_page  : Optional[int] = nominees[0][0]
    best_fallback_score : float         = nominees[0][2]

    # Sort nominees by regex score to check most likely headings first
    nominees.sort(key=lambda x: x[2], reverse=True)

    for page_num, clean, regex_score in nominees:
        ml_section, ml_score = classify_heading(clean)

        # ── ML-First Logic ──
        # If Tier 0 ML confirms the section, we take it immediately.
        if ml_section == section_key:
            log.ml_classify(
                f"Verdict CONFIRMED — '{clean[:45]}'",
                ml_section, ml_score,
                tier=f"pg={page_num} (ML-First)",
            )
            return page_num

        # If ML is broken (None, 0.0), only then we follow fallback rules
        if ml_section is None and ml_score == 0.0:
            log.ml_warn("ML engine unavailable — using safety fallback",
                        page=page_num, line=f'"{clean[:40]}"')
            if best_fallback_score >= 0.85:
                return best_fallback_page
            continue

        # If ML definitively said 'junk' or wrong section, we REJECT it.
        # This is where the transition to Pure ML happens.
        if ml_section != section_key:
             log.ml_classify(
                f"Verdict REJECTED — '{clean[:45]}'",
                ml_section or "junk", ml_score,
                tier=f"pg={page_num} (ML-Decision)",
            )
             # If Regex is VERY sure (e.g. 0.98), we might consider it, 
             # but normally we trust the ML's rejection.
             if regex_score >= 0.95:
                 log.regex(f"Regex override applied for perfect match", page=page_num)
                 return page_num
             continue

    # Final logic: if all ML checks failed/rejected, but we found a perfect 
    # regex match earlier, use it as a last resort.
    if best_fallback_score >= 0.92:
        log.regex_accept(section_key, best_fallback_page,
                         best_fallback_score, reason="Perfect regex match (ML unsure)")
        return best_fallback_page

    log.warn(f"Section '{section_key}' not found by ML ranking.")
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
            log.warn("No IMRAD sections detected")
            return {"sections": {}, "section_pages": {}, "imrad_pages": []}

        log.regex("Section start pages resolved", pages=str(section_start_pages))

        # ── 2. Find the back-matter boundary ─────────────────────────────────
        first_imrad_page = min(section_start_pages.values())
        back_matter_start = _find_back_matter_start(
            page_text_map, after_page=first_imrad_page + 1
        )
        if back_matter_start:
            log.regex("Back-matter boundary detected", page=back_matter_start)
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
                _intro_rrl_hit = False   # set True once we reach the RRL boundary
                _rad_stop_hit  = False   # set True when summary/conclusion heading found in RAD
                for line in page_text.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    if any(re.search(bp, line, re.IGNORECASE) for bp in all_boilerplate):
                        continue
                    if re.fullmatch(r'[\divxIVX]+', line):
                        continue

                    # ── Skip the section heading line itself ──────────────────
                    # Prevents "METHODOLOGY", "RESULTS AND DISCUSSION" etc.
                    # from leaking into the body text as a first line.
                    if line.upper() in _SECTION_HEADING_LINES:
                        continue

                    # ── Introduction: stop at RRL boundary ───────────────────
                    if section_key == "introduction":
                        if any(re.search(pat, line, re.IGNORECASE)
                               for pat in RRL_BOUNDARY_PATTERNS):
                            _intro_rrl_hit = True
                            log.regex("Introduction: RRL boundary reached — "
                                      "stopping intro extraction",
                                      line=repr(line[:60]))
                            break

                    # ── Introduction: stop at first sub-heading ───────────────
                    if section_key == "introduction":
                        if any(re.search(pat, line, re.IGNORECASE)
                               for pat in INTRO_SUBSECTION_PATTERNS):
                            _intro_rrl_hit = True
                            log.regex(
                                "Introduction: sub-heading boundary reached — "
                                "stopping intro extraction",
                                line=repr(line[:60]),
                            )
                            break

                    # ── Results/RAD: stop at Summary/Conclusion heading ───────
                    # Prevents CHAPTER V content from being absorbed into the
                    # Results and Discussion section when both share the same
                    # page range (no separate chapter detected).
                    if section_key in ("results", "results_and_discussion"):
                        # Tier 1: Strict Check (standalone)
                        if any(re.search(pat, line, re.IGNORECASE)
                               for pat in RAD_STOP_PATTERNS_STRICT):
                            _rad_stop_hit = True
                            log.regex("Results/RAD: conclusion boundary reached (STRICT) — stopping",
                                      line=repr(line[:60]))
                            break
                        
                        # Tier 2: Flexible Check (can be inline, but must be uppercase or long)
                        # We only check FLEX if the line is not short to avoid false-positives
                        # like mid-sentence "summary" mentions.
                        for pat in RAD_STOP_PATTERNS_FLEX:
                            match = re.search(pat, line, re.IGNORECASE)
                            if match:
                                # Secondary guard: if it's long prose and the match is NOT uppercase,
                                # it's almost certainly body text, not a heading.
                                found_match = match.group()
                                if len(line) > 100 and found_match != found_match.upper():
                                    continue
                                
                                # FIX: Split the line at the start of the match.
                                # Keep the part before the match if it belongs to Results.
                                text_before = line[:match.start()].strip()
                                if text_before and len(text_before) > 3:
                                    pg_lines.append(text_before)
                                    log.regex("Results: kept text before inline heading", 
                                              text=repr(text_before[:60]))

                                _rad_stop_hit = True
                                log.regex("Results/RAD: conclusion boundary reached (FLEX) — stopping",
                                          line=repr(line[:60]))
                                break
                        if _rad_stop_hit:
                            break

                    # For methods AND results: insert a newline before each
                    # sub-heading so the frontend can distinguish sections cleanly.
                    is_section_subheading = False
                    if section_key == "methods":
                        is_section_subheading = any(
                            re.search(r"\b" + entry["patterns"][0] + r"\b", line, re.IGNORECASE)
                            for entry in METHODOLOGY_SUBHEADINGS
                        )
                    elif section_key in ("results", "results_and_discussion", "discussion"):
                        is_section_subheading = any(
                            re.search(r"\b" + entry["patterns"][0] + r"\b", line, re.IGNORECASE)
                            for entry in RESULTS_SUBHEADINGS
                        )

                    if is_section_subheading:
                        pg_lines.append("\n" + line.strip() + "\n")
                        continue

                    pg_lines.append(line)

                if pg_lines:
                    pg_text_joined = " ".join(pg_lines)
                    if cleaned_lines:
                        running_chars += 1
                    cleaned_lines.extend(pg_lines)
                    running_chars += len(pg_text_joined)
                page_cleaned_chars.append(running_chars)

                # Stop collecting pages once the RRL boundary was hit
                if section_key == "introduction" and _intro_rrl_hit:
                    log.regex("Introduction page collection halted at RRL boundary",
                              page=pg)
                    break

                # Stop collecting pages once summary/conclusion boundary hit in RAD
                if section_key in ("results", "results_and_discussion") and _rad_stop_hit:
                    log.regex("Results/RAD page collection halted at conclusion boundary",
                              page=pg)
                    break

            # Join lines intelligently:
            # - Lines ending with \n are subheadings → keep on their own line
            # - All other lines are paragraph text → join with space
            parts = []
            buffer: List[str] = []
            for ln in cleaned_lines:
                if ln.endswith("\n"):
                    if buffer:
                        parts.append(" ".join(buffer))
                        buffer = []
                    parts.append(ln.rstrip("\n"))
                else:
                    buffer.append(ln)
            if buffer:
                parts.append(" ".join(buffer))

            final_content = "\n".join(parts)
            final_content = re.sub(r'\n{3,}', '\n\n', final_content).strip()

            # Introduction extraction stops at the first sub-heading (Option A).
            # sections["introduction"] now contains only the pure opening narrative.
            # If the AI summariser needs sub-section content it should receive the
            # full page_text_map range directly, not sections["introduction"].

            if len(final_content) >= MIN_SECTION_CHARS:
                # FIX #1: Store full content (up to MAX_SECTION_CHARS = 20000)
                result_sections[section_key] = final_content[:MAX_SECTION_CHARS]
                result_pages[section_key]    = section_page_nums
                log.info(f"Section extracted — '{section_key}'",
                         pages=str(section_page_nums),
                         chars=f"{len(final_content)} → stored {min(len(final_content), MAX_SECTION_CHARS)}")

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

        log.info("Frontend preview pages", pages=str(preview_pages))

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
        results_pages: List[int] = None,
    ) -> List[str]:
        """Detect Methodology and Results sub-headings using section-specific pages."""
        detected: List[str] = []

        # 1. Methodology Scan
        if methods_pages:
            m_text = ""
            for pg in sorted(methods_pages):
                m_text += _normalize_text(page_text_map.get(pg, "")) + "\n\n"
            
            for entry in METHODOLOGY_SUBHEADINGS:
                for pat in entry["patterns"]:
                    if re.search(r"\b" + pat + r"\b", m_text, re.IGNORECASE):
                        detected.append(entry["label"])
                        break

        # 2. Results/Discussion Scan
        if results_pages:
            r_text = ""
            for pg in sorted(results_pages):
                r_text += _normalize_text(page_text_map.get(pg, "")) + "\n\n"
            
            for entry in RESULTS_SUBHEADINGS:
                # Avoid duplicate labels (some subheadings appear in both lists)
                if entry["label"] in detected:
                    continue
                for pat in entry["patterns"]:
                    if re.search(r"\b" + pat + r"\b", r_text, re.IGNORECASE):
                        detected.append(entry["label"])
                        break

        if detected:
            log.regex("Sub-headings detected", count=len(detected), labels=str(detected))
        
        return detected

    # ─────────────────────────────────────────────────────────────────────────

    def get_all_subheading_labels(self) -> List[str]:
        m_labels = [entry["label"] for entry in METHODOLOGY_SUBHEADINGS]
        r_labels = [entry["label"] for entry in RESULTS_SUBHEADINGS]
        # Return unique combined list
        return list(dict.fromkeys(m_labels + r_labels))

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

        log.ml("Vectors built", keys=str(list(vectors.keys())))
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