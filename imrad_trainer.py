"""
train_imrad_nli.py
──────────────────
Fine-tunes the pretrained NLI model (cross-encoder/nli-MiniLM2-L6-H768)
on a labeled dataset of thesis section headings specific to CvSU / Filipino
undergraduate thesis documents.

HOW IT WORKS
────────────
NLI (Natural Language Inference) models score whether a premise *entails*
a hypothesis. We reframe IMRAD heading classification as:

  premise   → the raw heading text, e.g. "CHAPTER III"
  hypothesis → a descriptive label,  e.g. "This is a methodology section"

For every labeled heading we generate:
  • 1 positive pair  (correct section)   → label = entailment   (2)
  • 3 negative pairs (wrong sections)    → label = contradiction (0)

This gives us 4× the rows from a single CSV entry, which is important
because you only need ~150–300 real heading examples to get good results.

USAGE
─────
1.  Prepare data/imrad_headings.csv  (see format below)
2.  pip install transformers torch datasets scikit-learn
3.  python train_imrad_nli.py
4.  Trained model saved to  ./imrad_nli_model/

CSV FORMAT  (data/imrad_headings.csv)
──────────────────────────────────────
heading_text,section
CHAPTER I,introduction
CHAPTER ONE,introduction
INTRODUCTION,introduction
THE PROBLEM AND ITS BACKGROUND,introduction
BACKGROUND OF THE STUDY,introduction
CHAPTER II,introduction
REVIEW OF RELATED LITERATURE,introduction
CHAPTER III,methods
RESEARCH METHODOLOGY,methods
METHOD OF RESEARCH,methods
RESEARCH DESIGN AND METHODOLOGY,methods
MATERIALS AND METHODS,methods
CHAPTER IV,results
PRESENTATION OF DATA,results
FINDINGS,results
DATA ANALYSIS AND INTERPRETATION,results
RESULTS AND DISCUSSION,results
CHAPTER V,discussion
CONCLUSIONS AND RECOMMENDATIONS,discussion
SUMMARY AND CONCLUSIONS,discussion
SUMMARY CONCLUSIONS AND RECOMMENDATIONS,discussion

(Add more rows — aim for 40–80 per section class from your actual theses.)
"""

from __future__ import annotations
import re

import os
import csv
import json
import random
from pathlib import Path
from typing import List, Dict, Tuple

# ── Config ────────────────────────────────────────────────────────────────────

BASE_MODEL   = "cross-encoder/nli-MiniLM2-L6-H768"
OUTPUT_DIR   = "./imrad_nli_model"
DATA_PATH    = "./data/imrad_headings.csv"

EPOCHS       = 4
BATCH_SIZE   = 16
LEARNING_RATE = 2e-5
MAX_LENGTH   = 128      # tokens; headings are short, this is plenty
TEST_SPLIT   = 0.15     # fraction held out for evaluation
SEED         = 42

# Descriptive hypothesis templates — must match IMRAD_SECTION_HYPOTHESES in
# ml_service.py exactly. Five sections: introduction, methods, results,
# results_and_discussion (combined), discussion.
#
# Hypotheses are phrased as "This is a chapter heading for X" — simpler and
# more discriminative than longer descriptions. The model must learn from
# context what each section heading looks like, not from paragraph definitions.
SECTION_HYPOTHESES: Dict[str, str] = {
    "introduction":          "This is a chapter heading for the introduction section of a thesis",
    "methods":               "This is a chapter heading for the research methodology section",
    "results":               "This is a chapter heading for the results and findings section",
    "results_and_discussion": "This is a chapter heading for the combined results and discussion section",
    "discussion":            "This is a chapter heading for the conclusion and recommendations section",
}

ALL_SECTIONS = list(SECTION_HYPOTHESES.keys())

# NLI label mapping used by cross-encoder/nli-MiniLM2-L6-H768
# The model's config maps:  contradiction=0, entailment=2, neutral=1
# We only use contradiction (0) and entailment (2) for our pairs.
NLI_CONTRADICTION = 0
NLI_ENTAILMENT    = 2

