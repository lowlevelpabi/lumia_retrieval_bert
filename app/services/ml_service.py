"""
ml_service.py
─────────────
Local ML enhancements for OCR metadata extraction. Zero API cost.
Uses HuggingFace transformers + KeyBERT — all run offline.

Provides:
  1. keyword_extraction  — KeyBERT extracts meaningful keywords from abstract/text
  2. classify_department — zero-shot NLI classifies department from title+abstract
  3. classify_degree     — zero-shot NLI classifies degree program
  4. classify_project_type — zero-shot NLI: Thesis vs Capstone

Models used (auto-downloaded on first run, ~260MB total):
  - all-MiniLM-L6-v2   (KeyBERT / sentence-transformers) — already used by embedding_service
  - facebook/bart-large-mnli  (zero-shot classification)  — ~1.6GB, downloaded once
  
  If BART is too heavy for your machine, set USE_LIGHTWEIGHT_ZSC = True below
  to use cross-encoder/nli-MiniLM2-L6-H768 (~90MB) instead — slightly less
  accurate but much faster on CPU.

Install:
    pip install keybert sentence-transformers transformers torch
"""

from __future__ import annotations
import re
from typing import List, Optional, Tuple

# ── Config ────────────────────────────────────────────────────────────────────

# Set True to use the smaller/faster NLI model instead of BART
USE_LIGHTWEIGHT_ZSC: bool = True   # flip to False if you have a GPU / more RAM

KEYBERT_MODEL    = "all-MiniLM-L6-v2"   # same model embedding_service already uses
BART_MODEL       = "facebook/bart-large-mnli"
LIGHTWEIGHT_MODEL = "cross-encoder/nli-MiniLM2-L6-H768"

ZSC_MODEL = LIGHTWEIGHT_MODEL if USE_LIGHTWEIGHT_ZSC else BART_MODEL

# Confidence threshold — if the top label scores below this, keep the OCR/regex result
ZSC_MIN_CONFIDENCE: float = 0.45

# Max keywords to extract
MAX_KEYWORDS: int = 8

# ── Candidate labels ──────────────────────────────────────────────────────────

DEPARTMENT_LABELS: List[str] = [
    "Department of Computer Science",
    "Department of Information Technology",
    "Department of Information Systems",
    "Department of Computer Engineering",
    "College of Engineering",
    "College of Education",
    "College of Business",
    "College of Arts and Sciences",
]

DEGREE_LABELS: List[str] = [
    "BSCS",   # Bachelor of Science in Computer Science
    "BSIT",   # Bachelor of Science in Information Technology
    "BSIS",   # Bachelor of Science in Information Systems
    "BSCpE",  # Bachelor of Science in Computer Engineering
]

# Descriptive phrases for each degree (used as ZSC candidate labels — more natural language)
DEGREE_PHRASES: List[str] = [
    "computer science algorithms data structures software engineering",
    "information technology networks systems administration web development",
    "information systems business enterprise database management",
    "computer engineering hardware embedded systems circuits microprocessor",
]

PROJECT_TYPE_LABELS: List[str] = ["Thesis", "Capstone Project"]
PROJECT_TYPE_PHRASES: List[str] = [
    "theoretical research study investigation literature review analysis",
    "system development software application prototype design implementation",
]


# ── Lazy-loaded singletons ────────────────────────────────────────────────────

_keybert_model = None
_zsc_pipeline  = None


def _get_keybert():
    global _keybert_model
    if _keybert_model is None:
        try:
            from keybert import KeyBERT
            _keybert_model = KeyBERT(model=KEYBERT_MODEL)
            print(f"[MLService] KeyBERT loaded ({KEYBERT_MODEL})")
        except Exception as e:
            print(f"[MLService] KeyBERT unavailable: {e}")
            _keybert_model = False   # sentinel — don't retry
    return _keybert_model if _keybert_model is not False else None


def _get_zsc():
    global _zsc_pipeline
    if _zsc_pipeline is None:
        try:
            from transformers import pipeline
            _zsc_pipeline = pipeline(
                "zero-shot-classification",
                model=ZSC_MODEL,
                device=-1,   # CPU — change to 0 for GPU
            )
            print(f"[MLService] Zero-shot classifier loaded ({ZSC_MODEL})")
        except Exception as e:
            print(f"[MLService] Zero-shot classifier unavailable: {e}")
            _zsc_pipeline = False
    return _zsc_pipeline if _zsc_pipeline is not False else None


