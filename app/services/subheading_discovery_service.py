"""
subheading_discovery_service.py
────────────────────────────────
Automatically discovers unknown subheadings from new PDFs and learns them
over time via a frequency-based registry. Zero external API cost.

How it works
────────────
  1. SCAN  — When a PDF is processed, _scan_section_text() scores every line
             using 5 structural signals (bold font, short length, title-case,
             no trailing punctuation, surrounded by paragraph text). Lines
             that clear the threshold are "candidates".

  2. FILTER — Candidates are deduplicated and cleaned. Known labels and
              obvious false positives (table captions, column headers, page
              numbers) are excluded.

  3. REGISTER — Each new candidate is written to the JSON registry with a
                count of 1. Each time the same phrase is seen again across
                different papers, its count increments.

  4. PROMOTE — Candidates whose count reaches PROMOTE_THRESHOLD are
               automatically promoted to the active label lists in
               imrad_structure_service, so they start working immediately
               for all future documents — no code change needed.

  5. SIMILARITY CHECK — Before registering a new candidate, we check if it
                        is "close enough" to an existing confirmed label using
                        difflib (no ML model required). If so, we map it to
                        the existing label instead of creating a duplicate.

Registry file
─────────────
  Stored as JSON at REGISTRY_PATH (default: app/data/subheading_registry.json)
  Format:
  {
    "General Rating in Usability": {
      "count": 7,
      "section": "results",
      "confirmed": true,       ← promoted once count >= PROMOTE_THRESHOLD
      "source": "auto",        ← "auto" | "manual"
      "first_seen": "2025-01-15",
      "last_seen": "2025-06-10"
    },
    ...
  }

Integration
───────────
  Called from ocr_service.py after section text is extracted:

      from app.services.subheading_discovery_service import subheading_discovery_service
      subheading_discovery_service.scan_and_register(sections_raw)

  Called from imrad_structure_service.py at module load to merge promoted
  labels into the active lists:

      from app.services.subheading_discovery_service import subheading_discovery_service
      subheading_discovery_service.patch_label_lists()
"""

from __future__ import annotations

import json
import os
import re
from datetime import date
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Set, Tuple

from app.services.logging_service import log

# ── Configuration ─────────────────────────────────────────────────────────────

# Where the registry JSON lives. Adjust to match your project layout.
REGISTRY_PATH: str = os.path.join(
    os.path.dirname(__file__), "..", "data", "subheading_registry.json"
)

# How many distinct papers must contain a candidate before it is auto-promoted
# to the active label lists. Lower = learns faster but more false positives.
PROMOTE_THRESHOLD: int = 2

# Scoring weights for each structural signal (must sum to 1.0)
SIGNAL_WEIGHTS = {
    "bold":          0.35,   # line was bold in the PDF (highest signal)
    "short":         0.20,   # line is ≤ 10 words
    "title_case":    0.20,   # majority of words are capitalised
    "no_end_punct":  0.15,   # line does not end with . , ; :
    "isolated":      0.10,   # preceded or followed by a blank line
}

# Minimum score to consider a line a subheading candidate
CANDIDATE_THRESHOLD: float = 0.55

# Similarity threshold for mapping a new candidate to an existing label
# (uses difflib ratio, 0–1). Above this → treat as same label.
SIMILARITY_THRESHOLD: float = 0.82

# Hard maximum word count for a subheading candidate
MAX_CANDIDATE_WORDS: int = 12

# Minimum word count (avoids single words like "TOTAL", "N/A")
MIN_CANDIDATE_WORDS: int = 2

# ── False-positive patterns — lines matching these are never candidates ───────
_FP_PATTERNS: List[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in [
    r"^(?:Table|Figure|Fig\.?)\s+\d+",          # table/figure captions
    r"^\d[\d\.\,\s]+$",                          # pure numbers / scores
    r"^(?:TOTAL|N\/?A|YES|NO|TRUE|FALSE)$",      # table cell values
    r"\b(?:mean score|weighted mean|percentage|interpretation)\b",  # table headers
    r"^\s*(?:page\s*)?\d+\s*$",                  # page numbers
    r"^[A-Z\s]{1,3}$",                           # 1-3 ALL-CAPS chars (abbrevs)
    r"\b(?:www\.|http|\.com|\.ph)\b",            # URLs
    r"^(?:References?|Bibliography|Appendix|Appendices)\b",  # back-matter
    # Table row values: contain a decimal score AND an interpretation word
    r"\b\d+\.\d+\b.{0,30}\b(?:Acceptable|Excellent|Satisfactory|Fair|Poor|Good|Very Good|Outstanding)\b",
    # ALL-CAPS phrase that also contains numbers (data row, not a heading)
    r"^[A-Z][A-Z\s]+\s+\d+[\.\d]*\s+",
    # Lines with 3+ whitespace-separated tokens where one is a decimal (table row)
    r"^\S+\s+\d+[\.,]\d+\s+\S+$",
]]

