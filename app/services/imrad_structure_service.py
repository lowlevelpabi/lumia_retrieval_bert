"""
imrad_structure_service.py
──────────────────────────
Transforms flat extracted-text columns from SQL into structured JSON blocks
before sending to the frontend. No database schema changes required — this
runs at response time on the already-stored text strings.
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
    "Hypothesis Testing", "Correlation Analysis",
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

# Table / Figure caption — requires punctuation (. or :) after the number
# to distinguish true captions ("Table 6. General rating...") from inline
# paragraph references ("Table 6 below shows the interpretation of...").
_TABLE_FIGURE_RE = re.compile(
    r'^(?:Table|Figure|Fig\.?)\s+\d+[\.\:]\s*.{0,120}$',
    re.IGNORECASE,
)


# ── Core structuring function ─────────────────────────────────────────────────

def _structure_section(
    text: str,
    section_key: str,
    media: Optional[Dict[str, str]] = None,
    pages: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    """
    Split a flat text string into a list of typed blocks.
    
    Block types:
      "subheading"  — known IMRAD sub-heading line
      "table-label" — Table N. / Figure N. caption (short standalone line)
      "table-image" — base64 visual snippet from paper.media (emitted after label)
      "text"        — normal paragraph text (lines joined with spaces)
    """
    if not text or not text.strip():
        return []

    # Choose relevant subheading labels
    if section_key == "methods":
        labels = METHODOLOGY_LABELS
    elif section_key in ("results", "results_and_discussion", "discussion"):
        labels = RESULTS_LABELS
    else:
        labels = []

    blocks: List[Dict[str, Any]] = []
    buffer: List[str] = []
    pending_media: List[Dict[str, Any]] = []

    def flush_buffer() -> None:
        if buffer:
            joined = " ".join(t for t in buffer if t)
            if joined.strip():
                blocks.append({"type": "text", "text": joined.strip()})
            buffer.clear()

    def flush_pending_media() -> None:
        """Emit any queued images immediately at the current position in the stream."""
        if pending_media:
            blocks.extend(pending_media)
            pending_media.clear()

    media = media or {}
    pages = pages or []

    # ── Media Pool Management ────────────────────────────────────────────────
    section_media_pool = {
        mid: b64 for mid, b64 in media.items()
        if any(mid.startswith(f"T_{p}_") or mid.startswith(f"F_{p}_") for p in pages)
    }
    consumed_pool_ids = set()
    # ─────────────────────────────────────────────────────────────────────────

    # Regex for placeholders (supports [...] and [[...]])
    MARKER_RE = re.compile(r'(\[{1,2}(?:TABLE|FIGURE)_IMAGE:.*?\]{1,2})', re.IGNORECASE)

    # If the section text already contains inline markers from spatial extraction,
    # disable the caption-fallback path (Path 2) entirely. Using both simultaneously
    # causes intro sentences like "Table 6 below shows..." to incorrectly pull images
    # from the pool on the same pass that markers are already handling placement.
    has_inline_markers = bool(MARKER_RE.search(text))

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            # Significant break! Flush text, then emit any queued images immediately
            flush_buffer()
            flush_pending_media()
            continue
            
        if stripped.upper() in _SECTION_HEADING_EXACT:
            flush_buffer()
            continue

        # 1. Check for standalone subheading
        is_subheading = False
        if labels:
            matched_label = next(
                (label for label in labels
                 if label.lower() in stripped.lower() and len(stripped) <= len(label) + 15),
                None
            )
            if matched_label:
                flush_buffer()         # Flush existing paragraph text
                flush_pending_media()  # Emit any images that belong BEFORE this subheading
                blocks.append({"type": "subheading", "text": stripped})
                is_subheading = True
        
        if is_subheading:
            continue

        # 2. Check for Table/Figure Label (Caption) — only when no inline markers exist.
        # If the section has [[TABLE_IMAGE:X]] markers, spatial extraction handled placement;
        # running this fallback simultaneously causes intro sentences to wrongly pull images.
        if not has_inline_markers and _TABLE_FIGURE_RE.match(stripped):
            # Flush any accumulated paragraph text first
            flush_buffer()
            # Fallback caption matching
            is_table = stripped.upper().startswith("TABLE")
            prefix = "T_" if is_table else "F_"
            pool_keys = sorted(section_media_pool.keys(), key=lambda x: [int(c) if c.isdigit() else c for c in re.split('([0-9]+)', x)])
            match_id = next((pk for pk in pool_keys if pk.startswith(prefix) and pk not in consumed_pool_ids), None)
            
            if match_id:
                # Emit the image immediately at this exact position in the stream
                blocks.append({
                    "type": "table-image", 
                    "id": match_id, 
                    "text": section_media_pool[match_id]
                })
                consumed_pool_ids.add(match_id)
            else:
                # No image found, keep the text label as a fallback
                blocks.append({"type": "table-label", "text": stripped})
            continue

        # 3. Handle mixed text and markers (Inline support)
        # We split the line by any markers, keeping the markers as parts
        parts = MARKER_RE.split(stripped)
        for part in parts:
            p_stripped = part.strip()
            if not p_stripped:
                continue
                
            m_match = MARKER_RE.match(p_stripped)
            if m_match:
                # This part is a marker — flush accumulated text first, then emit image immediately
                flush_buffer()
                id_match = re.search(r':(.*?)[\]]', p_stripped)
                if id_match:
                    m_id = id_match.group(1).strip()
                    if m_id in media and m_id not in consumed_pool_ids:
                        blocks.append({
                            "type": "table-image",
                            "id": m_id,
                            "text": media[m_id]
                        })
                        consumed_pool_ids.add(m_id)
            else:
                # This part is regular text
                buffer.append(p_stripped)

    flush_buffer()
    flush_pending_media()  # Safety net: emit any images that were never flushed
    return blocks


# ── Service class ─────────────────────────────────────────────────────────────

class IMRADStructureService:
    """
    Builds a structured representation of all IMRAD sections from a Paper object.
    Called at response time in the papers router — no DB writes required.
    """

    def build(self, paper: Any) -> Dict[str, List[Dict[str, Any]]]:
        """
        Accepts a Paper SQLAlchemy model (or any object with .methods / .results
        / .discussion / .introduction attributes) and returns a dict of
        section_key → list of typed blocks.

        Introduction is returned as a single text block (it uses the summary
        in the IMRAD view, not the structured raw text).
        """
        result: Dict[str, List[Dict[str, Any]]] = {}

        # The media store is a JSON dict mapping IDs to base64 images
        media = getattr(paper, "media", {}) or {}
        section_pages = getattr(paper, "section_pages", {}) or {}

        section_map = {
            "introduction": getattr(paper, "introduction", None),
            "methods":      getattr(paper, "methods", None),
            "results":      getattr(paper, "results", None),
            "discussion":   getattr(paper, "discussion", None),
        }

        for key, text in section_map.items():
            if text and text.strip():
                pages_for_sec = section_pages.get(key, [])
                result[key] = _structure_section(text, key, media=media, pages=pages_for_sec)

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