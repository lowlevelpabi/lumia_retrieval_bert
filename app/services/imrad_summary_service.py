"""
imrad_summary_service.py
────────────────────────
100% local, zero-cost raw text extraction for IMRAD sections.
No external API. No paid services. 

Strategy per section
────────────────────
All sections (Introduction, Methods, Results, Discussion) are now 
returned as-is from their original extractions (up to character limits), 
preserving all markers and sub-headings. No extractive summarisation 
is applied.

Usage
─────
    from app.services.imrad_summary_service import imrad_summary_service

    # Synchronous — no await needed
    raw_texts = imrad_summary_service.summarise_all(paper.sections_dict())
    # → {"introduction": "...", "methods": "...", "results": "...", "discussion": "..."}
"""

import re
import math
from collections import Counter
from typing import Dict, List, Optional, Tuple
from app.services.logging_service import log

# ── Constants (previously imported from imrad_service — defined locally to avoid
#    a circular/missing import that silently kills the whole module) ──────────
IMRAD_SECTION_KEYS = ["introduction", "methods", "results", "discussion"]
MIN_SECTION_CHARS  = 50   # minimum chars for a section to be worth summarising

# Methodology sub-heading patterns used by _split_methods_by_subheadings.
# Kept in sync with imrad_service.METHODOLOGY_SUBHEADINGS.
METHODOLOGY_SUBHEADINGS = [
    {"label": "Research Design",                            "patterns": ["Research\\s+(?:Approach\\s+(?:and\\s+)?)?Design", "Research\\s+Design"]},
    {"label": "Research Approach",                          "patterns": ["Research\\s+Approach(?:\\s+and\\s+Design)?"]},
    {"label": "Research Settings",                          "patterns": ["Research\\s+Settings?"]},
    {"label": "Business Process",                           "patterns": ["Business\\s+Process"]},
    {"label": "Participants of the Study",                  "patterns": ["Participants?\\s+of\\s+the\\s+Study", "Participants?", "Respondents?"]},
    {"label": "Sampling Technique",                         "patterns": ["Stratified\\s+Sampl(?:ing|e)", "Sampling\\s+Technique"]},
    {"label": "Research Instruments",                       "patterns": ["Research\\s+Instruments?"]},
    {"label": "Data Collection, Instrument, and Procedure", "patterns": ["Data\\s+Collection,?\\s+Instrument,?\\s+and\\s+Procedure", "Data\\s+Collection"]},
    {"label": "Sources of Data",                            "patterns": ["Sources?\\s+of\\s+Data", "Data\\s+to\\s+be\\s+[Gg]athered"]},
    {"label": "Statistical Treatment of Data",              "patterns": ["Statistical\\s+Treatment\\s+of\\s+Data", "Statistical\\s+Treatment"]},
    {"label": "Data Analysis",                              "patterns": ["Data\\s+Anal(?:ysis|ytic)", "Statistical\\s+(?:Analysis|Treatment)"]},
    {"label": "Ethical Considerations",                     "patterns": ["Ethical\\s+Consid", "Ethics"]},
    {"label": "Development Model",                          "patterns": ["Development\\s+Model"]},
    {"label": "Analysis and Quick Design",                  "patterns": ["Analysis\\s+and\\s+Quick\\s+Design"]},
    {"label": "Prototype Cycles",                           "patterns": ["Prototype\\s+Cycles?"]},
    {"label": "Testing",                                    "patterns": ["Testing"]},
    {"label": "Implementation",                             "patterns": ["Implementation"]},
]

# Hard character cap on each stored summary — raised to fit a 3-page intro
MAX_SUMMARY_CHARS = 50000

def _truncate_text(text: str, max_chars: int) -> str:
    """Simple truncation to ensure text fits within database limits."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].strip()

# ─────────────────────────────────────────────────────────────────────────────
# Core Section Processing (Raw Passthrough)
# ─────────────────────────────────────────────────────────────────────────────

def _summarise_introduction(text: str) -> str:
    """Returns the Introduction text truncated to the maximum allowed length."""
    return _truncate_text(text.strip(), MAX_SUMMARY_CHARS)


def _summarise_methods(text: str) -> str:
    """Returns the Methods text truncated to the maximum allowed length."""
    return _truncate_text(text.strip(), MAX_SUMMARY_CHARS)


def _summarise_results(text: str) -> str:
    """Returns the Results text truncated to the maximum allowed length."""
    return _truncate_text(text.strip(), MAX_SUMMARY_CHARS)


def _summarise_discussion(text: str) -> str:
    """Returns the Discussion text truncated to the maximum allowed length."""
    return _truncate_text(text.strip(), MAX_SUMMARY_CHARS)


_SUMMARISERS = {
    "introduction": _summarise_introduction,
    "methods":      _summarise_methods,
    "results":      _summarise_results,
    "discussion":   _summarise_discussion,
}


# ─────────────────────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────────────────────

class IMRADSummaryService:
    """
    Zero-cost local extractive summariser. All methods are synchronous.

    If you need non-blocking behaviour in an async endpoint, wrap with:
        import asyncio
        summaries = await asyncio.to_thread(imrad_summary_service.summarise_all, sections)
    """

    def summarise_section(self, section_key: str, content: str) -> Optional[str]:
        """Extractively summarise one IMRAD section. Returns None on failure."""
        if not content or len(content.strip()) < MIN_SECTION_CHARS:
            return None
        fn = _SUMMARISERS.get(section_key)
        if not fn:
            return None
        try:
            result = fn(content)
            log.ml_summary(section_key, len(result))
            return result if result.strip() else None
        except Exception as e:
            log.error(f"Summary failed — '{section_key}'", exc=e)
            return None

    def summarise_all(self, sections: Dict[str, str]) -> Dict[str, Optional[str]]:
        """Summarise all IMRAD sections. Returns {section_key: summary | None}."""
        results: Dict[str, Optional[str]] = {}
        for key in IMRAD_SECTION_KEYS:
            results[key] = self.summarise_section(key, sections.get(key, ""))
        return results

    def summarise_missing(
        self,
        sections: Dict[str, str],
        existing_summaries: Dict[str, Optional[str]],
    ) -> Dict[str, Optional[str]]:
        """Only generate summaries for sections that don't already have one."""
        missing = {
            key: text
            for key, text in sections.items()
            if key in IMRAD_SECTION_KEYS
            and not existing_summaries.get(key)
            and text
            and len(text.strip()) >= MIN_SECTION_CHARS
        }
        if not missing:
            return {}
        return {key: self.summarise_section(key, text) for key, text in missing.items()}


# Singleton
imrad_summary_service = IMRADSummaryService()