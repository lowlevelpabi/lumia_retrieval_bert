import pytesseract
from pdf2image import convert_from_path
import os
from typing import Dict, Any, List, Optional

import re
import base64
from io import BytesIO
from pypdf import PdfReader
from app.services.imrad_service import imrad_service
from app.services.imrad_summary_service import imrad_summary_service


class OCRService:
    def __init__(self):
        tesseract_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            '/usr/bin/tesseract'
        ]

        try:
            import getpass
            user = getpass.getuser()
            tesseract_paths.append(fr'C:\Users\{user}\AppData\Local\Tesseract-OCR\tesseract.exe')
        except Exception:
            pass

        self.tesseract_available = False

        try:
            import subprocess
            subprocess.run(['tesseract', '--version'], capture_output=True, check=True)
            self.tesseract_available = True
            print("Tesseract detected in system PATH.")
        except (Exception, FileNotFoundError):
            for path in tesseract_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    self.tesseract_available = True
                    print(f"Tesseract detected at: {path}")
                    break

        if not self.tesseract_available:
            print("⚠️ Tesseract OCR not found. OCR features will be disabled.")

    async def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extracts metadata, IMRAD sections, and prepares the imrad_pages list
        for thumbnail filtering.

        Changes from original:
        - page_text_map is built from ALL pages (not just first 10) so IMRAD
          detection covers the full document.
        - meta_text still uses only first 10 pages for title/author/abstract.
        - detect_subheadings() receives page_text_map + methods_pages directly.
        - Returns 'imrad_pages' key: a short list of preview pages per section
          (first PREVIEW_PAGES_PER_SECTION pages of each section) used by
          extract_page_previews() to filter thumbnails.
        """
        print(f"--- Starting extraction for: {os.path.basename(pdf_path)} ---")
        try:
            print("Attempting direct text extraction via pypdf...")
            reader = PdfReader(pdf_path)
            num_pages = len(reader.pages)
            print(f"PDF has {num_pages} pages.")

            # ── Full page map for IMRAD (all pages) ───────────────────────────
            page_text_map: Dict[int, str] = {}
            for i in range(num_pages):
                p_text = reader.pages[i].extract_text()
                if p_text:
                    page_text_map[i + 1] = p_text

            # ── Meta text for title/author/abstract (first 10 pages only) ────
            meta_text = ""
            for i in range(min(10, num_pages)):
                meta_text += page_text_map.get(i + 1, "") + "\n"

            print(f"Extracted {len(meta_text)} characters via pypdf (meta pages).")

            if len(meta_text.strip()) < 50:
                print("Direct extraction insufficient. Falling back to OCR...")
                if self.tesseract_available:
                    try:
                        images = convert_from_path(pdf_path, first_page=1, last_page=3)
                        for i, img in enumerate(images):
                            print(f"OCR processing page {i+1}...")
                            meta_text += pytesseract.image_to_string(img)
                    except Exception as ocr_err:
                        print(f"OCR Error (likely missing Poppler): {ocr_err}")
                else:
                    print("OCR requested but Tesseract not found.")

            lines = [line.strip() for line in meta_text.split('\n') if line.strip()]

            # ── Year ──────────────────────────────────────────────────────────
            year_match = re.search(r'\b(20[1-2][0-9])\b', meta_text)
            detected_year = year_match.group(1) if year_match else "N/A"

            # ── Title ─────────────────────────────────────────────────────────
            TITLE_STOP_PATTERNS = [
                r'\b(submitted|presented|in partial|fulfillment|requirements|degree|bachelor|undergraduate|thesis|capstone|adviser|supervisor|prepared)\b',
                r'\b(cavite|university|college|department|imus|campus)\b',
                r'^(by|presented by|submitted by)$',
                r'\b(20[1-2][0-9])\b',
                r'[A-Z]{2,},\s+[A-Z]+',
                r'^[A-Z][a-z]+,\s+[A-Z]',
            ]
            title_lines = []
            for line in lines[:15]:
                is_stop = any(re.search(p, line, re.IGNORECASE) for p in TITLE_STOP_PATTERNS)
                looks_like_title = (
                    len(line) > 3 and
                    not line.endswith('.') and
                    not is_stop
                )
                if looks_like_title:
                    title_lines.append(line)
                elif title_lines:
                    break

            detected_title = " ".join(title_lines).strip() if title_lines else os.path.basename(pdf_path)
            detected_title = re.sub(r'\s+', ' ', detected_title)

            print(f"\n===== [OCR DIAGNOSIS] First 80 lines =====")
            for i, l in enumerate(lines[:80]):
                print(f"  [{i:02d}] {repr(l)}")
            print("=====  [END DIAGNOSIS] =====\n")

            # ── Authors ───────────────────────────────────────────────────────
            cover_text = meta_text[:5000]
            detected_authors = []

            # Strategy 1: ALL CAPS "LAST, FIRST MIDDLE MI." — e.g. DELA CRUZ, JUAN CARLO M.
            all_caps_names = re.findall(
                r'[A-Z]{2,}(?:\s+[A-Z]+)*,\s+[A-Z]+(?:\s+[A-Z]+)+\s+[A-Z]\.',
                cover_text
            )
            if all_caps_names:
                detected_authors = [re.sub(r'\s+', ' ', n).strip() for n in all_caps_names[:5]]

            # Strategy 2: Title Case "Last, First Middle MI." — e.g. Dela Cruz, Juan Carlo M.
            if not detected_authors:
                title_case_names = re.findall(
                    r'[A-Z][a-z]+,\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]*)+\s+[A-Z]\.',
                    cover_text
                )
                if title_case_names:
                    detected_authors = [re.sub(r'\s+', ' ', n).strip() for n in title_case_names[:5]]

            # Strategy 3: Names appear just ABOVE a "Month Year" date line — no "by" label
            if not detected_authors:
                date_match = re.search(
                    # Find possible month name under the author name list, so we can read upward from there to find names without relying on "by" labels which are often missing.
                    r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2}',
                    cover_text
                )
                if date_match:
                    chunk_before_date = cover_text[max(0, date_match.start() - 400) : date_match.start()]
                    lines_before = [l.strip() for l in chunk_before_date.split('\n') if l.strip()]
                    for line in reversed(lines_before):
                        words = line.split()
                        # Must be 2–4 words, each Title-cased or ALL CAPS, no digits, no noise
                        if (2 <= len(words) <= 4
                                and all(re.match(r'^[A-Z][a-zA-Z\-\.]+$', w) for w in words)):
                            detected_authors.insert(0, re.sub(r'\s+', ' ', line))
                        else:
                            # Stop as soon as we hit a non-name line coming upward
                            break
                    detected_authors = detected_authors[:5]

            author_fallback = "The system couldn't confidently detect any authors. Please click '+ Add Another Author' below to enter them manually."
            final_author = " | ".join(detected_authors) if detected_authors else author_fallback

            # ── Abstract ──────────────────────────────────────────────────────
            abstract_text = ""
            found_start = -1
            for pattern in [r'\bABSTRACT\b', r'\bSUMMARY\b', r'\bAbstract\b']:
                match = re.search(pattern, meta_text)
                if match:
                    found_start = match.end()
                    break

            if found_start != -1:
                abstract_text_raw = meta_text[found_start:].strip()
                raw_lines = abstract_text_raw.split('\n')
                cleaned_lines = []
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
                    # Also strip each long word of the title appearing alone on a line
                    for _frag in detected_title.split():
                        if len(_frag) > 8:
                            skip_patterns.append(fr"^{re.escape(_frag)}$")
                # Strip author name lines from abstract
                if detected_authors:
                    for _auth in detected_authors:
                        skip_patterns.append(re.escape(_auth.strip()))

                start_collecting = False
                for line in raw_lines:
                    line = line.strip()
                    if not line:
                        continue
                    if not start_collecting:
                        is_boilerplate = any(re.search(p, line, re.IGNORECASE) for p in skip_patterns)
                        is_page_num    = re.match(r'^\d+$', line) or re.match(r'^[ivx]+$', line, re.IGNORECASE)
                        is_short_label = (line.isupper() and len(line) < 100) or len(line) < 20
                        if is_boilerplate or line.upper() == "ABSTRACT" or is_short_label or is_page_num:
                            continue
                        else:
                            start_collecting = True
                    if start_collecting:
                        if re.match(r'^\d+$', line) or re.match(r'^[ivx]+$', line, re.IGNORECASE):
                            continue
                        cleaned_lines.append(line)

                abstract_text = " ".join(cleaned_lines)
                for stop in ["TABLE OF CONTENTS", "ACKNOWLEDGMENTS", "LIST OF TABLES", "INTRODUCTION", "CHAPTER I"]:
                    stop_idx = abstract_text.upper().find(stop)
                    if stop_idx != -1 and stop_idx > 100:
                        abstract_text = abstract_text[:stop_idx].strip()
                        break
                abstract_text = abstract_text[:2500].strip()

            if not abstract_text or len(abstract_text) < 100 or len(meta_text) < 200:
                print("Abstract extraction insufficient — no OCR fallback available for text-based PDFs.")

            # ── Degree ────────────────────────────────────────────────────────
            detected_degree = "N/A"
            degree_patterns = {
                "BSCS":  [r"Computer Science",       r"BSCS",  r"B\.S\. in Computer Science",       r"Bachelor of Science in Computer Science"],
                "BSIT":  [r"Information Technology", r"BSIT",  r"B\.S\. in Information Technology",  r"Bachelor of Science in Information Technology"],
                "BSIS":  [r"Information Systems",    r"BSIS",  r"B\.S\. in Information Systems",      r"Bachelor of Science in Information Systems"],
                "BSCpE": [r"Computer Engineering",   r"BSCpE", r"Bachelor of Science in Computer Engineering"],
            }
            for degree, patterns in degree_patterns.items():
                if any(re.search(p, meta_text, re.IGNORECASE) for p in patterns):
                    detected_degree = degree
                    break

            # ── Department ────────────────────────────────────────────────────
            dept_match = re.search(r'((?:College|Department) of [A-Za-z0-9\s]+)', meta_text, re.IGNORECASE)
            detected_dept = dept_match.group(1).strip() if dept_match else "N/A"
            if detected_dept != "N/A":
                words = detected_dept.split()
                detected_dept = ' '.join(
                    "of" if (i > 0 and w.lower() == "of") else w.capitalize()
                    for i, w in enumerate(words)
                )

            valid_ui_depts = [
                "Department of Computer Science", "Department of Information Technology",
                "Department of Information Systems", "Department of Computer Engineering",
            ]
            if detected_dept not in valid_ui_depts:
                detected_dept = {
                    "BSCS":  "Department of Computer Science",
                    "BSIT":  "Department of Information Technology",
                    "BSIS":  "Department of Information Systems",
                    "BSCpE": "Department of Computer Engineering",
                }.get(detected_degree, detected_dept)

            # ── Project type ──────────────────────────────────────────────────
            detected_project_type = "Thesis"
            for p_type, patterns in {
                "Capstone Project": [r"Capstone", r"Design Project", r"Software Project"],
                "Thesis":           [r"Thesis",   r"Dissertation"],
            }.items():
                if any(re.search(p, meta_text, re.IGNORECASE) for p in patterns):
                    detected_project_type = p_type
                    break

            # ── Keywords ──────────────────────────────────────────────────────
            detected_keywords = ""
            kw_match = re.search(
                r'[Kk]eywords?\s*[:\-–]\s*(.+?)(?:\n\n|\.\s+[A-Z]|$)',
                meta_text, re.DOTALL
            )
            if kw_match:
                detected_keywords = re.sub(r'\s+', ' ', kw_match.group(1).strip())[:300]

            if not abstract_text or len(abstract_text.strip()) < 50:
                abstract_text = "The author of this study doesn't provide any abstract, perhaps it is still in manuscript phase or incomplete study."

            # ── IMRAD Extraction ──────────────────────────────────────────────
            extracted_imrad = {"sections": {}, "section_pages": {}, "imrad_pages": []}
            detected_subs   = []
            try:
                extracted_imrad = imrad_service.extract_sections(
                    page_text_map,
                    title=detected_title,
                    authors=final_author,
                )

                # Use full_section_pages for subheading detection so we scan
                # the complete methods section, not just the preview pages.
                full_sec_pages = extracted_imrad.get("full_section_pages", {})
                methods_pages = full_sec_pages.get("methods") or extracted_imrad.get("section_pages", {}).get("methods", [])
                detected_subs = imrad_service.detect_subheadings(
                    page_text_map=page_text_map,
                    methods_pages=methods_pages,
                )
            except Exception as imrad_err:
                print(f"[IMRAD] Extraction failed (non-fatal): {type(imrad_err).__name__} - {imrad_err}")

            # ── Pre-generate IMRAD summaries ──────────────────────────────────
            # Done HERE (during preview) so the uploader sees summaries in
            # Step 2 and can correct them before confirming the upload.
            # The summaries travel back to the frontend in sections_summary
            # and are stored to DB in papers.py confirm_upload.
            sections_raw: dict = extracted_imrad.get("sections", {})

            # ── Inline intro truncation ───────────────────────────────────────
            # When OCR merges a sub-section heading inline with the paragraph
            # above it (e.g. "...(Dupont, 2024). Project Context Identifying...")
            # the page-level boundary detection in imrad_service never fires.
            # Cut the introduction at the first heading that appears at a sentence
            # or paragraph boundary (after ". ", "! ", "? ", or a newline).
            # Using boundary anchors prevents cutting on phrases that appear
            # naturally mid-sentence, e.g. "...systems relying on related studies,
            # or requiring exact word matching..." should NOT be cut.
            intro_raw: str = sections_raw.get("introduction", "")
            if intro_raw:
                # Each pattern requires the heading to follow a sentence-end or newline.
                # (?:^|\.\s+|\!\s+|\?\s+|\n\s*) = start of string OR end of sentence.
                INTRO_INLINE_CUT = [
                    # Distinctive phrases — safe to match anywhere after a boundary
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Background\s+of\s+the\s+Study\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Project\s+Context\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Context\s+of\s+the\s+(?:Study|Project)\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Purpose\s+of\s+the\s+(?:Study|Project)\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Statement\s+of\s+the\s+Problem\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Objectives?\s+of\s+the\s+Study\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Research\s+Objectives?\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Significance\s+of\s+the\s+Study\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Scope\s+and\s+(?:Delimitation|Limitation)\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Definition\s+of\s+Terms\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Conceptual\s+Framework\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Theoretical\s+Framework\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Review\s+of\s+(?:Related\s+)?Literature\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Related\s+(?:Works?|Studies)\s+(?:and\s+Literature\s+)?(?:show|discuss|suggest|indicate|reveal|demonstrate|present|provide|highlight|support|confirm|show|include)\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Hypothes[ie]s\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Research\s+Locale\b",
                    r"(?:^|\.\s+|\!\s+|\?\s+|\n\s*)Research\s+Questions?\b",
                ]
                cut_pos = len(intro_raw)
                for pat in INTRO_INLINE_CUT:
                    m = re.search(pat, intro_raw, re.IGNORECASE | re.MULTILINE)
                    if m:
                        # Find the first alpha character in the match — that's
                        # where the heading word actually starts (skip ". " etc.)
                        heading_start = next(
                            (ci for ci in range(m.start(), m.end()) if intro_raw[ci].isalpha()),
                            m.start(),
                        )
                        if heading_start < cut_pos:
                            cut_pos = heading_start
                if cut_pos < len(intro_raw):
                    print(f"[OCR] Introduction inline-trimmed at pos {cut_pos} "
                          f"('{intro_raw[cut_pos:cut_pos+40].strip()}')")
                    sections_raw["introduction"] = intro_raw[:cut_pos].rstrip(" .,;")
            sections_summary: dict = {}
            try:
                sections_summary = imrad_summary_service.summarise_all(sections_raw)
                print(f"[IMRADSummary] Preview summaries generated: "
                      f"{[k for k, v in sections_summary.items() if v]}")
            except Exception as sum_err:
                print(f"[IMRADSummary] Preview generation failed (non-fatal): {sum_err}")

            metadata = {
                "title":                detected_title,
                "author":               final_author,
                "year":                 detected_year,
                "abstract":             abstract_text,
                "department":           detected_dept,
                "keywords":             detected_keywords,
                "degree_program":       detected_degree,
                "project_type":         detected_project_type,
                "citation_count":       0,
                "detected_subheadings": detected_subs,
                "sections":             sections_raw,
                "sections_summary":     sections_summary,
                "section_pages":        extracted_imrad.get("section_pages", {}),
                # Flat list of preview page numbers — popped in papers.py before
                # the response is sent to the frontend.
                "imrad_pages":          extracted_imrad.get("imrad_pages", []),
            }

            print("Successfully finished extraction.")
            return metadata

        except Exception as e:
            print(f"CRITICAL Extraction Error: {type(e).__name__} - {e}")
            return {
                "title":          os.path.basename(pdf_path),
                "author":         "Unknown",
                "year":           "N/A",
                "abstract":       f"Extraction failed: {str(e)}",
                "department":     "N/A",
                "keywords":       "",
                "project_type":   "N/A",
                "degree_program": "N/A",
                "citation_count": 0,
                "imrad_pages":    [],
            }

    async def extract_page_previews(
        self,
        pdf_path: str,
        imrad_pages: Optional[List[int]] = None,
    ):
        """
        Extracts base64 thumbnails and text snippets for PDF pages.

        Args:
            pdf_path:    Path to the PDF.
            imrad_pages: If supplied, only these page numbers are rendered.
                         Pass None to render all pages (fallback/manual mode).

        Fixes vs original:
        - Converts one page at a time (first_page=N, last_page=N) so page N
          always maps to the correct image regardless of Poppler behaviour.
        - Accepts imrad_pages to skip non-IMRAD pages entirely, so the
          frontend review screen only shows relevant pages.
        """
        previews = []
        try:
            reader    = PdfReader(pdf_path)
            num_pages = len(reader.pages)

            pages_to_render = imrad_pages if imrad_pages else list(range(1, num_pages + 1))

            for page_num in pages_to_render:
                if page_num < 1 or page_num > num_pages:
                    continue

                page_text    = reader.pages[page_num - 1].extract_text() or ""
                preview_text = page_text[:200].strip()

                img_str = ""
                try:
                    images = convert_from_path(
                        pdf_path,
                        dpi=72,
                        first_page=page_num,
                        last_page=page_num,
                    )
                    if images:
                        buffered = BytesIO()
                        images[0].save(buffered, format="JPEG", quality=60)
                        img_str = base64.b64encode(buffered.getvalue()).decode()
                except Exception as page_err:
                    print(f"Thumbnail error on page {page_num}: {page_err}")
                    from PIL import Image as PILImage
                    placeholder = PILImage.new("RGB", (1, 1), color=(200, 200, 200))
                    buffered    = BytesIO()
                    placeholder.save(buffered, format="JPEG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()

                previews.append({
                    "page_num":     page_num,
                    "thumbnail":    img_str,
                    "preview_text": preview_text,
                })

        except Exception as e:
            print(f"Error extracting page previews: {e}")

        return previews


ocr_service = OCRService()