# ── Hard negatives ─────────────────────────────────────────────────────────────
# Lines from real documents that the model incorrectly accepted as section
# headings. Each is contradiction against ALL five hypotheses — the model
# learns these are NOT valid IMRAD chapter headings of any kind.
#
# Rule: only add lines that are genuinely confusing and not chapter headings.
# Do NOT add sub-headings like "Research Design" here — those are valid
# heading-shaped lines and rejecting them as hard negatives confuses the model.

HARD_NEGATIVE_LINES: List[str] = [
    # Table / figure labels that mention method-sounding words
    "Methodology BERT &",
    "Methodology BERT",
    "Table of Comparison for Foreign Studies",
    "Table of Comparison for Local Studies",
    "Table of Comparison",
    "Citation Count",
    "on Mechanism",
    "n Mechanism",
    "PRRSUB",
    "BERT-NLP",
    # Reference / journal fragments that sound academic but are citations
    "Selected Philippine Academic Library Websites. Qualitative and Quantitative",
    "of Advanced Information Systems Research",
    "Processing in Information Retrieval Systems",
    # Chapter II area — these are NOT chapter headings, they are sub-sections
    # of the literature review chapter and should not trigger IMRAD detection
    "Review of Related Literature",
    "Review of Related Studies",
    "Related Literature and Studies",
    "Foreign Literature",
    "Local Literature",
    "Foreign Studies",
    "Local Studies",
    "Research Gap",
    # Introduction sub-sections — these appear inside Chapter I body text,
    # they are not the chapter heading itself
    "Significance of the Study",
    "Statement of the Problem",
    "Objectives of the Study",
    "Definition of Terms",
    "Conceptual Framework",
    "Theoretical Framework",
    "Scope and Limitation of the Study",
    "Time and Place of the Study",
]


# ── Data helpers ──────────────────────────────────────────────────────────────

# Headings that indicate a combined Results+Discussion chapter.
# Used to auto-migrate old CSV rows that were labeled "results" before
# results_and_discussion was added as a first-class label.
_RAD_MIGRATION_PATTERNS = re.compile(
    r'(results\s+and\s+discussions?|'
    r'analysis\s+and\s+interpretation\s+of\s+data|'
    r'presentation,?\s+analysis\s+and\s+interpretation\s+of\s+data)',
    re.IGNORECASE,
)


def load_csv(path: str) -> List[Dict[str, str]]:
    """
    Load heading → section CSV. Returns list of {heading_text, section} dicts.

    Auto-migrates legacy rows: headings that match combined RAD patterns but
    are labeled as plain "results" are corrected to "results_and_discussion"
    so old CSV files work correctly without manual re-editing.
    """
    rows = []
    migrated = 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            heading = row.get("heading_text", "").strip()
            section = row.get("section", "").strip().lower()
            if not heading:
                continue
            # Auto-migrate: if labeled "results" but heading is clearly combined RAD
            if section == "results" and _RAD_MIGRATION_PATTERNS.search(heading):
                section = "results_and_discussion"
                migrated += 1
            if section in ALL_SECTIONS:
                rows.append({"heading_text": heading, "section": section})
    if migrated:
        print(f"[Train] Auto-migrated {migrated} rows from 'results' → 'results_and_discussion'")
    print(f"[Train] Loaded {len(rows)} heading rows from {path}")
    return rows


