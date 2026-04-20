from pypdf import PdfReader
import os

pdf_path = r'c:\Users\SIBIYA GAMING\Documents\Undergraduate Thesis System\lumia_retrieval_bert\sample_documents\UPDATED_MANUSCRIPT_APRIL_20_2026_REV3.pdf'
reader = PdfReader(pdf_path)
for i, page in enumerate(reader.pages):
    text = page.extract_text()
    if text:
        header = text[:500].replace('\n', ' ').strip()
        print(f"Page {i+1}: {header.encode('ascii', 'ignore').decode()}")
