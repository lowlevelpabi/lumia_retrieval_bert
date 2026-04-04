"""
imrad_service.py
────────────────
IMRAD section detection, text extraction, and media placement.

Uses a single-source spatial extraction via PyMuPDF: text blocks are read
with their Y-coordinates and sorted top→bottom so that table/figure images
are placed at exactly the position they occupy in the original PDF.
"""

import re
import base64
from typing import Dict, List, Optional, Union, Any, Tuple
from difflib import SequenceMatcher
from app.services.logging_service import log

# ─────────────────────────────────────────────────────────────────────────────
# IMRAD Configuration
# ─────────────────────────────────────────────────────────────────────────────

INCLUDE_ABSTRACT_VECTOR: bool = True
IMRAD_SECTION_KEYS: List[str] = ["introduction", "methods", "results", "discussion"]

MAX_SECTION_CHARS: int  = 20000
MIN_SECTION_CHARS: int  = 100
PREVIEW_PAGES_PER_SECTION: int = 3

FUZZY_THRESHOLD: float        = 0.60
EARLY_ACCEPT_THRESHOLD: float = 0.88
FIRST_CANDIDATE_MIN_SCORE: float = 0.80
MIN_HEADING_CHARS: int = 6

HEADING_KEYWORDS: Dict[str, List[str]] = {
    "introduction": [
        "INTRODUCTION", "I. INTRODUCTION", "1. INTRODUCTION",
        "CHAPTER I", "CHAPTER 1", "CHAPTER ONE", "I.",
        "THE PROBLEM AND ITS BACKGROUND",
        "THE PROBLEM AND ITS SETTING",
        "PROBLEM AND ITS BACKGROUND",
        "BACKGROUND OF THE STUDY",
        "INTRODUCTION AND BACKGROUND",
    ],
    "methods": [
        "METHODOLOGY", "METHODS", "RESEARCH METHODOLOGY",
        "MATERIALS AND METHODS", "III. METHODOLOGY", "3. METHODOLOGY",
        "CHAPTER III", "CHAPTER 3", "CHAPTER THREE", "III.",
        "RESEARCH DESIGN AND METHODOLOGY",
        "RESEARCH METHOD", "METHOD OF RESEARCH",
        "METHODS AND PROCEDURES", "RESEARCH PROCEDURES",
        "DESIGN AND METHODOLOGY",
    ],
    "results": [
        "RESULTS", "FINDINGS", "IV. RESULTS", "4. RESULTS",
        "CHAPTER IV", "CHAPTER 4", "CHAPTER FOUR", "IV.",
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
        "PRESENTATION, ANALYSIS AND INTERPRETATION OF DATA",
        "ANALYSIS AND INTERPRETATION OF DATA",
    ],
    "discussion": [
        "CONCLUSION", "CONCLUSIONS", "CONCLUSIONS AND RECOMMENDATIONS",
        "CONCLUSION AND RECOMMENDATION",
        "SUMMARY CONCLUSIONS AND RECOMMENDATIONS",
        "V. CONCLUSION", "5. CONCLUSION",
        "CHAPTER V", "CHAPTER 5", "CHAPTER FIVE", "V.",
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
    "REVIEW OF RELATED LITERATURE AND STUDIES", "REVIEW OF LITERATURE",
    "CHAPTER II", "CHAPTER 2", "CHAPTER TWO", "II.",
    "PROJECT CONTEXT", "CONTEXT OF THE STUDY", "CONTEXT OF THE PROJECT",
    "PURPOSE OF THE STUDY", "PURPOSE OF THE PROJECT",
    "RELATED WORKS", "RELATED WORK",
]

BACK_MATTER_PAGE_PATTERNS: List[str] = [
    r"\bREFERENCES\b", r"\bBIBLIOGRAPHY\b", r"\bACKNOWLEDGMENTS?\b",
    r"\bAPPENDI(?:X|CES)\b", r"\bANNEX\b",
    r"\bCURRICULUM\s+VITAE\b", r"\bABOUT\s+THE\s+AUTHOR\b",
]

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
]

RRL_BOUNDARY_PATTERNS: List[str] = [
    r"^\s*(?:[IVXLC]+|\d+)[\.]?\s*Review\s+of\s+(?:Related\s+)?Literature\b",
    r"^\s*Review\s+of\s+(?:Related\s+)?Literature\b",
    r"^\s*Related\s+(?:Works?|Literature|Studies)\b",
]