def build_nli_pairs(
    rows: List[Dict[str, str]],
) -> List[Dict]:
    """
    Convert labeled headings into NLI premise-hypothesis pairs.

    For each positive heading row:
      - 1 entailment   pair with the correct section hypothesis
      - 3 contradiction pairs with the other three section hypotheses

    For each hard negative line (HARD_NEGATIVE_LINES):
      - 4 contradiction pairs — one against every section hypothesis
      These teach the model that table labels, sub-headings, reference lines,
      and similar fragments are NOT valid IMRAD section headings.

    Returns list of {premise, hypothesis, label} dicts.
    """
    pairs = []

    # Positive heading rows
    for row in rows:
        heading = row["heading_text"]
        true_section = row["section"]
        for section, hypothesis in SECTION_HYPOTHESES.items():
            label = NLI_ENTAILMENT if section == true_section else NLI_CONTRADICTION
            pairs.append({
                "premise":    heading,
                "hypothesis": hypothesis,
                "label":      label,
            })

    # Hard negative lines — contradiction against every hypothesis
    for neg_line in HARD_NEGATIVE_LINES:
        for hypothesis in SECTION_HYPOTHESES.values():
            pairs.append({
                "premise":    neg_line,
                "hypothesis": hypothesis,
                "label":      NLI_CONTRADICTION,
            })

    random.seed(SEED)
    random.shuffle(pairs)
    n_entail = sum(1 for p in pairs if p["label"] == NLI_ENTAILMENT)
    n_contra = sum(1 for p in pairs if p["label"] == NLI_CONTRADICTION)
    print(f"[Train] Built {len(pairs)} NLI pairs "
          f"({n_entail} entailment, {n_contra} contradiction, "
          f"{len(HARD_NEGATIVE_LINES)} hard-negative lines × 4)")
    return pairs


def split_pairs(
    pairs: List[Dict],
    test_frac: float = TEST_SPLIT,
) -> Tuple[List[Dict], List[Dict]]:
    n_test = max(1, int(len(pairs) * test_frac))
    return pairs[n_test:], pairs[:n_test]   # train, test


# ── Dataset class ─────────────────────────────────────────────────────────────

def build_dataset(pairs: List[Dict], tokenizer, max_length: int = MAX_LENGTH):
    """
    Tokenise premise-hypothesis pairs and return a HuggingFace Dataset.
    The cross-encoder expects them concatenated with [SEP].
    """
    import torch
    from torch.utils.data import Dataset as TorchDataset

    class NLIDataset(TorchDataset):
        def __init__(self, pairs, tokenizer, max_length):
            self.encodings = tokenizer(
                [p["premise"]    for p in pairs],
                [p["hypothesis"] for p in pairs],
                truncation=True,
                padding="max_length",
                max_length=max_length,
                return_tensors="pt",
            )
            self.labels = torch.tensor([p["label"] for p in pairs], dtype=torch.long)

        def __len__(self):
            return len(self.labels)

        def __getitem__(self, idx):
            return {
                "input_ids":      self.encodings["input_ids"][idx],
                "attention_mask": self.encodings["attention_mask"][idx],
                "labels":         self.labels[idx],
            }

    return NLIDataset(pairs, tokenizer, max_length)


# ── Training ──────────────────────────────────────────────────────────────────

