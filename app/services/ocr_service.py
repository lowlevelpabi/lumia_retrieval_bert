import pytesseract
from pdf2image import convert_from_path
import os
from typing import Dict, Any

import re
import base64
from io import BytesIO
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
            
            # DIAGNOSTIC: Print the first 80 lines to see what OCR extracted
            print(f"\n===== [OCR DIAGNOSIS] First 80 lines of full_text =====")
            for i, l in enumerate(lines[:80]):
                print(f"  [{i:02d}] {repr(l)}")
            print("=====  [END DIAGNOSIS] =====\n")

            # --- ROBUST AUTHOR EXTRACTION ---
            # KEY INSIGHT (from diagnostic):
            # The entire cover page is often ONE giant line joined by double-spaces.
            # Standard Filipino academic format: "SURNAME, FIRSTNAME M.I."
            # We use re.findall to scan the first portion of the document for this pattern.
            
            cover_text = full_text[:5000]  # Only search cover page region
            detected_authors = []

            # Strategy 1: ALL CAPS format - "BILLONES, PRINCE ISIAH R."
            all_caps_names = re.findall(
                r'[A-Z]{2,}(?:\s+[A-Z]+)*,\s+[A-Z]+(?:\s+[A-Z]+)+\s+[A-Z]\.',
                cover_text
            )
            if all_caps_names:
                # Clean double-spaces from each found name
                detected_authors = [re.sub(r'\s+', ' ', n).strip() for n in all_caps_names[:5]]

            # Strategy 2: Title Case format - "Billones, Prince Isiah R."
            if not detected_authors:
                title_case_names = re.findall(
                    r'[A-Z][a-z]+,\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]*)+\s+[A-Z]\.',
                    cover_text
                )
                if title_case_names:
                    detected_authors = [re.sub(r'\s+', ' ', n).strip() for n in title_case_names[:5]]

            author_fallback = "The system couldn't confidently detect any authors. Please click '+ Add Another Author' below to enter them manually."
            final_author = " | ".join(detected_authors) if detected_authors else author_fallback

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
                # Define patterns to skip during initial line traversal
                skip_patterns = [
                    r"An undergraduate thesis (?:outline )?submitted to the faculty of.*",
                    r"Cavite State University.*",
                    r"in partial fulfillment of the requirements for the degree of.*",
                    r"Bachelor of Science in [A-Za-z\s]+(?: with Contribution no.*)?",
                    r"Prepared under the supervision of.*",
                    r"Adviser:.*",
                    r"Department of [A-Za-z\s]+",
                    r"College of [A-Za-z\s]+",
                    r"[A-Z][a-z]+ \d{4}", 
                    r"Imus Campus, Imus City, Cavite"
                ]
                if detected_title and detected_title != "Untitled":
                    skip_patterns.append(fr"^{re.escape(detected_title.strip().rstrip('.'))}\.?")

                start_collecting = False
                for line in raw_lines:
                    line = line.strip()
                    if not line: continue
                    
                    if not start_collecting:
                        # Skip until we find a line that:
                        # 1. Isn't boilerplate
                        # 2. Isn't just "ABSTRACT"
                        # 3. Isn't a short header/label/page number
                        is_boilerplate = any(re.search(p, line, re.IGNORECASE) for p in skip_patterns)
                        is_page_num = re.match(r'^\d+$', line) or re.match(r'^[ivx]+$', line, re.IGNORECASE)
                        is_short_label = (line.isupper() and len(line) < 100) or len(line) < 20
                        
                        if is_boilerplate or line.upper() == "ABSTRACT" or is_short_label or is_page_num:
                            continue
                        else:
                            start_collecting = True
                    
                    if start_collecting:
                        # Skip standalone page numbers integrated in middle of text (usually between pages)
                        if re.match(r'^\d+$', line) or re.match(r'^[ivx]+$', line, re.IGNORECASE):
                            continue
                        cleaned_lines.append(line)
                
                abstract_text = " ".join(cleaned_lines)

                # Final stop check for end sections
                stop_patterns = ["TABLE OF CONTENTS", "ACKNOWLEDGMENTS", "LIST OF TABLES", "INTRODUCTION", "CHAPTER I"]
                for stop in stop_patterns:
                    stop_idx = abstract_text.upper().find(stop)
                    if stop_idx != -1 and stop_idx > 100:
                        abstract_text = abstract_text[:stop_idx].strip()
                        break

                abstract_text = abstract_text[:2500].strip()
            
            # Fallback if no abstract keyword found OR if direct extraction failed (scanned PDF)
            if not abstract_text or len(abstract_text) < 100 or len(full_text) < 200:
                print("Direct text extraction seems insufficient. Attempting OCR fallback...")
                try:
                    ocr_full_text = await self.extract_text_via_ocr(pdf_path)
                    if len(ocr_full_text) > len(full_text):
                        full_text = ocr_full_text
                        # Re-run keyword search on OCR'd text
                        match = re.search(r'(?i)abstract[:\-. ]+(.*?)(?:\d+\.|\n\n|introduction|keywords|$)', full_text, re.DOTALL)
                        if match:
                            abstract_text = match.group(1).strip()
                except Exception as e:
                    print(f"OCR Fallback failed: {e}")


            # Extract Degree Program (Look for BSCS, BSIT, BSIS, etc.)
            detected_degree = "N/A"
            degree_patterns = {
                "BSCS": [r"Computer Science", r"BSCS", r"B\.S\. in Computer Science", r"Bachelor of Science in Computer Science"],
                "BSIT": [r"Information Technology", r"BSIT", r"B\.S\. in Information Technology", r"Bachelor of Science in Information Technology"],
                "BSIS": [r"Information Systems", r"BSIS", r"B\.S\. in Information Systems", r"Bachelor of Science in Information Systems"],
                "BSCpE": [r"Computer Engineering", r"BSCpE", r"Bachelor of Science in Computer Engineering"]
            }
            for degree, patterns in degree_patterns.items():
                if any(re.search(p, full_text, re.IGNORECASE) for p in patterns):
                    detected_degree = degree
                    break

            # Extract Department (Look for "College of" or "Department of")
            dept_match = re.search(r'((?:College|Department) of [A-Za-z0-9\s]+)', full_text, re.IGNORECASE)
            detected_dept = dept_match.group(1).strip() if dept_match else "N/A"
            
            # Normalize casing to match UI dropdown (e.g., Department of Information Systems)
            if detected_dept != "N/A":
                # Title case all words except "of"
                words = detected_dept.split()
                normalized_words = []
                for i, word in enumerate(words):
                    if i > 0 and word.lower() == "of":
                        normalized_words.append("of")
                    else:
                        normalized_words.append(word.capitalize())
                detected_dept = ' '.join(normalized_words)

            # --- NEW INFERENCE FALLBACK ---
            # If literal extraction didn't yield a valid department matching our UI, 
            # or returned N/A, infer from the degree program.
            valid_ui_depts = [
                "Department of Computer Science",
                "Department of Information Technology",
                "Department of Information Systems",
                "Department of Computer Engineering"
            ]

            if detected_dept not in valid_ui_depts:
                inference_map = {
                    "BSCS": "Department of Computer Science",
                    "BSIT": "Department of Information Technology",
                    "BSIS": "Department of Information Systems",
                    "BSCpE": "Department of Computer Engineering"
                }
                # Only overwrite if inference is successful
                inferred = inference_map.get(detected_degree)
                if inferred:
                    detected_dept = inferred

            # Extract Project Type (Capstone, Thesis, etc.)
            detected_project_type = "Thesis" # Default to Thesis
            type_patterns = {
                "Capstone Project": [r"Capstone", r"Design Project", r"Software Project"],
                "Thesis": [r"Thesis", r"Dissertation"]
            }
            for p_type, patterns in type_patterns.items():
                if any(re.search(p, full_text, re.IGNORECASE) for p in patterns):
                    detected_project_type = p_type
                    break


            # Extract Keywords (look for "Keywords:" label)
            detected_keywords = ""
            kw_match = re.search(
                r'[Kk]eywords?\s*[:\-–]\s*(.+?)(?:\n\n|\.\s+[A-Z]|$)',
                full_text,
                re.DOTALL
            )
            if kw_match:
                raw_kw = kw_match.group(1).strip()
                # Collapse whitespace and cap length
                detected_keywords = re.sub(r'\s+', ' ', raw_kw)[:300]

            # Abstract final fallback message
            if not abstract_text or len(abstract_text.strip()) < 50:
                abstract_text = "The author of this study doesn't provide any abstract, or it perhaps it is still in manuscript phase or incomplete study."

            metadata = {
                "title": detected_title,
                "author": final_author,
                "year": detected_year, 
                "abstract": abstract_text,
                "department": detected_dept,
                "keywords": detected_keywords,
                "degree_program": detected_degree,
                "project_type": detected_project_type,
                "citation_count": 0
            }
            
            print("Successfully finished extraction.")
            return metadata
            
        except Exception as e:
            print(f"CRITICAL Extraction Error: {type(e).__name__} - {e}")
            return {
                "title": os.path.basename(pdf_path),
                "author": "Unknown",
                "year": "N/A",
                "abstract": f"Extraction failed: {str(e)}",
                "department": "N/A",
                "keywords": "",
                "project_type": "N/A",
                "degree_program": "N/A",
                "citation_count": 0,
            }

    async def extract_page_previews(self, pdf_path: str):
        """
        Extracts base64 thumbnails and text snippets for all pages in a PDF.
        """
        previews = []
        try:
            reader = PdfReader(pdf_path)
            num_pages = len(reader.pages)
            
            # Convert PDF pages to images for thumbnails
            # We use low DPI (72) for fast processing and small payload
            images = convert_from_path(pdf_path, dpi=72)
            
            for i in range(num_pages):
                # 1. Get Text Preview
                page_text = reader.pages[i].extract_text() or ""
                preview_text = page_text[:200].strip()
                
                # 2. Convert Image to Base64
                buffered = BytesIO()
                images[i].save(buffered, format="JPEG", quality=60)
                img_str = base64.b64encode(buffered.getvalue()).decode()
                
                previews.append({
                    "page_num": i + 1,
                    "thumbnail": img_str,
                    "preview_text": preview_text
                })
        except Exception as e:
            print(f"Error extracting page previews: {e}")
            
        return previews

ocr_service = OCRService()