MAX_INTRO_PAGES: int = 15

SKIP_PAGE_PATTERNS: List[str] = [
    r"\.{4,}",
    r"\bTable\s+of\s+Contents\b",
    r"\bList\s+of\s+(?:Tables|Figures|Appendices)\b",
    r"\bAppendi(?:x|ces)\b",
    r"\bBibliography\b",
]

METHODOLOGY_SUBHEADINGS: List[Dict] = [
    {"label": "Research Design",              "patterns": [r"Research\s+(?:Approach\s+(?:and\s+)?)?Design", r"Research\s+Design"]},
    {"label": "Research Approach",            "patterns": [r"Research\s+Approach(?:\s+and\s+Design)?"]},
    {"label": "Research Settings",            "patterns": [r"Research\s+Settings?"]},
    {"label": "Business Process",             "patterns": [r"Business\s+Process"]},
    {"label": "Participants of the Study",    "patterns": [r"Participants?\s+of\s+the\s+Study", r"Participants?", r"Respondents?"]},
    {"label": "Sampling Technique",           "patterns": [r"Sampling\s+Technique"]},
    {"label": "Research Instruments",         "patterns": [r"Research\s+Instruments?"]},
    {"label": "Data Collection, Instrument, and Procedure", "patterns": [r"Data\s+Collection,?\s+Instrument,?\s+and\s+Procedure", r"Data\s+Collection"]},
    {"label": "Sources of Data",              "patterns": [r"Sources?\s+of\s+Data", r"Data\s+to\s+be\s+[Gg]athered"]},
    {"label": "Statistical Treatment of Data","patterns": [r"Statistical\s+Treatment\s+of\s+Data", r"Statistical\s+Treatment"]},
    {"label": "Data Analysis",                "patterns": [r"Data\s+Analy(?:sis|tical)"]},
    {"label": "Ethical Considerations",       "patterns": [r"Ethical\s+Considerations?"]},
    {"label": "Development Model",            "patterns": [r"Development\s+Model"]},
    {"label": "Requirement Analysis",         "patterns": [r"Requirement\s+Analysis"]},
    {"label": "System Development",           "patterns": [r"System\s+Development"]},
    {"label": "System Evaluation",            "patterns": [r"System\s+Evaluation"]},
]

RESULTS_SUBHEADINGS: List[Dict] = [
    {"label": "Discussion of the Methodology Phases", "patterns": [r"Discussion\s+of\s+(?:the\s+)?Methodology\s+Phases?"]},
    {"label": "Discussion of Findings",       "patterns": [r"Discussion\s+of\s+(?:the\s+)?(?:Findings?|Results?)"]},
    {"label": "System Software Evaluation Results", "patterns": [r"System\s+(?:Software\s+)?Evaluation\s+Results?"]},
    {"label": "Functionality",                "patterns": [r"^Functionality$"]},
    {"label": "Reliability",                  "patterns": [r"^Reliability$"]},
    {"label": "Usability",                    "patterns": [r"^Usability$"]},
    {"label": "Efficiency",                   "patterns": [r"^Efficiency$"]},
    {"label": "Portability",                  "patterns": [r"^Portability$"]},
    {"label": "Maintainability",              "patterns": [r"^Maintainability$"]},
    {"label": "User Acceptance Testing",      "patterns": [r"User\s+Acceptance\s+(?:Testing|Test)", r"\bUAT\b"]},
    {"label": "System Testing",              "patterns": [r"System\s+Testing"]},
]

BOILERPLATE_PATTERNS: List[str] = [
    r"Cavite State University", r"CvSU", r"Imus Campus",
    r"Bachelor of Science", r"in partial fulfillment",
    r"requirements for the degree", r"Undergraduate Thesis",
    r"^\s*\d+\s*$", r"^\s*[ivxIVX]+\s*$",
]

_SECTION_HEADING_LINES: set = {
    kw.upper() for kws in HEADING_KEYWORDS.values() for kw in kws
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_text(text: str) -> str:
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'-\n\s*', '', text)
    text = re.sub(r'\b([A-Z]{3,})\s([A-Z]{1,2})\b', lambda m: m.group(1) + m.group(2), text)
    text = re.sub(r'[^\S\n]+', ' ', text)
    return text