def train():
    try:
        from transformers import (
            AutoTokenizer,
            AutoModelForSequenceClassification,
            TrainingArguments,
            Trainer,
        )
        import torch
        from sklearn.metrics import accuracy_score, f1_score
        import numpy as np
    except ImportError as e:
        print(f"\n[Train] Missing dependency: {e}")
        print("[Train] Install with:  pip install transformers torch datasets scikit-learn")
        return

    # ── Validate data file ────────────────────────────────────────────────────
    data_path = Path(DATA_PATH)
    if not data_path.exists():
        print(f"\n[Train] Data file not found: {DATA_PATH}")
        print("[Train] Create data/imrad_headings.csv with columns: heading_text,section")
        print("[Train] See the docstring at the top of this file for the CSV format.")
        _write_seed_csv(data_path)
        print(f"[Train] A seed CSV with built-in examples has been written to {DATA_PATH}")
        print("[Train] Add your own thesis headings to that file, then re-run.")
        return

    rows = load_csv(str(data_path))
    if len(rows) < 20:
        print(f"[Train] Only {len(rows)} rows found — need at least 20 to train. "
              "Add more headings to the CSV.")
        return

    pairs = build_nli_pairs(rows)
    train_pairs, test_pairs = split_pairs(pairs)
    print(f"[Train] Train: {len(train_pairs)} pairs | Test: {len(test_pairs)} pairs")

    # ── Load base model ───────────────────────────────────────────────────────
    print(f"[Train] Loading base model: {BASE_MODEL}")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model     = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        ignore_mismatched_sizes=True,
    )

    train_dataset = build_dataset(train_pairs, tokenizer)
    test_dataset  = build_dataset(test_pairs,  tokenizer)

    # ── Training args ─────────────────────────────────────────────────────────
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[Train] Training on: {device.upper()}")

    # Detect transformers version to handle renamed arguments (4.41+ breaking change)
    import transformers as _tf_ver
    _tf_major, _tf_minor = [int(x) for x in _tf_ver.__version__.split(".")[:2]]
    _use_new_api = (_tf_major, _tf_minor) >= (4, 41)

    _eval_kwarg = {"eval_strategy": "epoch"} if _use_new_api else {"evaluation_strategy": "epoch"}

    args = TrainingArguments(
        output_dir                  = OUTPUT_DIR,
        num_train_epochs            = EPOCHS,
        per_device_train_batch_size = BATCH_SIZE,
        per_device_eval_batch_size  = BATCH_SIZE,
        learning_rate               = LEARNING_RATE,
        weight_decay                = 0.01,
        warmup_ratio                = 0.1,
        save_strategy               = "epoch",
        load_best_model_at_end      = True,
        metric_for_best_model       = "f1",
        greater_is_better           = True,
        logging_steps               = 10,
        seed                        = SEED,
        fp16                        = torch.cuda.is_available(),
        report_to                   = "none",
        **_eval_kwarg,
    )

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        return {
            "accuracy": accuracy_score(labels, preds),
            "f1":       f1_score(labels, preds, average="weighted"),
        }

    trainer = Trainer(
        model           = model,
        args            = args,
        train_dataset   = train_dataset,
        eval_dataset    = test_dataset,
        compute_metrics = compute_metrics,
    )

    print(f"\n[Train] Starting fine-tuning for {EPOCHS} epochs …")
    trainer.train()

    # ── Save ──────────────────────────────────────────────────────────────────
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    # Save metadata so ml_service.py can verify model origin
    meta = {
        "base_model":          BASE_MODEL,
        "fine_tuned_for":      "IMRAD heading classification",
        "section_hypotheses":  SECTION_HYPOTHESES,
        "training_rows":       len(rows),
        "training_pairs":      len(train_pairs),
        "epochs":              EPOCHS,
    }
    with open(os.path.join(OUTPUT_DIR, "imrad_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n[Train] Model saved to {OUTPUT_DIR}/")
    print("[Train] Update ml_service.py: set USE_FINETUNED_IMRAD_MODEL = True")

    # ── Quick sanity check ────────────────────────────────────────────────────
    print("\n[Train] Sanity check on held-out headings:")
    _run_sanity_check(OUTPUT_DIR, tokenizer)


def _run_sanity_check(model_dir: str, tokenizer):
    """Quick inference test on a handful of known headings."""
    from transformers import pipeline

    zsc = pipeline("zero-shot-classification", model=model_dir, device=-1)
    test_cases = [
        # Introduction — both standalone and chapter-prefixed
        ("INTRODUCTION",                                 "introduction"),
        ("CHAPTER I",                                    "introduction"),
        ("THE PROBLEM AND ITS BACKGROUND",               "introduction"),
        # Methods
        ("METHODOLOGY",                                  "methods"),
        ("CHAPTER III",                                  "methods"),
        ("PAMAMARAAN NG PANANALIKSIK",                   "methods"),
        # Results (standalone)
        ("PRESENTATION OF DATA",                         "results"),
        ("FINDINGS",                                     "results"),
        # Combined RAD — the most common Filipino thesis format
        ("RESULTS AND DISCUSSION",                       "results_and_discussion"),
        ("CHAPTER IV",                                   "results_and_discussion"),
        # Discussion / Conclusion
        ("CONCLUSIONS AND RECOMMENDATIONS",              "discussion"),
        ("CHAPTER V",                                    "discussion"),
        ("SUMMARY CONCLUSIONS AND RECOMMENDATIONS",      "discussion"),
        # Hard negatives — should NOT match any section
        ("Methodology BERT &",                           None),
        ("Background of the Study",                      None),
    ]
    hypotheses = list(SECTION_HYPOTHESES.values())
    section_keys = list(SECTION_HYPOTHESES.keys())

    print(f"  {'Heading':<45} {'Expected':<14} {'Predicted':<14} {'Score'}")
    print(f"  {'─'*45} {'─'*14} {'─'*14} {'─'*6}")
    correct = 0
    total   = 0
    for heading, expected in test_cases:
        result = zsc(heading, candidate_labels=hypotheses, multi_label=False)
        top_idx   = hypotheses.index(result["labels"][0])
        predicted = section_keys[top_idx]
        score     = result["scores"][0]
        if expected is None:
            # Hard negative: model should not be very confident
            ok = "✓" if score < 0.40 else "✗ (overconfident)"
            is_correct = score < 0.40
            exp_str = "none (neg)"
        else:
            ok = "✓" if predicted == expected else "✗"
            is_correct = predicted == expected
            exp_str = expected
        if is_correct:
            correct += 1
        total += 1
        print(f"  {heading:<45} {exp_str:<20} {predicted:<20} {score:.2f} {ok}")
    print(f"\n  {correct}/{total} correct on sanity set")


def _write_seed_csv(path: Path):
    """
    Write a starter CSV with the built-in keyword headings so the user has
    something to work from immediately.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    seed_rows = [
        # introduction
        ("CHAPTER I",                                    "introduction"),
        ("CHAPTER ONE",                                  "introduction"),
        ("CHAPTER 1",                                    "introduction"),
        ("INTRODUCTION",                                 "introduction"),
        ("I. INTRODUCTION",                              "introduction"),
        ("1. INTRODUCTION",                              "introduction"),
        ("THE PROBLEM AND ITS BACKGROUND",               "introduction"),
        ("THE PROBLEM AND ITS SETTING",                  "introduction"),
        ("PROBLEM AND ITS BACKGROUND",                   "introduction"),
        ("BACKGROUND OF THE STUDY",                      "introduction"),
        ("INTRODUCTION AND BACKGROUND",                  "introduction"),
        # methods
        ("CHAPTER III",                                  "methods"),
        ("CHAPTER THREE",                                "methods"),
        ("CHAPTER 3",                                    "methods"),
        ("METHODOLOGY",                                  "methods"),
        ("METHODS",                                      "methods"),
        ("RESEARCH METHODOLOGY",                         "methods"),
        ("MATERIALS AND METHODS",                        "methods"),
        ("III. METHODOLOGY",                             "methods"),
        ("3. METHODOLOGY",                               "methods"),
        ("RESEARCH DESIGN AND METHODOLOGY",              "methods"),
        ("RESEARCH METHOD",                              "methods"),
        ("METHOD OF RESEARCH",                           "methods"),
        ("METHODS AND PROCEDURES",                       "methods"),
        ("RESEARCH PROCEDURES",                          "methods"),
        ("DESIGN AND METHODOLOGY",                       "methods"),
        ("PAMAMARAAN NG PANANALIKSIK",                   "methods"),
        # results — standalone results chapter headings ONLY
        # NOTE: "CHAPTER IV", "CHAPTER 4", "CHAPTER FOUR" belong to
        # results_and_discussion below — do NOT duplicate them here or the
        # model gets contradictory training signal.
        ("RESULTS",                                      "results"),
        ("FINDINGS",                                     "results"),
        ("IV. RESULTS",                                  "results"),
        ("4. RESULTS",                                   "results"),
        ("PRESENTATION OF DATA",                         "results"),
        ("PRESENTATION AND ANALYSIS OF DATA",            "results"),
        ("ANALYSIS AND INTERPRETATION",                  "results"),
        ("DATA PRESENTATION",                            "results"),
        ("ANALYSIS AND DISCUSSION OF RESULTS",           "results"),
        ("PRESENTATION, ANALYSIS AND INTERPRETATION",    "results"),
        ("DATA ANALYSIS AND INTERPRETATION",             "results"),
        # results_and_discussion — combined chapter (very common in Filipino theses)
        ("RESULTS AND DISCUSSION",                           "results_and_discussion"),
        ("RESULTS AND DISCUSSIONS",                          "results_and_discussion"),
        ("IV. RESULTS AND DISCUSSION",                       "results_and_discussion"),
        ("4. RESULTS AND DISCUSSION",                        "results_and_discussion"),
        ("CHAPTER IV RESULTS AND DISCUSSION",                "results_and_discussion"),
        ("PRESENTATION, ANALYSIS AND INTERPRETATION OF DATA","results_and_discussion"),
        ("ANALYSIS AND INTERPRETATION OF DATA",              "results_and_discussion"),
        # Also add Chapter IV as results_and_discussion (many theses label it so)
        ("CHAPTER IV",                                       "results_and_discussion"),
        ("CHAPTER FOUR",                                     "results_and_discussion"),
        ("CHAPTER 4",                                        "results_and_discussion"),
        # discussion
        ("CHAPTER V",                                    "discussion"),
        ("CHAPTER FIVE",                                 "discussion"),
        ("CHAPTER 5",                                    "discussion"),
        ("CONCLUSION",                                   "discussion"),
        ("CONCLUSIONS",                                  "discussion"),
        ("CONCLUSIONS AND RECOMMENDATIONS",              "discussion"),
        ("CONCLUSION AND RECOMMENDATION",                "discussion"),
        ("SUMMARY CONCLUSIONS AND RECOMMENDATIONS",      "discussion"),
        ("V. CONCLUSION",                                "discussion"),
        ("5. CONCLUSION",                                "discussion"),
        ("SUMMARY, CONCLUSIONS AND RECOMMENDATIONS",     "discussion"),
        ("SUMMARY AND CONCLUSIONS",                      "discussion"),
        ("SUMMARY, FINDINGS, CONCLUSIONS AND RECOMMENDATIONS", "discussion"),
        ("SUMMARY OF FINDINGS",                          "discussion"),
        ("IMPLICATIONS AND RECOMMENDATIONS",             "discussion"),
        ("SUMMARY AND RECOMMENDATION",                   "discussion"),
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["heading_text", "section"])
        writer.writerows(seed_rows)
    print(f"[Train] Seed CSV written: {path} ({len(seed_rows)} rows)")


# ── Custom classification head training ──────────────────────────────────────

def train_classifier_head():
    """
    Train a dedicated 5-class classification head on top of the NLI backbone.

    WHY THIS EXISTS
    ───────────────
    The NLI fine-tuning approach trains the model to score entailment between
    a heading and a hypothesis sentence. This works but has a ceiling: the model
    must redistribute probability across 5 labels at inference time, so scores
    are typically 0.25–0.55 — close together and easy to confuse.

    A classification head approach instead:
      - Takes the [CLS] token embedding from the NLI backbone (frozen or unfrozen)
      - Adds a linear layer: hidden_size → 5 classes
      - Trains with cross-entropy loss directly on heading → section_key pairs
      - Produces cleaner, higher-confidence predictions (0.6–0.95 range typical)

    The trained classifier head is saved alongside the NLI model weights.
    ml_service.py detects it and switches to classifier-mode inference when present.

    USAGE
    ─────
    Run after train() completes:
        python train_imrad_nli.py --classifier

    Or train both in sequence:
        python train_imrad_nli.py --all
    """
    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, Dataset as TorchDataset
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        from sklearn.metrics import accuracy_score, f1_score, classification_report
        import numpy as np
    except ImportError as e:
        print(f"[Classifier] Missing dependency: {e}")
        return

    data_path = Path(DATA_PATH)
    if not data_path.exists():
        print(f"[Classifier] Data file not found: {DATA_PATH}. Run train() first.")
        return

    rows = load_csv(str(data_path))
    if len(rows) < 20:
        print(f"[Classifier] Only {len(rows)} rows — need at least 20.")
        return

    # Label map — 5 classes
    LABEL2ID = {s: i for i, s in enumerate(ALL_SECTIONS)}
    ID2LABEL = {i: s for s, i in LABEL2ID.items()}
    NUM_CLASSES = len(ALL_SECTIONS)
    print(f"[Classifier] Classes: {list(LABEL2ID.keys())}")

    # ── Dataset ───────────────────────────────────────────────────────────────
    class HeadingDataset(TorchDataset):
        def __init__(self, rows, tokenizer, max_length=MAX_LENGTH):
            self.encodings = tokenizer(
                [r["heading_text"] for r in rows],
                truncation=True,
                padding="max_length",
                max_length=max_length,
                return_tensors="pt",
            )
            self.labels = torch.tensor(
                [LABEL2ID[r["section"]] for r in rows], dtype=torch.long
            )
        def __len__(self):
            return len(self.labels)
        def __getitem__(self, idx):
            return {
                "input_ids":      self.encodings["input_ids"][idx],
                "attention_mask": self.encodings["attention_mask"][idx],
                "labels":         self.labels[idx],
            }

    # Augment: also add rows from HARD_NEGATIVE_LINES as a special "none" class?
    # No — hard negatives are filtered by _is_candidate_line before reaching the
    # classifier. We keep the 5-class setup clean.

    # Stratified split — ensures all 5 classes appear in both train and test sets.
    # With only ~60 rows a random split often drops some classes from the test set,
    # breaking the classification report and giving misleading eval metrics.
    from collections import defaultdict
    random.seed(SEED)
    by_class: dict = defaultdict(list)
    for r in rows:
        by_class[r["section"]].append(r)
    train_r, test_r = [], []
    for cls_rows in by_class.values():
        random.shuffle(cls_rows)
        n = max(1, int(len(cls_rows) * TEST_SPLIT))
        test_r.extend(cls_rows[:n])
        train_r.extend(cls_rows[n:])
    random.shuffle(train_r)
    random.shuffle(test_r)
    print(f"[Classifier] Stratified split — Train: {len(train_r)}, Test: {len(test_r)}")
    per_class = {k: len(v) for k, v in by_class.items()}
    print(f"[Classifier] Class distribution: {per_class}")

    base_model_path = OUTPUT_DIR if Path(OUTPUT_DIR).exists() else BASE_MODEL
    print(f"[Classifier] Loading backbone from: {base_model_path}")
    tokenizer = AutoTokenizer.from_pretrained(base_model_path)

    # Load as the full sequence-classification model, then extract the base
    # encoder. This avoids the "missing pooler.dense" warning that occurs when
    # loading an NLI checkpoint with AutoModel — the NLI model was saved as
    # AutoModelForSequenceClassification which includes a proper pooler.
    from transformers import AutoModelForSequenceClassification
    full_model = AutoModelForSequenceClassification.from_pretrained(
        base_model_path, ignore_mismatched_sizes=True,
    )
    # The underlying encoder is at .roberta (for roberta-based models).
    # Fall back gracefully for other architectures.
    if hasattr(full_model, "roberta"):
        backbone = full_model.roberta
    elif hasattr(full_model, "bert"):
        backbone = full_model.bert
    elif hasattr(full_model, "distilbert"):
        backbone = full_model.distilbert
    else:
        # Generic fallback: strip the classifier head by using base class
        backbone = full_model.base_model
    print(f"[Classifier] Backbone type: {type(backbone).__name__}, "
          f"hidden_size={backbone.config.hidden_size}")

    train_ds = HeadingDataset(train_r, tokenizer)
    test_ds  = HeadingDataset(test_r,  tokenizer)

    # ── Model with classification head ────────────────────────────────────────
    class IMRADClassifier(nn.Module):
        def __init__(self, backbone, num_classes):
            super().__init__()
            self.backbone = backbone
            hidden = backbone.config.hidden_size
            self.classifier = nn.Sequential(
                nn.Dropout(0.1),
                nn.Linear(hidden, hidden // 2),
                nn.GELU(),
                nn.Dropout(0.1),
                nn.Linear(hidden // 2, num_classes),
            )
        def forward(self, input_ids, attention_mask, labels=None):
            out = self.backbone(input_ids=input_ids, attention_mask=attention_mask)
            # Mean pooling over non-padding tokens — better than [CLS] for
            # cross-encoder NLI backbones where [CLS] is entailment-specialized
            token_embeddings = out.last_hidden_state
            mask_expanded    = attention_mask.unsqueeze(-1).float()
            pooled = (token_embeddings * mask_expanded).sum(1) / mask_expanded.sum(1).clamp(min=1e-9)
            logits = self.classifier(pooled)
            loss   = None
            if labels is not None:
                loss = nn.CrossEntropyLoss()(logits, labels)
            return {"loss": loss, "logits": logits}

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Classifier] Device: {device}")
    model = IMRADClassifier(backbone, NUM_CLASSES).to(device)

    # ── Training loop ─────────────────────────────────────────────────────────
    optimizer  = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    loader     = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    test_loader= DataLoader(test_ds,  batch_size=BATCH_SIZE)

    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0.0
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            out   = model(**batch)
            loss  = out["loss"]
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            total_loss += loss.item()

        # Evaluate
        model.eval()
        all_preds, all_labels = [], []
        with torch.no_grad():
            for batch in test_loader:
                batch  = {k: v.to(device) for k, v in batch.items()}
                out    = model(**batch)
                preds  = out["logits"].argmax(dim=-1).cpu().numpy()
                labels = batch["labels"].cpu().numpy()
                all_preds.extend(preds)
                all_labels.extend(labels)
        acc = accuracy_score(all_labels, all_preds)
        f1  = f1_score(all_labels, all_preds, average="weighted", zero_division=0)
        print(f"[Classifier] Epoch {epoch+1}/{EPOCHS} "
              f"loss={total_loss/len(loader):.4f} acc={acc:.3f} f1={f1:.3f}")

    # ── Save classifier head ──────────────────────────────────────────────────
    head_path = os.path.join(OUTPUT_DIR, "imrad_classifier_head.pt")
    torch.save({
        "state_dict": model.classifier.state_dict(),
        "label2id":   LABEL2ID,
        "id2label":   ID2LABEL,
        "hidden_size": backbone.config.hidden_size,
    }, head_path)
    print(f"[Classifier] Head saved to {head_path}")
    print("[Classifier] Set USE_CLASSIFIER_HEAD = True in ml_service.py to activate.")

    # Final report — pass explicit labels list so sklearn doesn't crash when
    # the test split happens to miss one or more classes (likely with small data)
    print("\n[Classifier] Classification report:")
    print(classification_report(
        all_labels, all_preds,
        labels=list(range(NUM_CLASSES)),
        target_names=[ID2LABEL[i] for i in range(NUM_CLASSES)],
        zero_division=0,
    ))


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    args = set(sys.argv[1:])
    if "--classifier" in args:
        train_classifier_head()
    elif "--all" in args:
        train()
        train_classifier_head()
    else:
        train()