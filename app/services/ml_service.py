from __future__ import annotations
import os
import re
from typing import List, Optional, Dict, Tuple
from app.services.logging_service import log

# ── Config ────────────────────────────────────────────────────────────────────

USE_LIGHTWEIGHT_ZSC: bool = True
KEYBERT_MODEL         = "all-MiniLM-L6-v2"
BART_MODEL            = "facebook/bart-large-mnli"
LIGHTWEIGHT_MODEL     = "cross-encoder/nli-MiniLM2-L6-H768"
CROSS_ENCODER_MODEL   = "cross-encoder/ms-marco-MiniLM-L-6-v2"

ZSC_MODEL = LIGHTWEIGHT_MODEL if USE_LIGHTWEIGHT_ZSC else BART_MODEL

# ── DistilBERT 9-class sequence classifier (Tier 0) ───────────────────────────
# Check for both default and clean folder names
_MODEL_CLEAN = "./distilbert_imrad_model"
_MODEL_STD = "./distilbert_imrad_model"
DISTILBERT_IMRAD_PATH: str  = _MODEL_CLEAN if os.path.isdir(_MODEL_CLEAN) else _MODEL_STD
USE_DISTILBERT_IMRAD:  bool = os.path.isdir(DISTILBERT_IMRAD_PATH)

# Maps the 9-class labels back to the 4 section keys used by imrad_service.py
# Sub-headings resolve to their parent section so downstream code needs no change.
_DISTILBERT_SECTION_MAP: dict = {
    "heading_intro":         "introduction",
    "subheading_intro":      "introduction",
    "heading_methods":       "methods",
    "subheading_methods":    "methods",
    "heading_results":       "results_and_discussion",
    "subheading_results":    "results_and_discussion",
    "heading_discussion":    "results_and_discussion",  # combined R&D section in Filipino theses
    "subheading_discussion": "results_and_discussion",
    "heading_other":         None,   # not an IMRaD section
    "body_text":             None,
    "junk":                  None,
}

# Path to the fine-tuned IMRAD heading model produced by train_imrad_nli.py.
FINETUNED_IMRAD_MODEL_PATH: str  = "./imrad_nli_model"
USE_FINETUNED_IMRAD_MODEL:  bool = os.path.isdir(FINETUNED_IMRAD_MODEL_PATH)

# Path to the custom classifier head produced by train_imrad_nli.py --classifier
CLASSIFIER_HEAD_PATH: str  = "./imrad_nli_model/imrad_classifier_head.pt"
USE_CLASSIFIER_HEAD:  bool = os.path.isfile(CLASSIFIER_HEAD_PATH)

# Confidence thresholds
ZSC_MIN_CONFIDENCE:          float = 0.45

# Threshold for Tier 0 ML. 0.25 is safe for 9 classes as long as it's the top.
IMRAD_MIN_CONFIDENCE:        float = 0.25   # score to record a candidate
IMRAD_EARLY_ACCEPT:          float = 0.50   # score for immediate accept

MAX_KEYWORDS: int = 8

# ── Candidate labels for general classifiers ──────────────────────────────────

DEPARTMENT_LABELS: List[str] = [
    "Department of Computer Science",
    "Department of Information Technology",
]

DEGREE_LABELS: List[str] = ["BSCS", "BSIT"]

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

# ── IMRAD heading hypotheses ──────────────────────────────────────────────────

IMRAD_SECTION_KEYS: List[str] = [
    "introduction", "methods", "results", "results_and_discussion", "discussion",
]

IMRAD_SECTION_HYPOTHESES: Dict[str, str] = {
    "introduction":          "This is a chapter heading for the introduction section of a thesis",
    "methods":               "This is a chapter heading for the research methodology section",
    "results":               "This is a chapter heading for the results and findings section",
    "results_and_discussion": "This is a chapter heading for the combined results and discussion section",
    "discussion":            "This is a chapter heading for the conclusion and recommendations section",
}