def _strip_page_header(text: str, title: str = "", authors: str = "") -> str:
    ALL_HEADINGS = sorted(
        [kw for kws in HEADING_KEYWORDS.values() for kw in kws],
        key=len, reverse=True,
    )
    upper = text.upper()
    ep, el = -1, 0
    for h in ALL_HEADINGS:
        pos = upper.find(h.upper())
        if pos != -1 and (ep == -1 or pos < ep):
            ep, el = pos, len(h)
    if ep != -1:
        ls = text.rfind('\n', 0, ep) + 1
        le = text.find('\n', ep + el)
        if le == -1: le = len(text)
        ml = text[ls:le].strip()
        if len(ml) <= 80 and (el / max(len(ml), 1)) >= 0.50:
            return text[le:].strip()
    return text.strip()


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
    return True


def _is_skip_page(text: str) -> bool:
    for pat in SKIP_PAGE_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def _is_back_matter_page(text: str) -> bool:
    top = _normalize_text(text)[:300]
    for pat in BACK_MATTER_PAGE_PATTERNS:
        if re.search(pat, top, re.IGNORECASE):
            return True
    return False


def _find_back_matter_start(page_text_map: Dict[int, str], after_page: int) -> Optional[int]:
    for pg in sorted(page_text_map.keys()):
        if pg >= after_page and _is_back_matter_page(page_text_map[pg]):
            return pg
    return None


def _find_intro_end_page(page_text_map: Dict[int, str], intro_start: int, next_section_start: int) -> int:
    return min(intro_start + MAX_INTRO_PAGES, next_section_start - 1)


# ─────────────────────────────────────────────────────────────────────────────
# Core scorer
# ─────────────────────────────────────────────────────────────────────────────

def _find_section_page(
    section_key: str,
    page_text_map: Dict[int, str],
    min_page: int = 1,
) -> Optional[int]:
    from app.services.ml_service import classify_heading

    keywords = HEADING_KEYWORDS.get(section_key, [])
    if not keywords:
        return None

    nominees: list = []
    for page_num in sorted(page_text_map.keys()):
        if page_num < min_page:
            continue
        normalized = _normalize_text(page_text_map[page_num])
        if _is_skip_page(normalized):
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
            fp_score = max((_fuzzy_score(clean, fp) for fp in FALSE_POSITIVE_KEYWORDS), default=0.0)
            penalised = target_score
            if fp_score >= target_score:
                penalised = target_score * 0.25
            elif fp_score >= FUZZY_THRESHOLD:
                penalised = target_score * 0.55
            if penalised >= FUZZY_THRESHOLD:
                nominees.append((page_num, clean, penalised))

    if not nominees:
        return None

    nominees.sort(key=lambda x: x[2], reverse=True)
    for page_num, clean, regex_score in nominees:
        ml_section, ml_score = classify_heading(clean)
        if ml_section == section_key:
            return page_num
        if ml_section is None and ml_score == 0.0 and regex_score >= 0.85:
            return page_num
        if regex_score >= 0.95:
            return page_num

    if nominees[0][2] >= 0.92:
        return nominees[0][0]
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Spatial Media Extraction (Single-source PyMuPDF)
# ─────────────────────────────────────────────────────────────────────────────