# ── Section key normaliser ────────────────────────────────────────────────────
_SECTION_ALIASES: Dict[str, str] = {
    "introduction":        "introduction",
    "methods":             "methods",
    "methodology":         "methods",
    "results":             "results",
    "results_and_discussion": "results",
    "discussion":          "results",   # discussion subheadings share results list
}


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalise_key(section_key: str) -> str:
    return _SECTION_ALIASES.get(section_key.lower(), section_key.lower())


def _is_false_positive(line: str) -> bool:
    """Return True if the line should never be treated as a subheading."""
    for pat in _FP_PATTERNS:
        if pat.search(line.strip()):
            return True
    return False


def _title_case_ratio(line: str) -> float:
    """Fraction of words (≥3 chars) that start with a capital letter."""
    words = [w for w in line.split() if len(w) >= 3]
    if not words:
        return 0.0
    return sum(1 for w in words if w[0].isupper()) / len(words)


def _score_line(
    line: str,
    is_bold: bool,
    prev_blank: bool,
    next_blank: bool,
) -> float:
    """
    Score a single line on structural heading signals. Returns 0–1.
    Higher = more likely to be a subheading.
    """
    stripped = line.strip()
    if not stripped:
        return 0.0

    word_count = len(stripped.split())
    if word_count < MIN_CANDIDATE_WORDS or word_count > MAX_CANDIDATE_WORDS:
        return 0.0

    scores: Dict[str, float] = {
        "bold":         1.0 if is_bold else 0.0,
        "short":        1.0 if word_count <= 10 else max(0.0, 1.0 - (word_count - 10) * 0.1),
        "title_case":   _title_case_ratio(stripped),
        "no_end_punct": 0.0 if stripped[-1] in ".,:;" else 1.0,
        "isolated":     1.0 if (prev_blank or next_blank) else 0.0,
    }

    return sum(SIGNAL_WEIGHTS[k] * v for k, v in scores.items())


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _find_similar_label(
    candidate: str,
    known_labels: List[str],
) -> Optional[str]:
    """
    Return the closest known label if similarity exceeds threshold,
    otherwise None (candidate is genuinely new).
    """
    best_label: Optional[str] = None
    best_score: float = 0.0
    for label in known_labels:
        s = _similarity(candidate, label)
        if s > best_score:
            best_score = s
            best_label = label
    if best_score >= SIMILARITY_THRESHOLD:
        return best_label
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Registry I/O
# ─────────────────────────────────────────────────────────────────────────────