# Ordered list used to map pipeline output back to section keys
_IMRAD_HYPOTHESES_LIST: List[str] = [
    IMRAD_SECTION_HYPOTHESES[k] for k in IMRAD_SECTION_KEYS
]


# ── Lazy-loaded singletons ────────────────────────────────────────────────────

_keybert_model        = None
_zsc_pipeline         = None    # general-purpose ZSC (base model)
_imrad_pipeline       = None    # IMRAD-specific ZSC (fine-tuned or base fallback)
_classifier_model     = None    # custom NLI classification head
_distilbert_clf       = None    # DistilBERT 9-class sequence classifier (Tier 0)
_cross_encoder        = None    # cross-encoder for re-ranking


def _get_keybert():
    global _keybert_model
    if _keybert_model is None:
        try:
            from keybert import KeyBERT
            _keybert_model = KeyBERT(model=KEYBERT_MODEL)
            log.ml_load(KEYBERT_MODEL, tier="KeyBERT")
        except Exception as e:
            log.ml_load_fail(KEYBERT_MODEL, e)
            _keybert_model = False
    return _keybert_model if _keybert_model is not False else None


def _get_zsc():
    """General-purpose ZSC — used for department, degree, project-type."""
    global _zsc_pipeline
    if _zsc_pipeline is None:
        try:
            from transformers import pipeline
            _zsc_pipeline = pipeline(
                "zero-shot-classification",
                model=ZSC_MODEL,
                device=-1,
            )
            log.ml_load(ZSC_MODEL, tier="Zero-shot (general)")
        except Exception as e:
            log.ml_load_fail(ZSC_MODEL, e)
            _zsc_pipeline = False
    return _zsc_pipeline if _zsc_pipeline is not False else None


