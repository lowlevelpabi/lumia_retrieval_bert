import os
import csv
import re
from pypdf import PdfReader

# 1. Put your PDFs in this folder
PDF_FOLDER = "./sample_documents"

# 2. Per-document CSVs will be saved here (created automatically)
OUTPUT_FOLDER = "./extracted_data_heading"


def clean_chunk(text):
    """Clean up PyPDF extraction artefacts."""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def process_single_pdf(pdf_path: str, output_csv: str):
    """Extract text chunks from one PDF and write them to a separate CSV."""
    chunks_written = 0

    with open(output_csv, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['text', 'label'])  # Header

        try:
            reader = PdfReader(pdf_path)
            for page_num, page in enumerate(reader.pages):
                raw_text = page.extract_text()
                if not raw_text:
                    continue

                # Split page into paragraph-level chunks on double newlines.
                # Falls back gracefully to single newlines for tightly-packed PDFs.
                chunks = raw_text.split('\n\n')

                for chunk in chunks:
                    cleaned = clean_chunk(chunk)

                    # Skip empty / noise-only chunks
                    if len(cleaned) < 5:
                        continue

                    writer.writerow([cleaned, ''])  # blank label — fill in Excel
                    chunks_written += 1

        except Exception as e:
            print(f"  ERROR reading {pdf_path}: {e}")

    return chunks_written


def process_all_pdfs():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith('.pdf')]

    if not pdf_files:
        print(f"No PDF files found in '{PDF_FOLDER}'. Exiting.")
        return

    print(f"Found {len(pdf_files)} PDF(s) in '{PDF_FOLDER}'.\n")

    for filename in sorted(pdf_files):
        pdf_path = os.path.join(PDF_FOLDER, filename)

        # Output CSV name mirrors the PDF name: e.g., "paper1.pdf" → "training_data_paper1.csv"
        base_name = os.path.splitext(filename)[0]
        output_csv = os.path.join(OUTPUT_FOLDER, f"training_data_{base_name}.csv")

        print(f"Processing : {filename}")
        print(f"  Output   : {output_csv}")

        count = process_single_pdf(pdf_path, output_csv)
        print(f"  Chunks   : {count} rows written\n")

    print("=" * 58)
    print(f"All done! Open each CSV inside '{OUTPUT_FOLDER}/' in Excel")
    print("and fill the 'label' column using exactly these 7 values:")
    print("  heading_intro      heading_methods    heading_results")
    print("  heading_discussion heading_other      body_text   junk")
    print("=" * 58)


if __name__ == "__main__":
    process_all_pdfs()