import asyncio
from pypdf import PdfReader
from app.services.imrad_service import imrad_service

pdf_path = r"uploads\6d8a6a82-d764-400d-8356-64922bb3f8f5_BARROWED_THESIS_OK1.pdf"

# 1. Simulate OCR service PDF reading
reader = PdfReader(pdf_path)
num_pages = len(reader.pages)
page_text_map = {}
for i in range(num_pages):
    p_text = reader.pages[i].extract_text()
    if p_text:
        page_text_map[i + 1] = p_text

print("Extracted PDF pages.")

# 2. Extract sections
res = imrad_service.extract_sections(
    page_text_map,
    title="",
    authors="",
    pdf_path=pdf_path
)

results_text = res.get("sections", {}).get("results_and_discussion", "")
if not results_text:
    results_text = res.get("sections", {}).get("results", "")

print("--- Results Output Snippet ---")
print(results_text[:1000])

print("\n--- Searching for 'MEAN' or 'FUNCTIONAL' ---")
for kw in ["FUNCTIONAL", "MEAN", "STANDARD DEVIATION", "INTERPRETATION"]:
    idx = results_text.upper().find(kw)
    if idx != -1:
         start = max(0, idx - 100)
         end = min(len(results_text), idx + 300)
         print(f"[{kw} found at {idx}] \n {results_text[start:end]}\n" + "-"*30)
    else:
         print(f"[{kw} NOT found]")

