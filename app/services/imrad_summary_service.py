"""
imrad_summary_service.py
────────────────────────
100% local, zero-cost extractive summariser for IMRAD sections.
No external API. No paid services. Uses only the Python standard library
plus re/collections (already installed in any Python 3.8+ environment).

Strategy per section
────────────────────
Introduction  — extract the top sentences from the Introduction section as a
                single prose block. Sub-section headings (Background, Objectives,
                SOP, etc.) remain part of the body text and are not re-split.

Methods       — detect sub-headings from METHODOLOGY_SUBHEADINGS, extract 2
                sentences per sub-heading block.

Results       — pick top 5 sentences from the whole section by sentence score.

Discussion    — pick top 4 sentences, preferring sentences that contain
                conclusion/recommendation signal words.

All summaries are returned as plain text with labelled sub-sections where
applicable.  No bullet points — plain academic prose paragraphs separated
by sub-section headings.

Usage
─────
    from app.services.imrad_summary_service import imrad_summary_service

    # Synchronous — no await needed
    summaries = imrad_summary_service.summarise_all(paper.sections_dict())
    # → {"introduction": "...", "methods": "...", "results": "...", "discussion": "..."}

    summaries = imrad_summary_service.summarise_missing(
        paper.sections_dict(), paper.summaries_dict()
    )
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
]

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

MIN_SENTENCE_CHARS = 40

INTRO_SENTENCES_PER_SUBSECTION   = 3
METHODS_SENTENCES_PER_SUBHEADING = 2
RESULTS_TOP_N    = 5
DISCUSSION_TOP_N = 4

# Hard character cap on each stored summary — raised to fit a 3-page intro
MAX_SUMMARY_CHARS = 6000

# Signal words that boost a sentence's score for the Discussion section
CONCLUSION_SIGNALS = [
    "conclud", "recommend", "suggest", "therefore", "thus", "hence",
    "implication", "finding", "result", "significant", "effectiv",
    "achiev", "demonstrat", "confirm", "support", "indicat",
]

# ── Introduction sub-section detection ───────────────────────────────────────
INTRO_SUBSECTIONS: List[Dict] = [
    {
        "label":    "Background of the Study",
        "patterns": [
            r"Background\s+of\s+the\s+Study",
            r"Introduction\s+and\s+Background",
            r"Background\s+and\s+Rationale",
            r"Project\s+Context",
            r"Context\s+of\s+the\s+(?:Study|Project)",
        ],
    },
    {
        "label":    "Statement of the Problem",
        "patterns": [
            r"Statement\s+of\s+the\s+Problem",
            r"Research\s+(?:Problem|Questions?)",
            r"Problem\s+Statement",
        ],
    },
    {
        "label":    "Objectives of the Study",
        "patterns": [
            r"Objectives?\s+of\s+the\s+Study",
            r"Research\s+Objectives?",
            r"Aims?\s+(?:and\s+Objectives?|of\s+the\s+Study)",
            r"General\s+Objective",
            r"Specific\s+Objectives?",
            r"Purpose\s+and\s+Description",
            r"Purpose\s+of\s+the\s+(?:Study|Project)",
        ],
    },
    {
        "label":    "Significance of the Study",
        "patterns": [
            r"Significance\s+of\s+the\s+Study",
            r"Importance\s+of\s+the\s+Study",
        ],
    },
    {
        "label":    "Scope and Delimitation",
        "patterns": [
            r"Scope\s+and\s+(?:Delimitation|Limitation)",
            r"Delimitation\s+of\s+the\s+Study",
        ],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Core NLP helpers  (zero external dependencies)
# ─────────────────────────────────────────────────────────────────────────────

_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "this",
    "that", "these", "those", "it", "its", "they", "their", "them",
    "he", "she", "we", "you", "i", "my", "our", "your", "his", "her",
    "which", "who", "whom", "what", "when", "where", "how", "not",
    "also", "such", "more", "than", "there", "then", "so", "if",
    "used", "using", "use", "study", "research", "paper", "result",
})


def _tokenize(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-z]+", text.lower())
            if w not in _STOPWORDS and len(w) > 2]


def _split_sentences(text: str) -> List[str]:
    """Simple sentence splitter that preserves common abbreviations."""
    protected = re.sub(
        r'\b(Dr|Mr|Mrs|Ms|Prof|Fig|et al|vs|e\.g|i\.e|approx|etc)\.',
        lambda m: m.group(0).replace('.', '<!DOT!>'),
        text,
    )
    raw = re.split(r'(?<=[.!?])\s+(?=[A-Z])', protected)
    sentences = []
    for s in raw:
        s = s.replace('<!DOT!>', '.').strip()
        if len(s) >= MIN_SENTENCE_CHARS:
            sentences.append(s)
    return sentences


def _score_sentences(
    sentences: List[str],
    boost_signals: Optional[List[str]] = None,
) -> List[Tuple[int, float]]:
    """
    TF-IDF-inspired sentence scoring.
    Returns [(original_index, score)] sorted by score descending.
    """
    if not sentences:
        return []

    corpus_freq: Counter = Counter()
    sent_tokens = []
    for s in sentences:
        tokens = _tokenize(s)
        sent_tokens.append(tokens)
        corpus_freq.update(set(tokens))

    n = len(sentences)
    scored = []
    for idx, tokens in enumerate(sent_tokens):
        if not tokens:
            scored.append((idx, 0.0))
            continue
        score = sum(
            math.log(n / corpus_freq[w]) if corpus_freq[w] > 0 else 0
            for w in set(tokens)
        )
        score /= math.sqrt(len(tokens))
        if boost_signals:
            sent_lower = sentences[idx].lower()
            bonus = sum(1 for sig in boost_signals if sig in sent_lower)
            score += bonus * 0.5
        scored.append((idx, score))

    return sorted(scored, key=lambda x: x[1], reverse=True)


def _truncate_to_sentence(text: str, max_chars: int) -> str:
    """
    Truncate text at max_chars, but walk back to the nearest sentence-ending
    punctuation so the result never cuts off mid-sentence.
    """
    if len(text) <= max_chars:
        return text
    chunk = text[:max_chars]
    # Walk back to the last '.', '!', or '?' followed by whitespace
    for i in range(len(chunk) - 1, max(0, len(chunk) - 300), -1):
        if chunk[i] in '.!?' and (i + 1 >= len(chunk) or chunk[i + 1] in ' \n'):
            return chunk[:i + 1].strip()
    return chunk.rstrip(" ,;")


def _top_sentences(
    text: str,
    n: int,
    boost_signals: Optional[List[str]] = None,
) -> str:
    """
    Pick top-n sentences by TF-IDF score, returned in original document order.

    Only falls back to raw text when there are genuinely fewer sentences than
    requested. Otherwise always summarises — even a small pool is worth scoring.
    """
    sentences = _split_sentences(text)

    if not sentences:
        return _truncate_to_sentence(text, MAX_SUMMARY_CHARS)

    # Fewer sentences than requested — return all of them (already short enough)
    if len(sentences) <= n:
        return " ".join(sentences)

    ranked = _score_sentences(sentences, boost_signals)
    top_indices = sorted([idx for idx, _ in ranked[:n]])
    return " ".join(sentences[i] for i in top_indices)


# ─────────────────────────────────────────────────────────────────────────────
# Sub-section splitters
# ─────────────────────────────────────────────────────────────────────────────

def _split_into_intro_subsections(text: str) -> List[Tuple[str, str]]:
    """Split Introduction into (label, body) pairs by heading keyword."""
    hits: List[Tuple[int, str]] = []
    for sub in INTRO_SUBSECTIONS:
        for pat in sub["patterns"]:
            # Heading should be at start of line or preceded by newline
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                hits.append((m.start(), sub["label"]))
                break

    if not hits:
        return [("Introduction", text)]

    hits.sort(key=lambda x: x[0])
    parts: List[Tuple[str, str]] = []
    
    # Pre-heading text (if any)
    pre = text[:hits[0][0]].strip()
    if pre and len(pre) > MIN_SENTENCE_CHARS:
        parts.append(("Introduction", pre))

    for i, (start, label) in enumerate(hits):
        end = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        body = text[start:end].strip()
        
        # Aggressively remove the heading line
        # headings are often short lines at the start of the block
        lines = body.split("\n")
        if lines:
            first_line = lines[0].strip()
            # If the first line is short and contains the label, or looks like a heading
            label_pat = label.lower().replace(" ", r"\s*")
            if (len(first_line) < 100 and 
                (re.search(label_pat, first_line.lower()) or 
                 re.match(r"^(?:[IVXLC]+|\d+)[\.\s]*$", first_line))):
                body = "\n".join(lines[1:]).strip()
            else:
                # Fallback: try to re.sub it from the start of the whole block
                clean_label = re.escape(label)
                body = re.sub(r"^(?:[IVXLC]+|\d+)[\.\s]*" + clean_label + r"[:\s\-]*(?:\n|$)", "", body, flags=re.IGNORECASE | re.MULTILINE).strip()
                # If it still starts with a number like "3. ", strip it if followed by a newline or start of prose
                body = re.sub(r"^(?:[IVXLC]+|\d+)[\.\s]+(?=[A-Z])", "", body).strip()
        
        if body:
            parts.append((label, body))

    return parts or [("Introduction", text)]


def _split_methods_by_subheadings(text: str) -> List[Tuple[str, str]]:
    """Split Methods text into (label, body) pairs using METHODOLOGY_SUBHEADINGS."""
    hits: List[Tuple[int, str]] = []
    for entry in METHODOLOGY_SUBHEADINGS:
        for pat in entry["patterns"]:
            m = re.search(r"\b" + pat + r"\b", text, re.IGNORECASE)
            if m:
                hits.append((m.start(), entry["label"]))
                break

    if not hits:
        return [("Methodology", text)]

    hits.sort(key=lambda x: x[0])
    parts: List[Tuple[str, str]] = []
    for i, (start, label) in enumerate(hits):
        end = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        body = text[start:end].strip()

        # Aggressively remove the heading line
        lines = body.split("\n")
        if lines:
            first_line = lines[0].strip()
            label_pat = label.lower().replace(" ", r"\s*")
            if (len(first_line) < 100 and 
                (re.search(label_pat, first_line.lower()) or 
                 re.match(r"^(?:[IVXLC]+|\d+)[\.\s]*$", first_line))):
                body = "\n".join(lines[1:]).strip()
            else:
                clean_label = re.escape(label)
                body = re.sub(r"^(?:[IVXLC]+|\d+)[\.\s]*" + clean_label + r"[:\s\-]*(?:\n|$)", "", body, flags=re.IGNORECASE | re.MULTILINE).strip()
                body = re.sub(r"^(?:[IVXLC]+|\d+)[\.\s]+(?=[A-Z])", "", body).strip()

        if body:
            parts.append((label, body))

    return parts or [("Methodology", text)]


# ─────────────────────────────────────────────────────────────────────────────
# Per-section summarisers
# ─────────────────────────────────────────────────────────────────────────────

def _summarise_introduction(text: str) -> str:
    """
    Summarise the Introduction section.

    If the introduction has detectable sub-sections (Background of the Study,
    Statement of the Problem, Objectives, etc.), summarise each sub-section
    with a label — this handles documents where the intro consists entirely of
    named sub-sections with no separate opening paragraph.

    If no sub-sections are detected, summarise as a single prose block.
    """
    parts = _split_into_intro_subsections(text)

    # Single block (no sub-sections found) — summarise as one paragraph
    if len(parts) == 1 and parts[0][0] == "Introduction":
        summary = _top_sentences(text, 5)
        return _truncate_to_sentence(summary, MAX_SUMMARY_CHARS)

    # Multiple sub-sections — summarise each and join into a single prose block
    blocks: list = []
    for label, body in parts:
        if not body or len(body.strip()) < MIN_SENTENCE_CHARS:
            continue
        sentences = _split_sentences(body)
        # Take up to 3 sentences per sub-section, or all if fewer
        n = min(3, len(sentences)) if sentences else 0
        if n == 0:
            # Body has no proper sentences — use first 200 chars as fallback
            snippet = body.strip()[:200].rstrip(" ,;")
            if snippet:
                blocks.append(snippet)
        else:
            ranked = _score_sentences(sentences)
            top_idx = sorted([i for i, _ in ranked[:n]])
            summary = " ".join(sentences[i] for i in top_idx)
            if summary.strip():
                blocks.append(summary.strip())

    result = " ".join(blocks)
    # Final cleanup: remove any leftover numbering markers from the start of sentences in the prose
    result = re.sub(r"(?<=\. )(?:\d+[\.\s]+|§\s*)", "", result)
    result = re.sub(r"^(?:\d+[\.\s]+|§\s*)", "", result)
    
    return _truncate_to_sentence(result.strip(), MAX_SUMMARY_CHARS) if result.strip() else _truncate_to_sentence(text, MAX_SUMMARY_CHARS)


def _summarise_methods(text: str) -> str:
    # Raw pass-through — Methods section is stored as-is with subheading
    # line breaks already embedded. No extractive summarisation: the full
    # structured text is more useful than a compressed version, and the
    # frontend renders subheadings visually from the raw text.
    return _truncate_to_sentence(text.strip(), MAX_SUMMARY_CHARS)


def _summarise_results(text: str) -> str:
    # Raw pass-through — same rationale as Methods. Results sections often
    # contain evaluation tables and structured data that extractive sentence
    # scoring destroys. Return the full text up to the char cap.
    return _truncate_to_sentence(text.strip(), MAX_SUMMARY_CHARS)


def _summarise_discussion(text: str) -> str:
    # Raw pass-through for combined RAD documents. For pure Discussion/Conclusion
    # sections (Chapter V), use extractive scoring to surface key sentences.
    sentences = _split_sentences(text)
    # Heuristic: if very few sentences, it's likely a pure conclusion section
    # → extractive is fine. If many sentences, it's a combined RAD → raw.
    if len(sentences) <= 8:
        return _truncate_to_sentence(
            _top_sentences(text, DISCUSSION_TOP_N, boost_signals=CONCLUSION_SIGNALS),
            MAX_SUMMARY_CHARS,
        )
    return _truncate_to_sentence(text.strip(), MAX_SUMMARY_CHARS)


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