def _extract_page_spatially(
    pdf_path: str,
    page_num_1based: int,
    result_media: Dict[str, str],
    section_key: str,
    all_boilerplate: List[str],
    subheading_list: List[Dict],
) -> Optional[List[str]]:
    """
    ONLY extracts table/figure images from a page and returns a list of
    [[TABLE_IMAGE:ID]] / [[FIGURE_IMAGE:ID]] marker strings.

    Returns None if PyMuPDF is unavailable or no captions are found.
    Returns an empty list [] if PyMuPDF works but this page has no tables/figures.

    The caller is ALWAYS responsible for text extraction via pypdf.
    This function no longer returns any paragraph text — it only injects markers.
    """
    try:
        import fitz
    except ImportError:
        return None

    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return None

    pg_idx = page_num_1based - 1
    if pg_idx >= len(doc):
        doc.close()
        return None

    page = doc.load_page(pg_idx)
    page_rect = page.rect

    # ── Step 1: Get all text blocks with coordinates ──────────────────────
    # Use "dict" mode to get per-line spans with accurate Y coordinates.
    # This prevents the caption's y0 from being set to the top of a merged
    # block that includes intro paragraph text above the actual caption line.
    text_blocks = []
    try:
        page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:  # 0 = text block
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                line_text = " ".join(s["text"] for s in spans).strip()
                if not line_text:
                    continue
                # Use the line's own bbox for accurate Y positioning
                bbox = line.get("bbox", None)
                if bbox is None:
                    continue
                text_blocks.append({
                    "y0": bbox[1], "y1": bbox[3],
                    "x0": bbox[0], "x1": bbox[2],
                    "text": line_text,
                })
    except Exception:
        # Fallback to blocks mode if dict mode fails
        raw_blocks = page.get_text("blocks")
        for b in raw_blocks:
            if b[6] != 0:
                continue
            text = b[4].strip()
            if not text:
                continue
            text = re.sub(r'\s*\n\s*', ' ', text).strip()
            text_blocks.append({
                "y0": b[1], "y1": b[3],
                "x0": b[0], "x1": b[2],
                "text": text,
            })

    # ── Step 2: Identify true captions ───────────────────────────────────
    CAP_RE = re.compile(r'(Table|Figure|Fig\.?)\s+\d+', re.I)
    # True captions have punctuation after the number: "Table 6. Title..." or "Table 6, Title..."
    # Inline refs do not: "Table 6 below shows..."
    # Note: some authors mistakenly use a comma instead of a period, e.g. "Table 3,"
    TRUE_CAP_RE = re.compile(r'^(Table|Figure|Fig\.?)\s+\d+[\.\:\-\,]', re.I)

    captions = []
    for tb in text_blocks:
        m = CAP_RE.search(tb["text"])
        if not m:
            continue
        start_pos = m.start()
        block_text = tb["text"]
        text_before = block_text[:start_pos].strip()
        is_short_prefix = len(text_before) <= 10
        candidate = block_text[start_pos:]
        is_titled_cap = bool(TRUE_CAP_RE.match(candidate))
        # A bare label is a very short standalone line like "Table 6" with no title yet
        # Must start with Table/Figure to avoid matching continuation lines like "respondents"
        is_bare_label = (len(block_text.strip()) < 80 and start_pos < 5
                         and bool(re.match(r'^(Table|Figure|Fig\.?)\s+\d+', block_text.strip(), re.I)))

        if not (is_short_prefix and (is_titled_cap or is_bare_label)):
            continue  # Inline body reference — skip

        tb["cap_start"] = start_pos
        tb["is_table"] = block_text.upper().find("TABLE", start_pos) != -1
        captions.append(tb)

    if not captions:
        doc.close()
        return None  # No tables/figures on this page

    # ── Step 3: Gather structural data for the entire page ─────────────

    # 3a. Run PyMuPDF table finder ONCE and cache all table bboxes.
    try:
        table_structs = page.find_tables()
        table_bboxes = [fitz.Rect(t.bbox) for t in table_structs.tables]
    except Exception:
        table_bboxes = []

    # 3b. Build a sorted list of horizontal drawing rules on the page.
    # Academic PDF tables almost always have explicit horizontal border lines.
    # Each entry is the Y midpoint of a rule that is wide (>40px) and thin (<6px).
    h_rules: List[float] = []
    try:
        for path in page.get_drawings():
            r = path.get("rect")
            if r is None:
                continue
            width  = abs(r[2] - r[0])
            height = abs(r[3] - r[1])
            if width > 40 and height < 6:
                h_rules.append((r[1] + r[3]) / 2)
        h_rules.sort()
    except Exception:
        h_rules = []

    TABLE_LABEL_RE = re.compile(r'^(Table|Figure|Fig\.?)\s+\d+', re.I)

    def _is_body_paragraph(txt: str) -> bool:
        """True only when a text line is clearly body prose (not a table row/header)."""
        if not txt or len(txt) <= 80:
            return False
        if txt == txt.upper():  # ALL CAPS → table header
            return False
        if TABLE_LABEL_RE.match(txt):  # starts with Table/Figure N
            return False
        return True

    # Sort text blocks top-to-bottom once — reused throughout
    text_blocks_sorted = sorted(text_blocks, key=lambda b: b["y0"])

    # markers: list of (caption_text_normalized, marker_string)
    markers = []  # list of (normalized_caption_text, marker_string)

    for cap_block in captions:
        cap_y0  = cap_block["y0"]
        cap_y1  = cap_block["y1"]
        is_table = cap_block.get("is_table", False)

        # Default zone: start at caption top, extend generously downward.
        zone_y0 = cap_y0 - 5
        zone_y1 = cap_y0 + 500  # generous fallback

        if is_table:
            # ── Strategy A: PyMuPDF structural table detection ─────────────
            # If find_tables() found a table whose top is within 300px
            # below the caption, use its exact bbox as the clip region.
            # This is the highest-fidelity strategy — trust it completely.
            matched_tbox = None
            for tbox in table_bboxes:
                # Table top should be at/below the caption (not above by >30px)
                # and within 300px below the caption line.
                if tbox.y0 >= cap_y0 - 30 and (tbox.y0 - cap_y0) < 300:
                    matched_tbox = tbox
                    break

            if matched_tbox is not None:
                # Reverted: Anchor at caption top to include full description/label.
                # min() handles cases where the caption might be slightly below tbox.y0.
                zone_y0 = min(cap_y0, matched_tbox.y0) - 10
                zone_y1 = matched_tbox.y1 + 8
                # Safety trim: stop before the first clearly-body paragraph AFTER the table.
                for tb in text_blocks_sorted:
                    if tb["y0"] <= matched_tbox.y1 + 5:
                        continue
                    txt = tb["text"].strip()
                    if bool(TRUE_CAP_RE.match(txt)) or _is_body_paragraph(txt):
                        zone_y1 = min(zone_y1, tb["y0"] - 5)
                    break  # Only check the FIRST block after the table

            else:
                # ── Strategy B: Horizontal drawing rule detection ───────────
                # Academic tables have printed horizontal border lines (rules).
                # Walk the rules below the caption forward until body text breaks in.
                rules_below = [y for y in h_rules if y > cap_y1]

                if len(rules_below) >= 2:
                    table_bottom = rules_below[0]
                    for ry in rules_below:
                        # Stop extending if body paragraph appears before this rule
                        body_breaks = False
                        for tb in text_blocks_sorted:
                            if tb["y0"] <= table_bottom + 5:
                                continue
                            if tb["y0"] > ry + 5:
                                break
                            if _is_body_paragraph(tb["text"].strip()):
                                body_breaks = True
                                break
                        if body_breaks:
                            break
                        table_bottom = ry
                    # Reverted: Anchor at caption top
                    zone_y0 = cap_y0 - 10
                    zone_y1 = table_bottom + 15

                else:
                    # ── Strategy C: Conservative heuristic fallback ─────────
                    # Require >80 chars (not >60) to avoid tripping on table
                    # headers / footers / short caption continuation lines.
                    for tb in text_blocks_sorted:
                        if tb["y0"] <= cap_y1 + 5:
                            continue
                        txt = tb["text"].strip()
                        if bool(TRUE_CAP_RE.match(txt)) or _is_body_paragraph(txt):
                            if tb["y0"] - 5 < zone_y1:
                                zone_y1 = tb["y0"] - 5
                            break

        else:
            # Figure: find the embedded image object near the caption
            images = page.get_image_info()
            for img in images:
                ib = fitz.Rect(img["bbox"])
                if abs(ib.y0 - cap_y0) < 400 or abs(ib.y1 - cap_y0) < 400:
                    zone_y0 = min(cap_y0, ib.y0) - 10
                    zone_y1 = max(cap_y0 + 20, ib.y1) + 10
                    break
            # Tighten for figures — stop at body paragraph below
            for tb in text_blocks_sorted:
                if tb["y0"] <= cap_y0 + 20:
                    continue
                txt = tb["text"].strip()
                if bool(TRUE_CAP_RE.match(txt)) or _is_body_paragraph(txt):
                    if tb["y0"] - 5 < zone_y1:
                        zone_y1 = tb["y0"] - 5
                    break

        # Minimum height guard — never clip less than 100px
        if (zone_y1 - zone_y0) < 100:
            zone_y1 = zone_y0 + 100

        zone_y0 = max(0, zone_y0)
        zone_y1 = min(page_rect.height, zone_y1)

        clip = fitz.Rect(
            max(0, page_rect.x0 + 25),
            zone_y0,
            min(page_rect.width, page_rect.x1 - 25),
            zone_y1,
        )

        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat, clip=clip)
        b64_img = base64.b64encode(pix.tobytes("jpeg")).decode('utf-8')

        prefix = "T" if is_table else "F"
        mid = f"{prefix}_{page_num_1based}_{len(result_media)}"
        result_media[mid] = f"data:image/jpeg;base64,{b64_img}"

        tag = "TABLE" if is_table else "FIGURE"
        marker = f"[[{tag}_IMAGE:{mid}]]"

        # Normalize the caption text so the caller can match it in the pypdf stream
        cap_text_norm = re.sub(r'\s+', ' ', cap_block["text"][cap_block["cap_start"]:]).strip()
        markers.append((cap_text_norm, marker))

    doc.close()

    # Return the markers — caller injects them into the pypdf text stream
    return [m for _, m in markers], {cap: mark for cap, mark in markers}



