"""
ml_service.py
─────────────
Local ML enhancements for OCR metadata extraction. Zero API cost.
Uses HuggingFace transformers + KeyBERT — all run offline.

Provides:
  1. keyword_extraction    — KeyBERT extracts meaningful keywords from abstract/text
  2. classify_department   — zero-shot NLI classifies department from title+abstract
  3. classify_degree       — zero-shot NLI classifies degree program
  4. classify_project_type — zero-shot NLI: Thesis vs Capstone
  5. classify_heading      — fine-tuned NLI classifies IMRAD section from a heading line
                             Falls back to base zero-shot NLI if fine-tuned model is absent.

Models used:
  - all-MiniLM-L6-v2              (KeyBERT / sentence-transformers) ~90 MB
  - cross-encoder/nli-MiniLM2-L6-H768  (zero-shot ZSC, base)       ~90 MB
  - ./imrad_nli_model/            (fine-tuned IMRAD classifier)     ~90 MB
      → produced by train_imrad_nli.py; same architecture, domain-adapted weights

Install:
    pip install keybert sentence-transformers transformers torch
"""

from __future__ import annotations
import os
import re
from typing import List, Optional, Dict, Tuple

# ── Config ────────────────────────────────────────────────────────────────────

USE_LIGHTWEIGHT_ZSC: bool = True
KEYBERT_MODEL         = "all-MiniLM-L6-v2"
BART_MODEL            = "facebook/bart-large-mnli"
LIGHTWEIGHT_MODEL     = "cross-encoder/nli-MiniLM2-L6-H768"

ZSC_MODEL = LIGHTWEIGHT_MODEL if USE_LIGHTWEIGHT_ZSC else BART_MODEL

# Path to the fine-tuned IMRAD heading model produced by train_imrad_nli.py.
FINETUNED_IMRAD_MODEL_PATH: str  = "./imrad_nli_model"
USE_FINETUNED_IMRAD_MODEL:  bool = os.path.isdir(FINETUNED_IMRAD_MODEL_PATH)

# Path to the custom classifier head produced by train_imrad_nli.py --classifier
# When present, this replaces the NLI zero-shot approach with a dedicated
# 5-class classification head — higher confidence scores, cleaner predictions.
CLASSIFIER_HEAD_PATH: str  = "./imrad_nli_model/imrad_classifier_head.pt"
USE_CLASSIFIER_HEAD:  bool = os.path.isfile(CLASSIFIER_HEAD_PATH)

# Confidence thresholds
ZSC_MIN_CONFIDENCE:          float = 0.45
# IMRAD thresholds apply to the COMBINED score (ml*0.6 + rx*0.4).
# With 5 labels the model spreads probability more — top scores of 0.25-0.50
# are expected. The regex validation guard ensures ML picks with rx=0.0 are
# always rejected, so a lower IMRAD_MIN_CONFIDENCE is safe.
IMRAD_MIN_CONFIDENCE:        float = 0.28   # combined score to record a candidate
IMRAD_EARLY_ACCEPT:          float = 0.50   # combined score for immediate accept

MAX_KEYWORDS: int = 8

# ── Candidate labels for general classifiers ──────────────────────────────────

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

DEGREE_LABELS: List[str] = ["BSCS", "BSIT", "BSIS", "BSCpE"]

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
# These must exactly match the hypotheses used in train_imrad_nli.py.
# IMPORTANT: "results_and_discussion" is a 5th label — many Filipino theses
# combine Results and Discussion into one chapter. The service detects this
# combined heading first, then falls back to separate results/discussion.
#
# Introduction hypothesis was broadened from "problem statement" to cover
# standalone "INTRODUCTION" headings that don't reference the problem —
# the old narrow hypothesis caused the model to misclassify them as discussion.

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

_keybert_model      = None
_zsc_pipeline       = None    # general-purpose ZSC (base model)
_imrad_pipeline     = None    # IMRAD-specific ZSC (fine-tuned or base fallback)
_classifier_model   = None    # custom classification head (highest accuracy tier)