def _load_registry() -> Dict:
    """Load the JSON registry. Returns empty dict on first run."""
    try:
        if os.path.exists(REGISTRY_PATH):
            with open(REGISTRY_PATH, encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log.error("SubheadingRegistry: load failed", exc=e)
    return {}


def _save_registry(registry: Dict) -> None:
    """Persist the registry to disk."""
    try:
        os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
        with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.error("SubheadingRegistry: save failed", exc=e)


# ─────────────────────────────────────────────────────────────────────────────
# Candidate extraction from plain text (no PDF required — works on stored text)
# ─────────────────────────────────────────────────────────────────────────────

def _extract_candidates_from_text(
    text: str,
    section_key: str,
    known_labels: List[str],
    bold_lines: Optional[Set[str]] = None,
) -> List[Tuple[str, float]]:
    """
    Scan a section's plain text for subheading candidates.

    bold_lines — optional set of line content strings that were bold in the
                 source PDF (extracted via PyMuPDF in imrad_service). If not
                 provided, the bold signal is skipped (score still works via
                 other signals).

    Returns list of (candidate_text, score) sorted by score descending.
    """
    bold_lines = bold_lines or set()
    lines = text.split("\n")
    candidates: List[Tuple[str, float]] = []
    seen: Set[str] = set()

    # Build a fast lookup of already-known labels (lowercased)
    known_lower: Set[str] = {lbl.lower() for lbl in known_labels}

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        # Skip already-known labels — nothing to discover there
        if stripped.lower() in known_lower:
            continue

        # Skip obvious false positives
        if _is_false_positive(stripped):
            continue

        prev_blank = (i == 0) or (not lines[i - 1].strip())
        next_blank = (i == len(lines) - 1) or (not lines[i + 1].strip())
        is_bold = stripped in bold_lines or stripped.upper() in bold_lines

        score = _score_line(stripped, is_bold, prev_blank, next_blank)

        if score >= CANDIDATE_THRESHOLD:
            # Normalise: strip leading numbering like "A. " or "1. "
            clean = re.sub(r'^(?:[IVXLC\d]+|[A-Za-z])[.\s]+', '', stripped).strip()
            if not clean or clean.lower() in seen:
                continue
            seen.add(clean.lower())
            candidates.append((clean, score))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates


# ─────────────────────────────────────────────────────────────────────────────
# Public service
# ─────────────────────────────────────────────────────────────────────────────

class SubheadingDiscoveryService:
    """
    Singleton service. Import `subheading_discovery_service`, not this class.

    Primary entry points
    ────────────────────
    scan_and_register(sections)          ← call after PDF extraction
    patch_label_lists()                  ← call at app startup / module load
    get_promoted_labels(section_key)     ← get confirmed labels for a section
    add_manual(label, section_key)       ← admin: force-add a label
    get_registry_summary()               ← admin: view all candidates + counts
    """

    def __init__(self) -> None:
        self._registry: Dict = _load_registry()
        self._patched: bool = False

    # ── Core: scan + register ─────────────────────────────────────────────────

    def scan_and_register(
        self,
        sections: Dict[str, str],
        bold_lines_by_section: Optional[Dict[str, Set[str]]] = None,
    ) -> Dict[str, List[str]]:
        """
        Scan all sections of a newly processed paper for unknown subheadings
        and register them in the registry.

        sections               — {section_key: raw_text} from imrad extraction
        bold_lines_by_section  — optional {section_key: set_of_bold_line_strings}
                                 from PyMuPDF font metadata. Pass None to skip.

        Returns {section_key: [newly_registered_candidates]} for logging.
        """
        from app.services.imrad_structure_service import (
            INTRODUCTION_LABELS, METHODOLOGY_LABELS, RESULTS_LABELS
        )

        label_map: Dict[str, List[str]] = {
            "introduction": list(INTRODUCTION_LABELS),
            "methods":      list(METHODOLOGY_LABELS),
            "results":      list(RESULTS_LABELS),
        }
        # Merge in any already-promoted registry labels
        for label, meta in self._registry.items():
            if meta.get("confirmed"):
                sec = meta.get("section", "results")
                if label not in label_map.get(sec, []):
                    label_map.setdefault(sec, []).append(label)

        all_known: List[str] = [lbl for lst in label_map.values() for lbl in lst]
        new_by_section: Dict[str, List[str]] = {}

        for section_key, text in sections.items():
            if not text or not text.strip():
                continue

            norm_key = _normalise_key(section_key)
            known_for_section = label_map.get(norm_key, []) + all_known
            bold_lines = (bold_lines_by_section or {}).get(section_key, set())

            candidates = _extract_candidates_from_text(
                text, norm_key, known_for_section, bold_lines
            )

            newly_registered: List[str] = []
            for candidate, score in candidates:
                registered = self._register_candidate(candidate, norm_key, score)
                if registered:
                    newly_registered.append(candidate)

            if newly_registered:
                new_by_section[section_key] = newly_registered
                log.info(
                    f"SubheadingDiscovery: {len(newly_registered)} new candidates in '{section_key}'",
                    candidates=", ".join(newly_registered[:5])
                )

        _save_registry(self._registry)
        return new_by_section

    def _register_candidate(
        self, candidate: str, section_key: str, score: float
    ) -> bool:
        """
        Register or increment a candidate in the registry.
        Returns True if this was a genuinely new entry.
        """
        today = str(date.today())

        # Check similarity to existing registry entries
        existing_keys = list(self._registry.keys())
        similar = _find_similar_label(candidate, existing_keys)

        if similar:
            # Increment the existing entry's count instead of creating a duplicate
            self._registry[similar]["count"] += 1
            self._registry[similar]["last_seen"] = today
            self._maybe_promote(similar)
            return False  # Not a brand-new entry

        # Genuinely new candidate — create a registry entry
        self._registry[candidate] = {
            "count":      1,
            "section":    section_key,
            "confirmed":  False,
            "source":     "auto",
            "score":      round(score, 3),
            "first_seen": today,
            "last_seen":  today,
        }
        log.info(f"SubheadingDiscovery: new candidate registered", label=candidate, section=section_key, score=round(score, 3))
        return True

    def _maybe_promote(self, label: str) -> None:
        """Promote a candidate to confirmed if it has hit the threshold."""
        entry = self._registry.get(label)
        if not entry or entry.get("confirmed"):
            return
        if entry["count"] >= PROMOTE_THRESHOLD:
            entry["confirmed"] = True
            log.success(
                f"SubheadingDiscovery: PROMOTED '{label}' → {entry['section']} labels",
                count=entry["count"]
            )
            # Invalidate the patch cache so next call to patch_label_lists() picks it up
            self._patched = False

    # ── Patch label lists at startup ──────────────────────────────────────────

    def patch_label_lists(self) -> None:
        """
        Merge all confirmed registry entries into the active label lists in
        imrad_structure_service. Call once at startup or after promotion.

        This mutates the module-level lists (INTRODUCTION_LABELS, etc.) in
        place so every subsequent call to _structure_section() benefits
        automatically with no restart required.
        """
        if self._patched:
            return

        import app.services.imrad_structure_service as svc

        promoted: Dict[str, List[str]] = {"introduction": [], "methods": [], "results": []}

        for label, meta in self._registry.items():
            if not meta.get("confirmed"):
                continue
            sec = meta.get("section", "results")
            target_sec = _normalise_key(sec)
            if target_sec not in promoted:
                promoted[target_sec] = []
            promoted[target_sec].append(label)

        # Patch introduction
        for lbl in promoted.get("introduction", []):
            if lbl not in svc.INTRODUCTION_LABELS:
                svc.INTRODUCTION_LABELS.append(lbl)

        # Patch methodology
        for lbl in promoted.get("methods", []):
            if lbl not in svc.METHODOLOGY_LABELS:
                svc.METHODOLOGY_LABELS.append(lbl)

        # Patch results (covers results + discussion)
        for lbl in promoted.get("results", []):
            if lbl not in svc.RESULTS_LABELS:
                svc.RESULTS_LABELS.append(lbl)

        # Keep ALL_SUBHEADING_LABELS in sync
        svc.ALL_SUBHEADING_LABELS = (
            svc.INTRODUCTION_LABELS + svc.METHODOLOGY_LABELS + svc.RESULTS_LABELS
        )

        total = sum(len(v) for v in promoted.values())
        if total:
            log.success(
                f"SubheadingDiscovery: patched {total} confirmed labels into active lists",
                intro=len(promoted.get("introduction", [])),
                methods=len(promoted.get("methods", [])),
                results=len(promoted.get("results", [])),
            )
        self._patched = True

    # ── Manual admin controls ─────────────────────────────────────────────────

    def add_manual(self, label: str, section_key: str) -> None:
        """
        Force-add a label as confirmed immediately (admin / seeding use).
        Useful for known labels you want to pre-load without waiting for
        the frequency threshold.
        """
        norm_key = _normalise_key(section_key)
        today = str(date.today())
        self._registry[label] = {
            "count":      PROMOTE_THRESHOLD,
            "section":    norm_key,
            "confirmed":  True,
            "source":     "manual",
            "score":      1.0,
            "first_seen": today,
            "last_seen":  today,
        }
        _save_registry(self._registry)
        self._patched = False  # Force re-patch on next call
        log.success(f"SubheadingDiscovery: manually added '{label}' → {norm_key}")

    def remove(self, label: str) -> bool:
        """Remove a label from the registry (admin use)."""
        if label in self._registry:
            del self._registry[label]
            _save_registry(self._registry)
            self._patched = False
            log.info(f"SubheadingDiscovery: removed '{label}'")
            return True
        return False

    def get_promoted_labels(self, section_key: str) -> List[str]:
        """Return all confirmed labels for a section."""
        norm_key = _normalise_key(section_key)
        return [
            lbl for lbl, meta in self._registry.items()
            if meta.get("confirmed") and _normalise_key(meta.get("section", "")) == norm_key
        ]

    def get_registry_summary(self) -> Dict:
        """
        Returns the full registry grouped by section and sorted by count.
        Useful for an admin dashboard endpoint.
        """
        summary: Dict[str, List[Dict]] = {}
        for label, meta in self._registry.items():
            sec = meta.get("section", "unknown")
            summary.setdefault(sec, []).append({
                "label":      label,
                "count":      meta["count"],
                "confirmed":  meta["confirmed"],
                "source":     meta["source"],
                "score":      meta.get("score", 0),
                "first_seen": meta.get("first_seen"),
                "last_seen":  meta.get("last_seen"),
            })
        for sec in summary:
            summary[sec].sort(key=lambda x: x["count"], reverse=True)
        return summary

    def reload_registry(self) -> None:
        """Hot-reload the registry from disk (e.g. after a manual JSON edit)."""
        self._registry = _load_registry()
        self._patched = False
        log.info("SubheadingDiscovery: registry reloaded from disk")


# ── Singleton ─────────────────────────────────────────────────────────────────
subheading_discovery_service = SubheadingDiscoveryService()