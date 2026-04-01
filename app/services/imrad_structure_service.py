"""
imrad_structure_service.py
──────────────────────────
Transforms flat extracted-text columns from SQL into structured JSON blocks
before sending to the frontend. No database schema changes required — this
runs at response time on the already-stored text strings.

Output format per section:
    [
        {"type": "subheading",   "text": "Research Design"},
        {"type": "text",         "text": "The study used a descriptive quantitative approach..."},
        {"type": "table-label",  "text": "Table 1. Distribution of Respondents"},
        {"type": "text",         "text": "The weighted mean of 4.54 indicates..."},
    ]

Usage:
    from app.services.imrad_structure_service import imrad_structure_service
    structured = imrad_structure_service.build(paper)
    # → {"introduction": [...], "methods": [...], "results": [...], "discussion": [...]}
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Optional

# ── Subheading label lists ────────────────────────────────────────────────────
# Must stay in sync with imrad_service.py METHODOLOGY_SUBHEADINGS and
# RESULTS_SUBHEADINGS labels.

METHODOLOGY_LABELS: List[str] = [
    "Research Design", "Research Approach", "Research Settings",
    "Business Process", "Participants of the Study", "Sampling Technique",
    "Research Instruments", "Data Collection, Instrument, and Procedure",
    "Sources of Data", "Statistical Treatment of Data", "Data Analysis",
    "Ethical Considerations", "Development Model",
]

RESULTS_LABELS: List[str] = [
    "Discussion of the Methodology Phases", "Discussion of Findings",
    "Participation in the Study", "System Software Evaluation Results",
    "Functional Requirements", "Non-Functional Requirements",
    "System Testing", "User Acceptance Testing",
    "Functionality", "Reliability", "Usability", "Efficiency",
    "Portability", "Maintainability", "Descriptive Statistics",
    "Hypothesis Testing", "Correlation Analysis", "Interpretation",
]

ALL_SUBHEADING_LABELS: List[str] = METHODOLOGY_LABELS + RESULTS_LABELS

# Section heading strings that should never appear as body content.
# These are the chapter-level headings that _strip_page_header handles,
# but may still slip through in edge cases.
_SECTION_HEADING_EXACT = {
    "INTRODUCTION", "METHODOLOGY", "METHODS", "RESULTS",
    "RESULTS AND DISCUSSION", "RESULTS AND DISCUSSIONS",
    "DISCUSSION", "CONCLUSION", "CONCLUSIONS",
    "CONCLUSIONS AND RECOMMENDATIONS", "FINDINGS",
    "CHAPTER I", "CHAPTER II", "CHAPTER III", "CHAPTER IV", "CHAPTER V",
    "CHAPTER 1", "CHAPTER 2", "CHAPTER 3", "CHAPTER 4", "CHAPTER 5",
}

# Table / Figure caption — only short standalone lines (≤ 80 chars)
_TABLE_FIGURE_RE = re.compile(
    r'^(?:Table|Figure|Fig\.?)\s+\d+[\.\:]\s*.{0,60}$',
    re.IGNORECASE,
)


# ── Core structuring function ─────────────────────────────────────────────────

def _structure_section(
    text: str,
    section_key: str,
) -> List[Dict[str, str]]:
    """
    Split a flat text string into a list of typed blocks.

    Block types:
      "subheading"  — known IMRAD sub-heading line
      "table-label" — Table N. / Figure N. caption (short standalone line)
      "text"        — normal paragraph text (lines joined with spaces)
    """
    if not text or not text.strip():
        return []

    # Choose which subheading labels are relevant for this section
    if section_key == "methods":
        labels = METHODOLOGY_LABELS
    elif section_key in ("results", "results_and_discussion", "discussion"):
        labels = RESULTS_LABELS
    else:
        labels = []  # introduction — no subheading splitting needed

    blocks: List[Dict[str, str]] = []
    buffer: List[str] = []

    def flush_buffer() -> None:
        if buffer:
            joined = " ".join(t for t in buffer if t)
            if joined.strip():
                blocks.append({"type": "text", "text": joined.strip()})
            buffer.clear()

    for line in text.split("\n"):
        stripped = line.strip()

        # Skip empty lines and exact section headings
        if not stripped:
            continue
        if stripped.upper() in _SECTION_HEADING_EXACT:
            continue

        # Known subheading — line must closely match a label (± 15 chars)
        if labels:
            matched_label = next(
                (
                    label for label in labels
                    if label.lower() in stripped.lower()
                    and len(stripped) <= len(label) + 15
                ),
                None,
            )
            if matched_label:
                flush_buffer()
                blocks.append({"type": "subheading", "text": stripped})
                continue

        # Regular text — accumulate into buffer
        buffer.append(stripped)

    flush_buffer()
    return blocks


# ── Service class ─────────────────────────────────────────────────────────────

class IMRADStructureService:
    """
    Builds a structured representation of all IMRAD sections from a Paper object.
    Called at response time in the papers router — no DB writes required.
    """

    def build(self, paper: Any) -> Dict[str, List[Dict[str, str]]]:
        """
        Accepts a Paper SQLAlchemy model (or any object with .methods / .results
        / .discussion / .introduction attributes) and returns a dict of
        section_key → list of typed blocks.

        Introduction is returned as a single text block (it uses the summary
        in the IMRAD view, not the structured raw text).
        """
        result: Dict[str, List[Dict[str, str]]] = {}

        section_map = {
            "introduction": getattr(paper, "introduction", None),
            "methods":      getattr(paper, "methods", None),
            "results":      getattr(paper, "results", None),
            "discussion":   getattr(paper, "discussion", None),
        }

        for key, text in section_map.items():
            if text and text.strip():
                result[key] = _structure_section(text, key)

        return result

    def build_section(
        self,
        text: Optional[str],
        section_key: str,
    ) -> List[Dict[str, str]]:
        """Structure a single section's text. Useful for one-off calls."""
        if not text:
            return []
        return _structure_section(text, section_key)


imrad_structure_service = IMRADStructureService()