# ── Public API ────────────────────────────────────────────────────────────────

def extract_keywords(text: str, existing: str = "") -> str:
    """
    Extract keywords from text using KeyBERT.
    Falls back gracefully to existing keywords (from regex) if KeyBERT is unavailable.

    Args:
        text:     Abstract or intro text to extract keywords from.
        existing: Already-detected keywords (from OCR regex). Returned as-is on failure.

    Returns:
        Comma-separated keyword string.
    """
    if not text or len(text.strip()) < 50:
        return existing

    kb = _get_keybert()
    if kb is None:
        return existing

    try:
        # Use MMR (Maximal Marginal Relevance) for diverse, non-redundant keywords
        keyphrases = kb.extract_keywords(
            text[:2000],           # cap to avoid slowness
            keyphrase_ngram_range=(1, 2),
            stop_words="english",
            use_mmr=True,
            diversity=0.5,
            top_n=MAX_KEYWORDS,
        )
        keywords = [phrase for phrase, score in keyphrases if score >= 0.2]
        if keywords:
            result = ", ".join(keywords)
            print(f"[MLService] Keywords: {result}")
            return result
    except Exception as e:
        print(f"[MLService] Keyword extraction error: {e}")

    return existing


def classify_department(title: str, abstract: str, existing: str = "N/A") -> str:
    """
    Use zero-shot NLI to classify the department from title + abstract.
    Falls back to existing (OCR/regex result) if confidence is too low.
    """
    zsc = _get_zsc()
    if zsc is None:
        return existing

    text = f"{title}. {abstract}"[:512]
    try:
        result = zsc(text, candidate_labels=DEPARTMENT_LABELS, multi_label=False)
        top_label: str  = result["labels"][0]
        top_score: float = result["scores"][0]
        print(f"[MLService] Department → '{top_label}' ({top_score:.2f})")
        if top_score >= ZSC_MIN_CONFIDENCE:
            return top_label
    except Exception as e:
        print(f"[MLService] Department classification error: {e}")

    return existing


def classify_degree(title: str, abstract: str, existing: str = "N/A") -> str:
    """
    Use zero-shot NLI to classify the degree program.
    Candidate labels are descriptive phrases; we map the winner back to the code.
    """
    zsc = _get_zsc()
    if zsc is None:
        return existing

    text = f"{title}. {abstract}"[:512]
    try:
        result = zsc(text, candidate_labels=DEGREE_PHRASES, multi_label=False)
        top_idx   = DEGREE_PHRASES.index(result["labels"][0])
        top_score = result["scores"][0]
        top_code  = DEGREE_LABELS[top_idx]
        print(f"[MLService] Degree → '{top_code}' ({top_score:.2f})")
        if top_score >= ZSC_MIN_CONFIDENCE:
            return top_code
    except Exception as e:
        print(f"[MLService] Degree classification error: {e}")

    return existing


def classify_project_type(title: str, abstract: str, existing: str = "Thesis") -> str:
    """
    Use zero-shot NLI to classify Thesis vs Capstone Project.
    """
    zsc = _get_zsc()
    if zsc is None:
        return existing

    text = f"{title}. {abstract}"[:512]
    try:
        result = zsc(text, candidate_labels=PROJECT_TYPE_PHRASES, multi_label=False)
        top_idx   = PROJECT_TYPE_PHRASES.index(result["labels"][0])
        top_score = result["scores"][0]
        top_label = PROJECT_TYPE_LABELS[top_idx]
        print(f"[MLService] Project type → '{top_label}' ({top_score:.2f})")
        if top_score >= ZSC_MIN_CONFIDENCE:
            return top_label
    except Exception as e:
        print(f"[MLService] Project type classification error: {e}")

    return existing


def enhance_metadata(
    title: str,
    abstract: str,
    existing_keywords: str = "",
    existing_department: str = "N/A",
    existing_degree: str = "N/A",
    existing_project_type: str = "Thesis",
) -> dict:
    """
    Run all ML enhancements in one call.
    Safe to call even if models aren't installed — returns existing values on failure.

    Returns dict with keys: keywords, department, degree_program, project_type
    """
    text_for_keywords = abstract or title

    return {
        "keywords":     extract_keywords(text_for_keywords, existing=existing_keywords),
        "department":   classify_department(title, abstract, existing=existing_department),
        "degree_program": classify_degree(title, abstract, existing=existing_degree),
        "project_type": classify_project_type(title, abstract, existing=existing_project_type),
    }