import fitz # PyMuPDF
import pandas as pd
import re
import os

def extract_segments_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    segments = []
    for page in doc:
        text = page.get_text("text")
        # Split by newlines and filter out empty or very short noise
        lines = [s.strip() for s in text.split('\n') if len(s.strip()) > 3]
        segments.extend(lines)
    return segments

def auto_label_hybrid(text):
    text_upper = text.upper().strip()
    
    # 1. Heading Logic (Regex)
    if re.search(r'^(CHAPTER\s+[1I]|INTRODUCTION|BACKGROUND)', text_upper): return 'heading_intro'
    if re.search(r'^(CHAPTER\s+[3III]|METHODOLOGY|RESEARCH\s+DESIGN)', text_upper): return 'heading_methods'
    if re.search(r'^(CHAPTER\s+[4IV]|RESULTS|DISCUSSION|FINDINGS)', text_upper): return 'heading_results'
    if re.search(r'^(REFERENCES|APPENDICES|BIBLIOGRAPHY|TABLE\s+OF\s+CONTENTS)', text_upper): return 'heading_other'
    
    # 2. Body Text Logic (Length-based)
    if len(text.split()) > 15:
        return 'body_text'
    
    # 3. Noise/Junk
    if len(text) < 10 or re.search(r'^[0-9\.\s]+$', text):
        return 'junk'
        
    return 'junk'

# Paths to your uploaded PDFs
pdf_dir = './sample_data'
pdf_files = [os.path.join(pdf_dir, f) for f in os.listdir(pdf_dir) if f.endswith('.pdf')]

new_data = []
print(f"Processing {len(pdf_files)} PDFs...")

for pdf in pdf_files:
    try:
        lines = extract_segments_from_pdf(pdf)
        for line in lines:
            label = auto_label_hybrid(line)
            if label != 'junk': # Only keep useful data for training
                new_data.append({'text': line, 'label': label})
    except Exception as e:
        print(f"Could not process {pdf}: {e}")

new_df = pd.DataFrame(new_data)
old_df = pd.read_csv('./training_csv/lumia_trainext_imrad_ds2002.csv')

# Combine and save
combined_df = pd.concat([old_df, new_df], ignore_index=True).drop_duplicates(subset=['text'])
combined_df.to_csv('expanded_imrad_dataset.csv', index=False)

print(f"\nExtraction Complete!")
print(f"Original rows: {len(old_df)}")
print(f"New total rows: {len(combined_df)}")
print(combined_df['label'].value_counts())