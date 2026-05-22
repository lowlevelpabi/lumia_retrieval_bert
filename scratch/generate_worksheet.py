import os
import sys
import random

# Ensure Python can find the 'app' module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ocr_service import ocr_service

sample_dir = r"c:\Users\Maruf\Documents\BSCS-4A (2025)\Undergrad Thesis 1\Final Thesis System\Thesis Backend\sample_documents"
output_file = r"c:\Users\Maruf\Documents\BSCS-4A (2025)\Undergrad Thesis 1\Final Thesis System\Thesis Backend\scratch\imrad_evaluation_worksheet.md"

# Select 3 typical thesis PDFs from your sample directory
target_pdfs = [
    "ALERTO-ENHANCING-EMERGENCY-RESPONSE-AND-REPORTING-USING.pdf",
    "MOBILE APPLICATION FOR DISEASE CLASSIFICATION OF COFFEE.pdf",
    "DEEPFAKE DETECTION OF KNOWN PERSONALITIES.pdf"
]

print("Starting extraction for worksheet generation. This may take a minute or two...")

with open(output_file, "w", encoding="utf-8") as out:
    out.write("# IMRAD Extraction Evaluation Worksheet\n\n")
    out.write("> **Instructions:** For each extracted paragraph below, read the text and verify if the `Predicted Section` is correct. Write the true section in the `Actual Section` bracket (e.g., [Introduction], [Methods], etc.).\n\n")
    out.write("---\n\n")
    
    for pdf_name in target_pdfs:
        pdf_path = os.path.join(sample_dir, pdf_name)
        print(f"Extracting IMRAD from: {pdf_name}...")
        
        try:
            # Use the exact same extraction pipeline the web app uses
            metadata = ocr_service.extract_metadata_sync(pdf_path, session_id="test_session")
            sections = metadata.get("sections", {})
            
            out.write(f"## Document: {pdf_name}\n\n")
            
            # Loop through each extracted section (Intro, Methods, Results, Discussion)
            for sec_name, sec_text in sections.items():
                if not sec_text or sec_name == "references": 
                    continue
                
                # Split the big chunk of text into individual paragraphs
                paragraphs = [p.strip() for p in sec_text.split('\n\n') if len(p.strip()) > 150]
                
                # Randomly pick 2 paragraphs from this section to test
                samples = random.sample(paragraphs, min(2, len(paragraphs)))
                
                for idx, sample in enumerate(samples):
                    out.write(f"**System Prediction:** `{sec_name.title()}`\n\n")
                    out.write(f"**Actual Section:** [ _________________ ]\n\n")
                    out.write(f"> {sample}\n\n")
                    out.write("---\n\n")
                    
        except Exception as e:
            print(f"Failed to process {pdf_name}: {e}")

print(f"\nSuccess! Worksheet generated at: {output_file}")
