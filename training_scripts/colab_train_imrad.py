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

# ── 2. Load & prepare the EXPANDED data ───────────────────
# Using the file we generated from the PDFs
df = pd.read_csv('expanded_imrad_dataset.csv')
df = df.dropna(subset=['text', 'label'])
df = df[df['text'].str.strip().str.len() > 5]

# Map IMRAD labels to IDs
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
    'heading_discussion': 4 # Mapping discussion to results as per common IMRAD groupings
}
id2label = {v: k for k, v in label_map.items()}

df['label'] = df['label'].map(label_map)
df = df.dropna(subset=['label'])
df['label'] = df['label'].astype(int)

print("Balanced distribution after oversampling:")
target_count = df['label'].value_counts().max()
balanced_dfs = []
for label in df['label'].unique():
    label_df = df[df['label'] == label]
    balanced_dfs.append(label_df.sample(target_count, replace=True))
df = pd.concat(balanced_dfs, ignore_index=True).sample(frac=1, random_state=42)
print(df['label'].map(id2label).value_counts())

# ── 3. Train / validation split ─────────────────────────
train_df, val_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df['label'])
train_dataset = Dataset.from_pandas(train_df.reset_index(drop=True))
val_dataset   = Dataset.from_pandas(val_df.reset_index(drop=True))

# ── 4. Tokenise ──────────────────────────────────────
MODEL_NAME = "distilbert-base-uncased"
tokenizer  = AutoTokenizer.from_pretrained(MODEL_NAME)

def tokenize(examples):
    return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=128)

tokenized_train = train_dataset.map(tokenize, batched=True)
tokenized_val   = val_dataset.map(tokenize, batched=True)

# ── 5. Load model ─────────────────────────────────────
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=9, id2label=id2label, label2id=label_map)

# ── 6. Training args ──────────────────────────────────
training_args = TrainingArguments(
    output_dir="./results",
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    num_train_epochs=5,
    weight_decay=0.01,
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True
)

# ── 7. Train ───────────────────────────────────────
trainer = Trainer(model=model, args=training_args, train_dataset=tokenized_train, eval_dataset=tokenized_val)
trainer.train()

# ── 8. Save ────────────────────────────────────────
trainer.save_model("./distilbert_imrad_model")
tokenizer.save_pretrained("./distilbert_imrad_model")
print("Model retrained and saved.")