def _get_classifier_model():
    """
    Load the custom 5-class classification head (highest accuracy tier).
    Returns (backbone, classifier_head, tokenizer, label2id, id2label) or None.

    Includes a weight-variance sanity check: a head that failed to train
    has near-uniform output weights (variance ≈ 0) and produces ~0.20 scores
    for every input. We refuse to load such a checkpoint and fall back to NLI.
    This prevents a bad training run from silently breaking all detection.
    """
    global _classifier_model
    if _classifier_model is None:
        if not USE_CLASSIFIER_HEAD:
            _classifier_model = False
        else:
            try:
                import torch
                import torch.nn as nn
                from transformers import AutoTokenizer, AutoModelForSequenceClassification

                ckpt = torch.load(CLASSIFIER_HEAD_PATH, map_location="cpu",
                                  weights_only=False)
                label2id    = ckpt["label2id"]
                id2label    = ckpt["id2label"]
                hidden_size = ckpt["hidden_size"]
                num_classes = len(label2id)

                # ── Sanity check: reject untrained / collapsed checkpoints ─────
                state = ckpt["state_dict"]
                last_weight_key = [k for k in state.keys() if "weight" in k][-1]
                weight_var = state[last_weight_key].float().var().item()
                if weight_var < 1e-3:
                    log.ml_warn("Classifier head appears untrained — falling back to NLI",
                                weight_var=f"{weight_var:.2e}",
                                hint="retrain: python imrad_trainer.py --classifier")
                    _classifier_model = False
                    return None

                # ── Load backbone from NLI checkpoint ─────────────────────────
                tokenizer  = AutoTokenizer.from_pretrained(FINETUNED_IMRAD_MODEL_PATH)
                full_model = AutoModelForSequenceClassification.from_pretrained(
                    FINETUNED_IMRAD_MODEL_PATH, ignore_mismatched_sizes=True,
                )
                if hasattr(full_model, "roberta"):
                    backbone = full_model.roberta
                elif hasattr(full_model, "bert"):
                    backbone = full_model.bert
                elif hasattr(full_model, "distilbert"):
                    backbone = full_model.distilbert
                else:
                    backbone = full_model.base_model
                backbone.eval()

                # ── Build and load classification head ─────────────────────────
                head = nn.Sequential(
                    nn.Dropout(0.1),
                    nn.Linear(hidden_size, hidden_size // 2),
                    nn.GELU(),
                    nn.Dropout(0.1),
                    nn.Linear(hidden_size // 2, num_classes),
                )
                head.load_state_dict(state)
                head.eval()

                # ── Live entropy check ────────────────────────────────────────
                # Run a dummy forward pass. A dead model outputs ~0.20 for all 5
                # classes (max_prob ≈ 0.20-0.22, spread < 0.05). A working model
                # should be notably more confident on a clear heading like "METHODOLOGY".
                import torch.nn.functional as _F
                dummy_enc = tokenizer(
                    "METHODOLOGY", truncation=True, padding="max_length",
                    max_length=128, return_tensors="pt",
                )
                with torch.no_grad():
                    dummy_out    = backbone(**dummy_enc)
                    mask_exp     = dummy_enc["attention_mask"].unsqueeze(-1).float()
                    dummy_pooled = (dummy_out.last_hidden_state * mask_exp).sum(1) / mask_exp.sum(1).clamp(min=1e-9)
                    dummy_logits = head(dummy_pooled)
                    dummy_probs  = _F.softmax(dummy_logits, dim=-1)[0]
                max_prob = dummy_probs.max().item()
                spread   = dummy_probs.max().item() - dummy_probs.min().item()
                if max_prob < 0.30 or spread < 0.05:
                    log.ml_warn("Classifier head outputs near-uniform predictions — falling back to NLI",
                                max_prob=f"{max_prob:.2f}", spread=f"{spread:.2f}",
                                hint="retrain: python imrad_trainer.py --classifier")
                    _classifier_model = False
                    return None

                _classifier_model = (backbone, head, tokenizer, label2id, id2label)
                log.ml_load(
                    CLASSIFIER_HEAD_PATH,
                    tier=f"Tier 1 — custom head  ({num_classes} classes, "
                         f"weight_var={weight_var:.4f}, max_prob={max_prob:.2f})"
                )
            except Exception as e:
                log.error("Classifier head failed to load", exc=e)
                _classifier_model = False

    return _classifier_model if _classifier_model is not False else None


def _get_imrad_pipeline():
    """
    IMRAD heading classifier — three-tier priority:

    Tier 1: Custom classification head (train_imrad_nli.py --classifier)
            Direct 5-class CrossEntropy, scores 0.6–0.95, most accurate.
    Tier 2: Fine-tuned NLI ZSC (train_imrad_nli.py)
            NLI entailment across 5 hypotheses, scores 0.25–0.55.
    Tier 3: Base NLI zero-shot (no training required)
            Weakest but always available as a last resort.
    """
    global _imrad_pipeline
    if _imrad_pipeline is None:
        if USE_FINETUNED_IMRAD_MODEL:
            try:
                from transformers import pipeline
                _imrad_pipeline = pipeline(
                    "zero-shot-classification",
                    model=FINETUNED_IMRAD_MODEL_PATH,
                    device=-1,
                )
                tier = "Tier 1+2" if USE_CLASSIFIER_HEAD else "Tier 2"
                log.ml_load(FINETUNED_IMRAD_MODEL_PATH,
                            tier=f"{tier} — fine-tuned NLI")
            except Exception as e:
                log.ml_load_fail(FINETUNED_IMRAD_MODEL_PATH, e)
                log.warn("Falling back to base NLI (Tier 3)")
                _imrad_pipeline = False

        if _imrad_pipeline is None or _imrad_pipeline is False:
            base = _get_zsc()
            if base is not None:
                _imrad_pipeline = base
                log.ml_load(ZSC_MODEL,
                            tier="Tier 3 — base NLI zero-shot  (run train_imrad_nli.py for better accuracy)")
            else:
                _imrad_pipeline = False

    return _imrad_pipeline if _imrad_pipeline is not False else None


# ── Public API ────────────────────────────────────────────────────────────────

def extract_keywords(text: str, existing: str = "") -> str:
    """
    Extract keywords from text using KeyBERT.
    Falls back to existing keywords on failure.
    """
    if not text or len(text.strip()) < 50:
        return existing

    kb = _get_keybert()
    if kb is None:
        return existing

    try:
        keyphrases = kb.extract_keywords(
            text[:2000],
            keyphrase_ngram_range=(1, 2),
            stop_words="english",
            use_mmr=True,
            diversity=0.5,
            top_n=MAX_KEYWORDS,
        )
        keywords = [phrase for phrase, score in keyphrases if score >= 0.2]
        if keywords:
            log.ml_keywords(keywords)
            return ", ".join(keywords)
    except Exception as e:
        log.error("Keyword extraction failed", exc=e)

    return existing


def classify_department(title: str, abstract: str, existing: str = "N/A") -> str:
    """Zero-shot NLI — classifies department from title + abstract."""
    zsc = _get_zsc()
    if zsc is None:
        return existing

    text = f"{title}. {abstract}"[:512]
    try:
        result     = zsc(text, candidate_labels=DEPARTMENT_LABELS, multi_label=False)
        top_label  = result["labels"][0]
        top_score  = result["scores"][0]
        if top_score >= ZSC_MIN_CONFIDENCE:
            log.ml_classify("Department", top_label, top_score)
            return top_label
        log.ml_warn("Department score below threshold — keeping existing",
                    score=f"{top_score:.2f}", label=top_label)
    except Exception as e:
        log.error("Department classification failed", exc=e)

    return existing


def classify_degree(title: str, abstract: str, existing: str = "N/A") -> str:
    """Zero-shot NLI — classifies degree program."""
    zsc = _get_zsc()
    if zsc is None:
        return existing

    text = f"{title}. {abstract}"[:512]
    try:
        result    = zsc(text, candidate_labels=DEGREE_PHRASES, multi_label=False)
        top_idx   = DEGREE_PHRASES.index(result["labels"][0])
        top_score = result["scores"][0]
        top_code  = DEGREE_LABELS[top_idx]
        if top_score >= ZSC_MIN_CONFIDENCE:
            log.ml_classify("Degree program", top_code, top_score)
            return top_code
        log.ml_warn("Degree score below threshold — keeping existing",
                    score=f"{top_score:.2f}", label=top_code)
    except Exception as e:
        log.error("Degree classification failed", exc=e)

    return existing


def classify_project_type(title: str, abstract: str, existing: str = "Thesis") -> str:
    """Zero-shot NLI — classifies Thesis vs Capstone Project."""
    zsc = _get_zsc()
    if zsc is None:
        return existing

    text = f"{title}. {abstract}"[:512]
    try:
        result    = zsc(text, candidate_labels=PROJECT_TYPE_PHRASES, multi_label=False)
        top_idx   = PROJECT_TYPE_PHRASES.index(result["labels"][0])
        top_score = result["scores"][0]
        top_label = PROJECT_TYPE_LABELS[top_idx]
        if top_score >= ZSC_MIN_CONFIDENCE:
            log.ml_classify("Project type", top_label, top_score)
            return top_label
        log.ml_warn("Project type score below threshold — keeping existing",
                    score=f"{top_score:.2f}", label=top_label)
    except Exception as e:
        log.error("Project type classification failed", exc=e)

    return existing


def classify_heading(heading_text: str) -> Tuple[Optional[str], float]:
    """
    Classify a raw heading line into one of the five IMRAD section keys:
    introduction, methods, results, results_and_discussion, discussion.

    Three-tier system (highest to lowest accuracy):
      Tier 1: Custom classification head (if imrad_classifier_head.pt exists)
      Tier 2: Fine-tuned NLI ZSC (if imrad_nli_model/ exists)
      Tier 3: Base NLI zero-shot (always available)

    Returns:
        (section_key, confidence)
        Returns (None, 0.0) if all tiers are unavailable.
    """
    if not heading_text or len(heading_text.strip()) < 2:
        return None, 0.0

    text = heading_text.strip()

    # ── Tier 0: DistilBERT 9-class sequence classifier (highest accuracy) ────
    if USE_DISTILBERT_IMRAD:
        global _distilbert_clf
        if _distilbert_clf is None:
            try:
                from transformers import pipeline as hf_pipeline
                _distilbert_clf = hf_pipeline(
                    "text-classification",
                    model=DISTILBERT_IMRAD_PATH,
                    tokenizer=DISTILBERT_IMRAD_PATH,
                    device=-1,          # CPU — safe on Ryzen 7
                    truncation=True,
                    max_length=128,
                )
                log.ml_load(DISTILBERT_IMRAD_PATH, tier="Tier 0 — DistilBERT 9-class")
            except Exception as e:
                log.ml_load_fail(DISTILBERT_IMRAD_PATH, e)
                _distilbert_clf = False

        if _distilbert_clf and _distilbert_clf is not False:
            try:
                result      = _distilbert_clf(text[:512])[0]
                raw_label   = result["label"]   # e.g. "heading_methods"
                score       = result["score"]
                section_key = _DISTILBERT_SECTION_MAP.get(raw_label)  # map to section key

                log.ml_classify(
                    f"Verdict — '{text[:45]}'",
                    f"{raw_label} → {section_key}",
                    score,
                    tier="Tier 0 — DistilBERT",
                )

                if section_key is not None and score >= IMRAD_MIN_CONFIDENCE:
                    return section_key, score
                # heading_other / body_text / junk → not a heading
                if section_key is None:
                    return None, score
            except Exception as e:
                log.error("DistilBERT inference failed", exc=e)

    # ── Tier 1: Custom NLI classification head ────────────────────────────────
    clf = _get_classifier_model()
    if clf is not None:
        try:
            import torch
            import torch.nn.functional as F
            backbone, head, tokenizer, label2id, id2label = clf

            enc = tokenizer(
                text, truncation=True, padding="max_length",
                max_length=128, return_tensors="pt",
            )
            with torch.no_grad():
                out = backbone(**enc)
                token_emb    = out.last_hidden_state
                mask_exp     = enc["attention_mask"].unsqueeze(-1).float()
                pooled       = (token_emb * mask_exp).sum(1) / mask_exp.sum(1).clamp(min=1e-9)
                logits       = head(pooled)
                probs        = F.softmax(logits, dim=-1)[0]

            top_idx     = probs.argmax().item()
            top_score   = probs[top_idx].item()
            section_key = id2label[top_idx]
            log.ml_classify(f"Verdict — '{text[:45]}'", section_key, top_score,
                            tier="Tier 1 — custom NLI head")
            return section_key, top_score
        except Exception as e:
            log.error("Classifier head inference failed", exc=e)

    # ── Tier 2/3: NLI pipeline ────────────────────────────────────────────────
    pipe = _get_imrad_pipeline()
    if pipe is None:
        return None, 0.0

    try:
        result = pipe(
            text,
            candidate_labels=_IMRAD_HYPOTHESES_LIST,
            multi_label=False,
        )
        top_hypothesis = result["labels"][0]
        top_score      = result["scores"][0]
        top_idx        = _IMRAD_HYPOTHESES_LIST.index(top_hypothesis)
        section_key    = IMRAD_SECTION_KEYS[top_idx]

        tier_label = "Tier 2 — fine-tuned NLI" if USE_FINETUNED_IMRAD_MODEL else "Tier 3 — base NLI"
        log.ml_classify(f"Verdict — '{text[:45]}'", section_key, top_score,
                        tier=tier_label)
        return section_key, top_score

    except Exception as e:
        log.error("Heading classification failed", exc=e)
        return None, 0.0


def enhance_metadata(
    title: str,
    abstract: str,
    existing_keywords:     str = "",
    existing_department:   str = "N/A",
    existing_degree:       str = "N/A",
    existing_project_type: str = "Thesis",
) -> dict:
    """
    Run all ML enhancements in one call.
    Safe to call even if models aren't installed — returns existing values on failure.

    Returns dict with keys: keywords, department, degree_program, project_type
    """
    return {
        "keywords":       extract_keywords(abstract or title, existing=existing_keywords),
        "department":     classify_department(title, abstract, existing=existing_department),
        "degree_program": classify_degree(title, abstract, existing=existing_degree),
        "project_type":   classify_project_type(title, abstract, existing=existing_project_type),
    }


# ── Query Expansion ───────────────────────────────────────────────────────────────────────────

def expand_query(query: str) -> str:
    """
    Expand a short search query with semantically related keyphrases.

    For queries with fewer than 4 words, KeyBERT extracts 3 related phrases
    from the query itself so the embedding captures richer semantics.  For
    longer queries the original text is returned unchanged to avoid noise.

    Examples:
        "CNN images"   →  "CNN images convolutional neural network image classification"
        "SDLC agile"   →  "SDLC agile software development lifecycle iterative"
    """
    if not query or not query.strip():
        return query
    if len(query.split()) >= 4:
        return query   # long enough — skip expansion

    kb = _get_keybert()
    if kb is None:
        return query

    try:
        expansions = kb.extract_keywords(
            query,
            keyphrase_ngram_range=(1, 2),
            stop_words="english",
            top_n=3,
        )
        extra_terms = " ".join(
            phrase for phrase, score in expansions
            if score >= 0.25 and phrase.lower() not in query.lower()
        )
        expanded = f"{query} {extra_terms}".strip()
        if expanded != query:
            log.info("[QueryExpand] Expanded query",
                     original=query, expanded=expanded)
        return expanded
    except Exception as e:
        log.error("Query expansion failed", exc=e)
        return query


# ── Cross-Encoder Re-ranking ─────────────────────────────────────────────────────────────

def _get_cross_encoder():
    """Lazy-load the cross-encoder model (CPU, ~80 MB)."""
    global _cross_encoder
    if _cross_encoder is None:
        try:
            from sentence_transformers import CrossEncoder
            _cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL, device="cpu")
            log.ml_load(CROSS_ENCODER_MODEL, tier="Cross-Encoder re-ranker")
        except Exception as e:
            log.ml_load_fail(CROSS_ENCODER_MODEL, e)
            _cross_encoder = False
    return _cross_encoder if _cross_encoder is not False else None


def rerank_with_cross_encoder(
    query: str,
    candidates: List[Dict],
    top_k: int = 10,
) -> List[Dict]:
    """
    Re-rank a list of search-result dicts using a cross-encoder.

    Each candidate must have a 'text' key (the text to score against the query)
    and a 'score' key (the original vector score, used as fallback).

    The cross-encoder reads the query and each document *jointly*, which is
    far more accurate than cosine similarity for small corpora where scores
    cluster tightly.

    Args:
        query:      The raw user search query.
        candidates: List of dicts, each with at least {'text': str, 'score': float, ...}
        top_k:      How many results to return after re-ranking.

    Returns:
        The same list of dicts, sorted by cross-encoder score descending,
        truncated to top_k.  Each dict gains a 'rerank_score' key.
    """
    if not candidates or not query:
        return candidates[:top_k]

    ce = _get_cross_encoder()
    if ce is None:
        log.warn("[Rerank] Cross-encoder unavailable — skipping re-rank")
        return candidates[:top_k]

    try:
        pairs = [(query, c["text"]) for c in candidates]
        scores = ce.predict(pairs)
        for c, s in zip(candidates, scores):
            c["rerank_score"] = float(s)
        reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
        log.info("[Rerank] Cross-encoder re-ranked candidates",
                 total=str(len(candidates)), top_k=str(top_k))
        return reranked[:top_k]
    except Exception as e:
        log.error("Cross-encoder re-ranking failed", exc=e)
        return candidates[:top_k]