def _get_keybert():
    global _keybert_model
    if _keybert_model is None:
        try:
            from keybert import KeyBERT
            _keybert_model = KeyBERT(model=KEYBERT_MODEL)
            print(f"[MLService] KeyBERT loaded ({KEYBERT_MODEL})")
        except Exception as e:
            print(f"[MLService] KeyBERT unavailable: {e}")
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
            print(f"[MLService] General ZSC loaded ({ZSC_MODEL})")
        except Exception as e:
            print(f"[MLService] General ZSC unavailable: {e}")
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
                # A properly trained head has output weights with meaningful spread.
                # Thresholds (empirically calibrated):
                #   weight_var < 1e-3  → weights nearly uniform, model did not learn
                #   weight_var = 0.0009 was observed from a bad training run that
                #     oscillated acc 0.44→0.22→0.22→0.55 — still essentially random.
                # We also run a quick forward pass on a dummy input and check that
                # the predicted class probability spread is > 0.05, meaning the model
                # actually picks a winner rather than assigning ~0.20 to every class.
                state = ckpt["state_dict"]
                last_weight_key = [k for k in state.keys() if "weight" in k][-1]
                weight_var = state[last_weight_key].float().var().item()
                if weight_var < 1e-3:
                    print(f"[MLService] ⚠️  Classifier head appears untrained "
                          f"(weight_var={weight_var:.2e} < 1e-3). "
                          f"Falling back to NLI. Retrain: python imrad_trainer.py --classifier")
                    _classifier_model = False
                    return None

                # ── Load backbone from NLI checkpoint ─────────────────────────
                # Must use AutoModelForSequenceClassification (not AutoModel) to
                # get the properly initialized pooler. Extract base encoder only.
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
                    print(f"[MLService] ⚠️  Classifier head outputs near-uniform predictions "
                          f"(max_prob={max_prob:.2f}, spread={spread:.2f}). "
                          f"Model did not train properly. Falling back to NLI. "
                          f"Retrain: python imrad_trainer.py --classifier")
                    _classifier_model = False
                    return None

                _classifier_model = (backbone, head, tokenizer, label2id, id2label)
                print(f"[MLService] IMRAD classifier head loaded "
                      f"({num_classes} classes: {list(label2id.keys())}, "
                      f"weight_var={weight_var:.4f}, max_prob={max_prob:.2f})")
            except Exception as e:
                print(f"[MLService] Classifier head failed to load: {e}")
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
                print(f"[MLService] IMRAD NLI pipeline loaded ({tier}, "
                      f"{FINETUNED_IMRAD_MODEL_PATH})")
            except Exception as e:
                print(f"[MLService] Fine-tuned model failed: {e}. Falling back to base NLI.")
                _imrad_pipeline = False

        if _imrad_pipeline is None or _imrad_pipeline is False:
            base = _get_zsc()
            if base is not None:
                _imrad_pipeline = base
                print("[MLService] IMRAD using base NLI (Tier 3). "
                      "Run train_imrad_nli.py for better accuracy.")
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
            result = ", ".join(keywords)
            print(f"[MLService] Keywords: {result}")
            return result
    except Exception as e:
        print(f"[MLService] Keyword extraction error: {e}")

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
        print(f"[MLService] Department → '{top_label}' ({top_score:.2f})")
        if top_score >= ZSC_MIN_CONFIDENCE:
            return top_label
    except Exception as e:
        print(f"[MLService] Department classification error: {e}")

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
        print(f"[MLService] Degree → '{top_code}' ({top_score:.2f})")
        if top_score >= ZSC_MIN_CONFIDENCE:
            return top_code
    except Exception as e:
        print(f"[MLService] Degree classification error: {e}")

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
        print(f"[MLService] Project type → '{top_label}' ({top_score:.2f})")
        if top_score >= ZSC_MIN_CONFIDENCE:
            return top_label
    except Exception as e:
        print(f"[MLService] Project type classification error: {e}")

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

    # ── Tier 1: Custom classification head ───────────────────────────────────
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
                # Mean pooling (matches training in train_imrad_nli.py)
                token_emb    = out.last_hidden_state
                mask_exp     = enc["attention_mask"].unsqueeze(-1).float()
                pooled       = (token_emb * mask_exp).sum(1) / mask_exp.sum(1).clamp(min=1e-9)
                logits       = head(pooled)
                probs        = F.softmax(logits, dim=-1)[0]

            top_idx     = probs.argmax().item()
            top_score   = probs[top_idx].item()
            section_key = id2label[top_idx]
            print(f"[MLService][clf] '{text[:50]}' → '{section_key}' ({top_score:.2f})")
            return section_key, top_score
        except Exception as e:
            print(f"[MLService] Classifier head inference error: {e}")

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

        tag = "ft" if USE_FINETUNED_IMRAD_MODEL else "zs"
        print(f"[MLService][{tag}] '{text[:50]}' → '{section_key}' ({top_score:.2f})")
        return section_key, top_score

    except Exception as e:
        print(f"[MLService] Heading classification error: {e}")
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