# ─────────────────────────────────────────────────────────────────────────────
# IMRAD Summary Helpers
# ─────────────────────────────────────────────────────────────────────────────

def build_imrad_summary_prompt(section_key: str, content: str) -> str:
    ct = content[:8000]
    if section_key == "introduction":
        return f"""You are summarising the Introduction section of a Filipino undergraduate thesis for display in a 2-column IMRAD layout.

Instructions:
- Identify each sub-section present in the text.
- For each sub-section, write a concise summary in 2–4 sentences.
- Use clear headings for each sub-section.
- Keep the total summary under 400 words.
- Write in plain academic prose. No bullet lists.

Introduction text:
---
{ct}
---

Respond with the structured summary only. No preamble."""

    elif section_key == "methods":
        return f"""You are summarising the Methodology section of a Filipino undergraduate thesis.

Instructions:
- Identify all sub-headings present in the text.
- For each sub-heading, write a concise 2–3 sentence summary.
- Keep the total summary under 450 words.

Methodology text:
---
{ct}
---

Respond with the structured summary only. No preamble."""

    elif section_key == "results":
        return f"""You are summarising the Results/Findings section of a Filipino undergraduate thesis.

Instructions:
- Write a concise 3–5 sentence paragraph summarising the key findings.
- Keep the summary under 200 words.

Results text:
---
{ct}
---

Respond with the summary paragraph only. No preamble."""

    elif section_key == "discussion":
        return f"""You are summarising the Conclusions and Recommendations section of a Filipino undergraduate thesis.

Instructions:
- Write a concise 3–5 sentence paragraph covering the main conclusions and recommendations.
- Keep the summary under 200 words.

Conclusions text:
---
{ct}
---

Respond with the summary paragraph only. No preamble."""

    return f"Summarise the following academic text in 3–5 sentences:\n\n{ct}"


