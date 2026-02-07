import pytesseract
from pdf2image import convert_from_path
import os
from typing import Dict, Any

import re
from pypdf import PdfReader

class OCRService:
    def __init__(self):
        # Common Windows paths for Tesseract
        tesseract_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Users\\' + os.getlogin() + r'\AppData\Local\Tesseract-OCR\tesseract.exe'
        ]
        self.tesseract_available = False
        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                self.tesseract_available = True
                break

    async def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extracts metadata using a mix of direct text extraction and regex heuristics.
        """
        print(f"--- Starting extraction for: {os.path.basename(pdf_path)} ---")
        full_text = ""
        try:
            # 1. Try to extract text directly using pypdf
            print("Attempting direct text extraction via pypdf...")
            reader = PdfReader(pdf_path)
            num_pages = len(reader.pages)
            print(f"PDF has {num_pages} pages.")
            
            # Check up to 10 pages for text
            for i in range(min(10, num_pages)):
                page_text = reader.pages[i].extract_text()
                if page_text:
                    full_text += page_text + "\n"
            
            print(f"Extracted {len(full_text)} characters via pypdf.")

            # 2. OCR Fallback (Only if pypdf returns almost nothing)
            if len(full_text.strip()) < 50:
                print("Direct text extraction failed to find significant text. Falling back to OCR...")
                if self.tesseract_available:
                    try:
                        # Extract first 3 pages for OCR
                        images = convert_from_path(pdf_path, first_page=1, last_page=3)
                        for i, img in enumerate(images):
                            print(f"OCR processing page {i+1}...")
                            full_text += pytesseract.image_to_string(img)
                    except Exception as ocr_err:
                        print(f"OCR Error (likely missing Poppler): {ocr_err}")
                else:
                    print("OCR requested but Tesseract not found in default paths.")

            # --- Smarter Heuristics ---
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            
            # Extract Year (Look for 2010-2029)
            year_match = re.search(r'\b(20[1-2][0-9])\b', full_text)
            detected_year = year_match.group(1) if year_match else "N/A"

            # Extract Title
            detected_title = lines[0] if lines else os.path.basename(pdf_path)
            
            # --- IMPROVED AUTHOR EXTRACTION ---
            # Search for the authors in ALL CAPS after the degree mentions
            detected_authors = []
            found_degree = False
            for line in lines:
                # Look for the degree line
                if "Bachelor of Science" in line or "Computer Science" in line:
                    found_degree = True
                    continue
                
                # If we found the degree, the next few lines in ALL CAPS are likely authors
                if found_degree and line.isupper() and len(line) > 5:
                    detected_authors.append(line)
                elif found_degree and line and not line.isupper():
                    # Stop once we hit a line that isn't ALL CAPS (like the date)
                    if len(detected_authors) > 0:
                        break

            final_author = ", ".join(detected_authors) if detected_authors else "Autodetected (Please Verify)"

            # --- SMARTER ABSTRACT EXTRACTION ---
            # Try to find the word 'ABSTRACT' or 'SUMMARY'
            abstract_text = ""
            abstract_patterns = [r'\bABSTRACT\b', r'\bSUMMARY\b', r'\bAbstract\b']
            
            found_start = -1
            for pattern in abstract_patterns:
                match = re.search(pattern, full_text)
                if match:
                    found_start = match.end()
                    break
            
            if found_start != -1:
                # Take up to 3000 characters after the 'ABSTRACT' heading
                abstract_text_raw = full_text[found_start:].strip()
                
                # --- CLEANING HEADER FROM ABSTRACT ---
                raw_lines = abstract_text_raw.split('\n')
                cleaned_lines = []
                start_collecting = False
                
                for line in raw_lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # If we haven't started collecting yet, check if this line is a "header" line
                    if not start_collecting:
                        # Skip lines that are ALL CAPS and short (likely names or titles)
                        # Or lines that are very short (likely labels)
                        if (line.isupper() and len(line) < 100) or len(line) < 20:
                            continue
                        else:
                            start_collecting = True
                    
                    if start_collecting:
                        cleaned_lines.append(line)
                
                abstract_text = "\n".join(cleaned_lines)

                # Clean up: stop if we hit another common header
                stop_patterns = ["TABLE OF CONTENTS", "ACKNOWLEDGMENTS", "LIST OF TABLES", "INTRODUCTION", "CHAPTER I"]
                for stop in stop_patterns:
                    stop_idx = abstract_text.upper().find(stop)
                    if stop_idx != -1 and stop_idx > 100:
                        abstract_text = abstract_text[:stop_idx].strip()
                        break
                
                # Limit size
                abstract_text = abstract_text[:2500]
            
            # Fallback if no abstract keyword found
            if not abstract_text or len(abstract_text) < 100:
                abstract_text = full_text[:1500].strip()

            # Extract Department (Look for "College of" or "Department of")
            dept_match = re.search(r'(College of [A-Za-z\s]+|Department of [A-Za-z\s]+)', full_text, re.IGNORECASE)
            detected_dept = dept_match.group(1) if dept_match else "N/A"

            # Extract Keywords (Look for "Keywords:" or "Index Terms:")
            keywords_match = re.search(r'(Keywords:|Index Terms:)(.*?)(?=\n|\.)', full_text, re.IGNORECASE)
            detected_keywords = keywords_match.group(2).strip() if keywords_match else ""

            metadata = {
                "title": detected_title,
                "author": final_author,
                "year": detected_year, 
                "abstract": abstract_text if abstract_text else "No text could be extracted.",
                "department": detected_dept,
                "keywords": detected_keywords,
                "citation_count": 0  # Default to 0 for new uploads
            }
            
            print("Successfully finished extraction.")
            return metadata
            
        except Exception as e:
            print(f"CRITICAL Extraction Error: {type(e).__name__} - {e}")
            return {
                "title": os.path.basename(pdf_path),
                "author": "Unknown",
                "year": "N/A",
                "abstract": f"Extraction failed: {str(e)}"
            }

ocr_service = OCRService()
