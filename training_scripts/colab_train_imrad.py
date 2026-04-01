# ============================================================
#  IMRaD DistilBERT Classifier — Google Colab Training Script
#  Runtime: GPU (T4)  |  Expected time: ~5-10 minutes
# ============================================================

# 1. Install dependencies
# !pip install transformers datasets torch scikit-learn pandas

import pandas as pd
import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments,
)
from sklearn.model_selection import train_test_split

# ── 2. Load & prepare data ───────────────────────────────────
df = pd.read_csv('imrad_training_data_clean.csv')
df = df.dropna(subset=['text', 'label'])
df = df[df['text'].str.strip().str.len() > 5]

print("Original distribution:")
print(df['label'].value_counts())

target_count = df['label'].value_counts().max() 
balanced_dfs = []

for label in df['label'].unique():
    label_df = df[df['label'] == label]
    current_count = len(label_df)
    
    if current_count < target_count:
        multiplier = target_count // current_count
        label_df = pd.concat([label_df] * multiplier, ignore_index=True)
        remainder = target_count % current_count
        if remainder > 0:
            label_df = pd.concat([label_df, label_df.iloc[:remainder]], ignore_index=True)
            
    balanced_dfs.append(label_df)

df = pd.concat(balanced_dfs, ignore_index=True).sample(frac=1, random_state=42)
print("\nBalanced distribution after oversampling:")
print(df['label'].value_counts())

label_map = {
    'heading_intro':      0,
    'subheading_intro':   1,
    'heading_methods':    2,
    'subheading_methods': 3,
    'heading_results':    4,
    'subheading_results': 5,
    'heading_other':      6,  
    'body_text':          7,
    'junk':               8,
}
id2label = {v: k for k, v in label_map.items()}

df['label'] = df['label'].map(label_map)
df = df.dropna(subset=['label'])          
df['label'] = df['label'].astype(int)

print("Label distribution:")
print(df['label'].map(id2label).value_counts())
print(f"\nTotal samples: {len(df)}")

# ── 3. Train / validation split (80/20) ─────────────────────
train_df, val_df = train_test_split(
    df, test_size=0.2, random_state=42, stratify=df['label']
)

train_dataset = Dataset.from_pandas(train_df.reset_index(drop=True))
val_dataset   = Dataset.from_pandas(val_df.reset_index(drop=True))

# ── 4. Tokenise ──────────────────────────────────────────────
MODEL_NAME = "distilbert-base-uncased"
tokenizer  = AutoTokenizer.from_pretrained(MODEL_NAME)

def tokenize(examples):
    return tokenizer(
        examples["text"],
        padding="max_length",
        truncation=True,
        max_length=128,
    )

tokenized_train = train_dataset.map(tokenize, batched=True)
tokenized_val   = val_dataset.map(tokenize, batched=True)

# ── 5. Load base model ───────────────────────────────────────
model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=len(label_map),
    id2label=id2label,
    label2id=label_map,
)

# ── 6. Training arguments ────────────────────────────────────
training_args = TrainingArguments(
    output_dir="./results",
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    num_train_epochs=5,          
    weight_decay=0.01,
    eval_strategy="epoch",       
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    logging_steps=10,
)

# ── 7. Train ─────────────────────────────────────────────────
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train,
    eval_dataset=tokenized_val,
    processing_class=tokenizer, 
)

print("\nStarting training...")
trainer.train()

# ── 8. Save model ────────────────────────────────────────────
trainer.save_model("./distilbert_imrad_model")
tokenizer.save_pretrained("./distilbert_imrad_model")
print("\nModel saved to ./distilbert_imrad_model")

# ── 9. Quick smoke test ──────────────────────────────────────
from transformers import pipeline

clf = pipeline(
    "text-classification",
    model="./distilbert_imrad_model",
    tokenizer="./distilbert_imrad_model",
)
test_texts = [
    "INTRODUCTION Coffee has been a valuable segment of the Philippine economy.",
    "METHODOLOGY The researchers used a mixed-method approach.",
    "RESULTS AND DISCUSSION The system achieved an overall mean of 4.51.",
    "Statement of the Problem The office processes applications manually.",
    "Participants of the Study The study involved IT professionals and students.",
]
print("\nSmoke test results:")
for t in test_texts:
    r = clf(t[:512])[0]
    print(f"  [{r['label']:22s} {r['score']:.2f}]  {t[:60]}")

# ── 10. Zip for download ─────────────────────────────────────
# Run this in a NEW Colab cell after training completes:
# !zip -r distilbert_imrad_model.zip ./distilbert_imrad_model