# ─────────────────────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────────────────────

class IMRADService:

    def extract_sections(
        self,
        page_input: Union[str, Dict[int, str]],
        title: str = "",
        authors: str = "",
        pdf_path: str = "",
    ) -> Dict[str, Any]:
        """
        Extract Introduction, Methodology, Results, and Discussion sections.

        Uses single-source PyMuPDF spatial extraction for pages containing
        tables/figures, ensuring images are placed at their exact PDF position.
        Falls back to pypdf text for pages without media.
        """
        if not page_input:
            return {"sections": {}, "section_pages": {}, "imrad_pages": []}

        page_text_map = {1: page_input} if isinstance(page_input, str) else dict(page_input)
        all_pages = sorted(page_text_map.keys())

        # ── 1. Locate section start pages ────────────────────────────────
        combined_page = _find_section_page("results_and_discussion", page_text_map, min_page=1)
        section_start_pages: Dict[str, int] = {}
        min_p = 1

        for key in IMRAD_SECTION_KEYS:
            if combined_page is not None and key in ("results", "discussion"):
                if combined_page >= min_p:
                    section_start_pages[key] = combined_page
                continue
            pg = _find_section_page(key, page_text_map, min_page=min_p)
            if pg is not None:
                section_start_pages[key] = pg
                min_p = pg + 1

        if not section_start_pages:
            log.warn("No IMRAD sections detected")
            return {"sections": {}, "section_pages": {}, "imrad_pages": []}

        log.info("Section start pages", pages=str(section_start_pages))

        # ── 2. Back-matter boundary ──────────────────────────────────────
        first_imrad = min(section_start_pages.values())
        back_matter = _find_back_matter_start(page_text_map, after_page=first_imrad + 1)
        last_valid = (back_matter - 1) if back_matter else all_pages[-1]

        # ── 3. Extract text per section ──────────────────────────────────
        result_sections: Dict[str, str] = {}
        result_pages: Dict[str, List[int]] = {}
        result_media: Dict[str, str] = {}

        # Build boilerplate regex list
        dynamic_strip: List[str] = []
        if title and title not in ("N/A", ""):
            dynamic_strip.append(re.escape(title.strip()))
            for frag in title.split():
                if len(frag) > 8:
                    dynamic_strip.append(r'^' + re.escape(frag) + r'$')
        if authors and authors not in ("N/A", ""):
            for a in authors.split('|'):
                if a.strip():
                    dynamic_strip.append(re.escape(a.strip()))
        all_boilerplate = BOILERPLATE_PATTERNS + dynamic_strip

        sorted_items = sorted(section_start_pages.items(), key=lambda x: x[1])

        for i, (section_key, start_pg) in enumerate(sorted_items):
            # Calculate section end page
            end_pg = last_valid
            next_section_pg = last_valid + 1
            for j in range(i + 1, len(sorted_items)):
                if sorted_items[j][1] != start_pg:
                    end_pg = min(sorted_items[j][1] - 1, last_valid)
                    next_section_pg = sorted_items[j][1]
                    break

            if section_key == "introduction":
                end_pg = _find_intro_end_page(page_text_map, start_pg, next_section_pg)

            section_page_nums = [p for p in all_pages if start_pg <= p <= end_pg]

            # Choose subheading list for this section
            if section_key == "methods":
                sh_list = METHODOLOGY_SUBHEADINGS
            elif section_key in ("results", "results_and_discussion", "discussion"):
                sh_list = RESULTS_SUBHEADINGS
            else:
                sh_list = []

            cleaned_lines: List[str] = []
            section_stop = False
            # Also accept comma: some authors write "Table 3," instead of "Table 3."
            TRUE_CAP_RE = re.compile(r'^(Table|Figure|Fig\.?)\s+\d+[\.\:\-\,]', re.I)

            for idx_pg, pg in enumerate(section_page_nums):
                if section_stop:
                    break

                # ── Get image markers for this page (PyMuPDF, images only) ──
                # Returns a dict of {caption_text: marker_string} or None if
                # PyMuPDF unavailable. Text is ALWAYS taken from pypdf below.
                page_markers: Dict[str, str] = {}
                if pdf_path and section_key in ("methods", "results", "discussion"):
                    spatial_result = _extract_page_spatially(
                        pdf_path, pg, result_media, section_key,
                        all_boilerplate, sh_list,
                    )
                    if spatial_result is not None:
                        _, page_markers = spatial_result

                # ── Always extract text from pypdf ────────────────────────
                page_text = _normalize_text(page_text_map.get(pg, ""))

                pg_lines: List[str] = []
                for line in page_text.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    if any(re.search(bp, line, re.I) for bp in all_boilerplate):
                        continue
                    if re.fullmatch(r'[\divxIVX]+', line):
                        continue
                    if line.upper() in _SECTION_HEADING_LINES:
                        continue

                    # Section boundaries
                    if section_key == "introduction":
                        if any(re.search(pat, line, re.I) for pat in RRL_BOUNDARY_PATTERNS + INTRO_SUBSECTION_PATTERNS):
                            section_stop = True
                            break
                    if section_key in ("results", "results_and_discussion"):
                        if any(re.search(pat, line, re.I) for pat in RAD_STOP_PATTERNS_STRICT):
                            section_stop = True
                            break
                        stop = False
                        for pat in RAD_STOP_PATTERNS_FLEX:
                            m = re.search(pat, line, re.I)
                            if m and not (len(line) > 100 and m.group() != m.group().upper()):
                                tb = line[:m.start()].strip()
                                if tb and len(tb) > 3:
                                    pg_lines.append(tb)
                                stop = True
                                break
                        if stop:
                            section_stop = True
                            break

                    # Subheading detection
                    is_sh = False
                    for entry in sh_list:
                        if re.search(r"\b" + entry["patterns"][0] + r"\b", line, re.I):
                            pg_lines.append("\n" + line.strip() + "\n")
                            is_sh = True
                            break
                    if is_sh:
                        continue

                    # ── Inject image marker after matching caption line ────
                    # A caption line in pypdf text looks like "Table 6. General rating..."
                    # We match it against the markers extracted by PyMuPDF and inject
                    # the marker immediately after, then skip the caption line itself
                    # (the image screenshot already includes the caption visually).
                    if page_markers and TRUE_CAP_RE.match(line):
                        line_norm = re.sub(r'\s+', ' ', line).strip()
                        matched_marker = None
                        for cap_text, marker in page_markers.items():
                            cap_norm = re.sub(r'\s+', ' ', cap_text).strip()
                            # Match if the pypdf line starts with the same Table/Figure N. prefix
                            if line_norm[:40].lower().startswith(cap_norm[:40].lower()):
                                matched_marker = marker
                                break
                            # Fuzzy fallback: both start with same "Table N" token
                            # Strip any trailing punctuation (. : - ,) before comparing
                            line_prefix = re.match(r'((?:Table|Figure|Fig\.?)\s+\d+)', line_norm, re.I)
                            cap_prefix  = re.match(r'((?:Table|Figure|Fig\.?)\s+\d+)', cap_norm,  re.I)
                            if line_prefix and cap_prefix and line_prefix.group(1).lower() == cap_prefix.group(1).lower():
                                matched_marker = marker
                                break
                        if matched_marker:
                            pg_lines.append(f"\n{matched_marker}\n")
                            continue  # Skip the raw caption text — it's inside the image

                    pg_lines.append(line)

                cleaned_lines.extend(pg_lines)

            # ── Join lines intelligently ─────────────────────────────────
            # Lines ending with \n are subheadings/placeholders → own line
            # Other lines are paragraph text → join with spaces
            parts: List[str] = []
            buffer: List[str] = []
            for ln in cleaned_lines:
                if ln.startswith("\n") or ln.endswith("\n"):
                    if buffer:
                        parts.append(" ".join(buffer))
                        buffer = []
                    parts.append(ln.strip())
                else:
                    buffer.append(ln)
            if buffer:
                parts.append(" ".join(buffer))

            final_content = "\n".join(parts)
            final_content = re.sub(r'\n{3,}', '\n\n', final_content).strip()

            if len(final_content) >= MIN_SECTION_CHARS:
                result_sections[section_key] = final_content[:MAX_SECTION_CHARS]
                result_pages[section_key] = section_page_nums
                log.info(f"Section '{section_key}' extracted",
                         pages=str(section_page_nums), chars=len(final_content))

        # ── 4. Build preview structures ──────────────────────────────────
        preview_sec_pages = {
            k: v[:PREVIEW_PAGES_PER_SECTION] for k, v in result_pages.items()
        }
        preview_pages = sorted(set(
            pg for pages in preview_sec_pages.values() for pg in pages
        ))

        return {
            "sections":           result_sections,
            "section_pages":      preview_sec_pages,
            "full_section_pages": result_pages,
            "imrad_pages":        preview_pages,
            "media":              result_media,
        }

    # ─────────────────────────────────────────────────────────────────────

    def detect_subheadings(
        self,
        page_text_map: Dict[int, str],
        methods_pages: List[int],
        results_pages: List[int] = None,
    ) -> List[str]:
        detected: List[str] = []
        if methods_pages:
            m_text = "\n".join(_normalize_text(page_text_map.get(pg, "")) for pg in sorted(methods_pages))
            for entry in METHODOLOGY_SUBHEADINGS:
                for pat in entry["patterns"]:
                    if re.search(r"\b" + pat + r"\b", m_text, re.IGNORECASE):
                        detected.append(entry["label"])
                        break
        if results_pages:
            r_text = "\n".join(_normalize_text(page_text_map.get(pg, "")) for pg in sorted(results_pages))
            for entry in RESULTS_SUBHEADINGS:
                if entry["label"] not in detected:
                    for pat in entry["patterns"]:
                        if re.search(r"\b" + pat + r"\b", r_text, re.IGNORECASE):
                            detected.append(entry["label"])
                            break
        return detected

    def get_all_subheading_labels(self) -> List[str]:
        return list(dict.fromkeys(
            [e["label"] for e in METHODOLOGY_SUBHEADINGS] +
            [e["label"] for e in RESULTS_SUBHEADINGS]
        ))

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
        for key, content in sections.items():
            if key in IMRAD_SECTION_KEYS and content and len(content.strip()) >= MIN_SECTION_CHARS:
                vectors[key] = embedding_service.get_embedding(content)
        log.ml("Vectors built", keys=str(list(vectors.keys())))
        return vectors

    def get_summary_prompts(self, sections: Dict[str, str]) -> Dict[str, str]:
        prompts: Dict[str, str] = {}
        for key in IMRAD_SECTION_KEYS:
            content = sections.get(key, "")
            if content and len(content.strip()) >= MIN_SECTION_CHARS:
                prompts[key] = build_imrad_summary_prompt(key, content)
        return prompts


# Singleton instance
imrad_service = IMRADService()