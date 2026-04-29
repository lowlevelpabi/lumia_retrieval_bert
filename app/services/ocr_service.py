import easyocr
import numpy as np
from PIL import Image
from pdf2image import convert_from_path
import os
from typing import Dict, Any, List, Optional

import re
import base64
from io import BytesIO
from pypdf import PdfReader
from app.services.imrad_service import imrad_service
from app.services.imrad_summary_service import imrad_summary_service
from app.services.logging_service import log
from app.core.task_manager import task_manager

# ── Test flag: set True to skip pypdf and always use EasyOCR ──────────────────
# WARNING: Kung gusto nyo masayang ang inyong mga precious time, i-True nyo yung value
# sa ibaba or ng variable FORCE_OCR: bool :) Happy waiting and wasting time kneegers.
FORCE_OCR: bool = True
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Extraction Controls
# ─────────────────────────────────────────────────────────────────────────────
ENABLE_TABLE_EXTRACTION: bool = False

class OCRService:
    def __init__(self):
        log.info("Initializing EasyOCR (English)")
        try:
            self.reader = easyocr.Reader(['en'], gpu=False)
            self.ocr_available = True
            log.success("EasyOCR initialized")
        except Exception as e:
            log.error("EasyOCR initialization failed", exc=e)
            self.ocr_available = False

    async def extract_metadata(self, pdf_path: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        import asyncio
        return await asyncio.to_thread(self.extract_metadata_sync, pdf_path, session_id)

    def extract_metadata_sync(self, pdf_path: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        log.section(f"Extracting — {os.path.basename(pdf_path)}")
        try:
            log.info("Direct text extraction via pypdf...")
            if session_id: task_manager.update_task(session_id, 10, "Loading PDF...")
            reader = PdfReader(pdf_path)
            num_pages = len(reader.pages)
            log.info("PDF loaded", pages=num_pages)
            # ... all the existing logic from extract_metadata ...

            # ── Full page map for IMRAD (all pages) ───────────────────────────
            page_text_map: Dict[int, str] = {}
            for i in range(num_pages):
                p_text = reader.pages[i].extract_text()
                if p_text:
                    page_text_map[i + 1] = p_text

            MAX_OCR_SUPPLEMENT_PAGES = 30

            empty_pages = [
                pg for pg in range(1, num_pages + 1)
                if len(page_text_map.get(pg, "").strip()) < 150
            ]

            if empty_pages:
                if session_id: task_manager.update_task(session_id, 20, f"OCR Supplement: {len(empty_pages)} scanned pages...")
                capped = empty_pages[:MAX_OCR_SUPPLEMENT_PAGES]
                log.info("Running OCR supplement on low-text pages",
                         total=len(empty_pages), processing=len(capped),
                         pages=str(capped[:10]))

                # Probe Tesseract once before the loop
                _tesseract_ok = False
                try:
                    import pytesseract
                    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' # wag nyo baguhin to, default na yan kung san naka lagay tesseract nyo
                    pytesseract.get_tesseract_version()
                    _tesseract_ok = True
                except Exception:
                    _tesseract_ok = False
                
                if _tesseract_ok:
                    log.info("OCR supplement engine: Tesseract (fast)")
                else:
                    log.info("Tesseract not found or configured — OCR supplement engine: EasyOCR (slow)")

                for pg_num in capped:
                    try:
                        imgs = convert_from_path(
                            pdf_path, dpi=150,
                            first_page=pg_num, last_page=pg_num,
                        )
                        if not imgs:
                            continue
                        ocr_text = ""
                        if _tesseract_ok:
                            import pytesseract
                            ocr_text = pytesseract.image_to_string(
                                imgs[0],
                                config="--psm 6 --oem 1",
                            ).strip()
                        elif self.ocr_available:
                            img_np = np.array(imgs[0])
                            ocr_results = self.reader.readtext(img_np, detail=0)
                            ocr_text = "\n".join(ocr_results).strip()
                        if ocr_text:
                            page_text_map[pg_num] = ocr_text
                    except Exception as pg_err:
                        log.error("OCR supplement failed", exc=pg_err, page=pg_num)

            log.info("Page map after OCR supplement",
                     covered=f"{len(page_text_map)}/{num_pages}")

            # ── Meta text for title/author/abstract (first 10 pages only) ────
            meta_text = ""
            for i in range(min(10, num_pages)):
                meta_text += page_text_map.get(i + 1, "") + "\n"

            log.info("pypdf meta text extracted", chars=len(meta_text))

            if FORCE_OCR or len(meta_text.strip()) < 50:
                log.warn("Direct extraction insufficient — falling back to OCR for meta pages")
                # Tesseract first (milliseconds/page); EasyOCR only if unavailable.
                # Only pages 1-3 needed for title / author / abstract.
                _meta_tess_ok = False
                try:
                    import pytesseract
                    pytesseract.get_tesseract_version()
                    _meta_tess_ok = True
                except Exception:
                    pass

                if _meta_tess_ok:
                    try:
                        import pytesseract
                        log.info("Meta OCR engine: Tesseract")
                        images = convert_from_path(pdf_path, dpi=200,
                                                   first_page=1, last_page=5)
                        for i, img in enumerate(images):
                            log.info("Tesseract processing page", page=i + 1)
                            meta_text += pytesseract.image_to_string(
                                img, config="--psm 6 --oem 1"
                            ).strip() + "\n"
                    except Exception as tess_err:
                        log.error("Tesseract meta fallback failed", exc=tess_err)
                elif self.ocr_available:
                    try:
                        log.info("Meta OCR engine: EasyOCR")
                        images = convert_from_path(pdf_path, first_page=1, last_page=3)
                        for i, img in enumerate(images):
                            log.info("EasyOCR processing page", page=i + 1)
                            img_np = np.array(img)
                            results = self.reader.readtext(img_np, detail=0)
                            meta_text += "\n".join(results) + "\n"
                    except Exception as ocr_err:
                        log.error("EasyOCR meta fallback failed", exc=ocr_err)
                else:
                    log.warn("No OCR engine available for meta extraction")

            lines = [line.strip() for line in meta_text.split('\n') if line.strip()]

            # ── Year ──────────────────────────────────────────────────────────
            year_match = re.search(r'\b(20[1-2][0-9])\b', meta_text)
            detected_year = year_match.group(1) if year_match else "N/A"

            # ── Title ─────────────────────────────────────────────────────────
            TITLE_STOP_PATTERNS = [
                r'\b(submitted|presented|in partial|fulfillment|requirements|degree|bachelor|undergraduate|thesis|capstone|adviser|supervisor|prepared)\b',
                r'\b(cavite|university|college|department|campus)\b',
                # "imus" only stops when paired with campus/city context
                r'\bimus\s+campus\b',
                r'^imus\s*city',
                r'^(by|presented by|submitted by)$',
                r'\b(20[1-2][0-9])\b',
            ]
            # Case-sensitive anchored patterns for author names to avoid matching title fragments
            NAME_STOP_PATTERNS = [
                r'^[A-Z]{2,},\s+[A-Z]{2,}(?:\s+[A-Z][A-Z\s\.]*)?$', # ALL CAPS: REYES, YNAA M.
                r'^[A-Z][a-z]+,\s+[A-Z][a-z]+(?:\s+[A-Z][A-Z\s\.]*)?$', # Title Case: Reyes, Ynaa M.
            ]
            title_lines = []
            for line in lines[:15]:
                # Title fragments sometimes contain commas (e.g. "ASSESSMENT, AND DATA LOGGING").
                # We only consider it a 'Name Stop' if it lacks common title words like AND, OR, FOR, OF.
                is_name_stop = any(re.match(p, line) for p in NAME_STOP_PATTERNS) and not re.search(r'\b(AND|OR|FOR|OF|THE|WITH|ON|IN|A|TO)\b', line, re.IGNORECASE)
                is_stop = any(re.search(p, line, re.IGNORECASE) for p in TITLE_STOP_PATTERNS) or is_name_stop
                looks_like_title = (
                    len(line) > 3 and
                    not is_stop
                )
                if looks_like_title:
                    title_lines.append(line)
                elif title_lines:
                    break

            detected_title = " ".join(title_lines).strip() if title_lines else os.path.basename(pdf_path)
            detected_title = re.sub(r'\s+', ' ', detected_title)

            '''
            print(f"\n===== [OCR DIAGNOSIS] First 80 lines =====")
            for i, l in enumerate(lines[:80]):
                print(f"  [{i:02d}] {repr(l)}")
            print("=====  [END DIAGNOSIS] =====\n")
            '''
            
            # ── Authors ───────────────────────────────────────────────────────
            COVER_END_ANCHORS = re.compile(
                r'(?:^|\n)(?:'
                r'BIOGRAPHICAL\s+DATA|BIOGRAPHY|ABOUT\s+THE\s+AUTHORS?|'
                r'ACKNOWLEDGMENT|TABLE\s+OF\s+CONTENTS'
                r')\b',
                re.IGNORECASE
            )
            raw_cover = meta_text[:6000]
            end_match = COVER_END_ANCHORS.search(raw_cover)
            cover_text = raw_cover[:end_match.start()].strip() if end_match else raw_cover

            # Also stop at the first roman-numeral page marker (iii, iv, v…)
            # which marks the start of front-matter beyond the title page
            roman_pg = re.search(r'\n\s*(iii|iv|vi|vii|viii)\s*\n', cover_text, re.IGNORECASE)
            if roman_pg:
                cover_text = cover_text[:roman_pg.start()].strip()

            log.regex("Author scan region",
                      chars=len(cover_text),
                      truncated_at=repr(end_match.group().strip()[:30]) if end_match else "none")

            detected_authors = []

            # Matches 2 to 7 word lines, allowing initials anywhere
            NAME_LINE_RE = re.compile(
                r'^[A-Z][a-zA-Z\-\.\,\ñ\Ñ]+(?:\s+[a-zA-Z\-\.\,\ñ\Ñ]+){1,6}$'
            )
            NOISE_LINE_RE = re.compile(
                r'\b(University|College|Department|Campus|Cavite|Bachelor|'
                r'Science|Thesis|Capstone|Submitted|Partial|Fulfillment|'
                r'Requirements|Prepared|Supervision|Adviser)\b',
                re.IGNORECASE
            )

            # ── STRATEGY 1: Names above a "Month Year" date line (Structural) ──
            date_match = re.search(
                r'(?:January|February|March|April|May|June|July|August|September|'
                r'October|November|December)\s+20\d{2}',
                cover_text
            )
            if date_match:
                chunk_before_date = cover_text[max(0, date_match.start() - 600) : date_match.start()]
                lines_before = [l.strip() for l in chunk_before_date.split('\n') if l.strip()]

                for line in reversed(lines_before):
                    if NAME_LINE_RE.match(line) and not NOISE_LINE_RE.search(line):
                        detected_authors.insert(0, re.sub(r'\s+', ' ', line))
                    elif detected_authors:
                        break
                detected_authors = detected_authors[:5]

            # ── STRATEGY 2: Look for "Contribution No." block (Structural) ──
            if not detected_authors:
                contrib_match = re.search(
                    r'Contribution\s+No\.?',
                    cover_text, re.IGNORECASE
                )
                if contrib_match:
                    chunk = cover_text[max(0, contrib_match.start() - 500) : contrib_match.start()]
                    clines = [l.strip() for l in chunk.split('\n') if l.strip()]
                    for line in reversed(clines):
                        if NAME_LINE_RE.match(line) and not NOISE_LINE_RE.search(line):
                            detected_authors.insert(0, re.sub(r'\s+', ' ', line))
                        elif detected_authors:
                            break
                    detected_authors = detected_authors[:5]

            # ── STRATEGY 3: Explicit Labels (e.g., "Prepared by") ──
            if not detected_authors:
                by_match = re.search(
                    r'(?:by|submitted by|presented by|prepared by|authors?)[:\s]+'
                    r'([A-Z][a-zA-Z\s\.\,\ñ\Ñ]+?)'
                    r'(?=\n|submitted|prepared|adviser|department|college|cavite|\Z)',
                    cover_text, re.IGNORECASE
                )
                if by_match:
                    raw_by = by_match.group(1).strip()
                    candidates = [l.strip() for l in re.split(r'[\n;]', raw_by) if l.strip()]
                    for c in candidates[:5]:
                        if len(c.split()) >= 2:
                            detected_authors.append(re.sub(r'\s+', ' ', c))

            # ── STRATEGY 4: ALL CAPS "LAST, FIRST" Anywhere (Fallback) ──
            if not detected_authors:
                cover_text_flat = re.sub(r'\s+', ' ', cover_text)
                all_caps_names = re.findall(
                    r'\b([A-ZÑ]{2,20}(?:[ \-]+[A-ZÑ]{2,20})?,[ ]+[A-ZÑ]{2,20}(?:[ ]+[A-ZÑ]{2,20}){0,2}(?:[ ]+[A-ZÑ]\.)?)\b',
                    cover_text_flat
                )
                all_caps_names = [m.strip() for m in all_caps_names]
                if all_caps_names:
                    NAME_NOISE = re.compile(
                        r'\b(UNIVERSITY|COLLEGE|DEPARTMENT|CAMPUS|CAVITE|BACHELOR|SCIENCE|'
                        r'THESIS|CAPSTONE|SUBMITTED|PARTIAL|FULFILLMENT|REQUIREMENTS|'
                        r'DEVELOPMENTAL|APPROVAL|PROPOSAL|RESEARCH|DEGREE|COURSE|'
                        r'ADVISER|CHAIRPERSON|COORDINATOR|ADMINISTRATOR|CRITIC)\b'
                    )
                    GEO_NOISE = re.compile(
                        r'\b(Cavite|Manila|Imus|Bacoor|Laguna|Batangas|Quezon|Makati|'
                        r'Pasig|Taguig|Paranaque|Caloocan|Malabon|Muntinlupa|'
                        r'Metro|City|Province|Municipality|Barangay|Street|Avenue|'
                        r'Subdivision|Village|Compound|Block|Lot|Phase|'
                        r'January|February|March|April|May|June|July|August|'
                        r'September|October|November|December|Monday|Tuesday|'
                        r'Wednesday|Thursday|Friday|Saturday|Sunday)\b',
                        re.IGNORECASE
                    )
                    seen_upper = set()
                    filtered = []
                    for n in all_caps_names:
                        clean = re.sub(r'\s+', ' ', n).strip()
                        key   = clean.upper()
                        if not NAME_NOISE.search(clean) and not GEO_NOISE.search(clean) and len(clean.split()) >= 2 and key not in seen_upper:
                            filtered.append(clean)
                            seen_upper.add(key)
                    if filtered:
                        detected_authors = filtered[:5]

            # ── STRATEGY 5: Title Case Anywhere (Fallback) ──
            if not detected_authors:
                title_case_names = re.findall(
                    r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]*)*(?:\s+[A-Z]\.)?(?=\s|$|\n)',
                    cover_text
                )
                if title_case_names:
                    GEO_NOISE = re.compile(
                        r'\b(Cavite|Manila|Imus|Bacoor|Laguna|Batangas|Quezon|Makati|'
                        r'Pasig|Taguig|Paranaque|Caloocan|Malabon|Muntinlupa|'
                        r'Metro|City|Province|Municipality|Barangay|Street|Avenue|'
                        r'Subdivision|Village|Compound|Block|Lot|Phase|'
                        r'January|February|March|April|May|June|July|August|'
                        r'September|October|November|December|Monday|Tuesday|'
                        r'Wednesday|Thursday|Friday|Saturday|Sunday)\b',
                        re.IGNORECASE
                    )
                    filtered_tc = [
                        re.sub(r'\s+', ' ', n).strip()
                        for n in title_case_names
                        if not GEO_NOISE.search(n)
                    ]
                    if filtered_tc:
                        detected_authors = filtered_tc[:5]

            # Deduplicate final author list (safety net for all strategies)
            seen = set()
            unique_authors = []
            for a in detected_authors:
                key = re.sub(r'\s+', ' ', a).strip().upper()
                if key not in seen:
                    unique_authors.append(a)
                    seen.add(key)
            detected_authors = unique_authors[:5]

            author_fallback = "The system couldn't confidently detect any authors. Please click '+ Add Another Author' below to enter them manually."
            final_author = " | ".join(detected_authors) if detected_authors else author_fallback

            # ── Abstract ──────────────────────────────────────────────────────
            # ── Line-level skip patterns ───────────────────────────────────────
            ABSTRACT_SKIP_PATTERNS = [
                r"^An undergraduate thesis(?:\s+outline)?\s+submitted$",
                r"^Cavite\s+State\s+University$",
                r"^CvSU$",
                r"^Imus\s+Campus$",
                r"^Imus\s+City$",
                r"^in\s+partial\s+fulfillment$",
                r"^requirements\s+for\s+the\s+degree$",
                r"^Bachelor\s+of\s+Science$",
                r"^Prepared\s+under\s+the\s+supervision$",
                r"^Adviser\s*:$",
                r"^Department\s+of\s+[A-Za-z\s]+$",
                r"^College\s+of\s+[A-Za-z\s]+$",
                r"^Contribution\s+No\.?$",
                r"^undergraduate\s+thesis$",
                r"^(?:January|February|March|April|May|June|July|August|"
                r"September|October|November|December)\s+20\d{2}$",
                r"^20[1-2]\d$",
            ]
            if detected_title and detected_title not in ("N/A", "Untitled", ""):
                ABSTRACT_SKIP_PATTERNS.append(
                    re.escape(detected_title.strip().rstrip("."))
                )
                for _frag in detected_title.split():
                    if len(_frag) > 8:
                        ABSTRACT_SKIP_PATTERNS.append(fr"^{re.escape(_frag)}$")
            if detected_authors:
                for _auth in detected_authors:
                    ABSTRACT_SKIP_PATTERNS.append(re.escape(_auth.strip()))

            def _is_abstract_boilerplate(line: str) -> bool:
                """Return True if this line is institutional header content."""
                if not line:
                    return True
                if re.match(r'^\d+$', line) or re.match(r'^[ivxIVX]+$', line):
                    return True
                if line.upper() in ("ABSTRACT", "SUMMARY", "ABSTRACT:", "SUMMARY:"):
                    return True
                if any(re.search(p, line, re.IGNORECASE) for p in ABSTRACT_SKIP_PATTERNS):
                    return True
                # ALL-CAPS author line  e.g. "BILLONES, PRINCE ISIAH R."
                if re.match(r'^[A-Z]{2,}(?:\s+[A-Z]+)*,\s+[A-Z]+', line):
                    return True
                # Title-case author line  e.g. "Billones, Prince Isiah R."
                if re.match(r'^[A-Z][a-z]+,\s+[A-Z][a-z]+', line):
                    return True
                return False

            abstract_text = ""
            found_start   = -1
            for pattern in [r'\bABSTRACT\b', r'\bSUMMARY\b', r'\bAbstract\b']:
                match = re.search(pattern, meta_text)
                if match:
                    # ── Strict Header Gate ──
                    # We only care about text AFTER the 'ABSTRACT' heading.
                    # Anything before it (University Name, Address, etc.) is noise.
                    found_start = match.end()
                    break

            if found_start != -1:
                abstract_text_raw = meta_text[found_start:].strip()

                # ── Step 1: Smart Slice for Merged Lines ──
                # If the OCR merges the header and body into a single line, line-by-line fails.
                # We find the 'Adviser' or 'Date' terminus and slice everything before it.
                search_window = abstract_text_raw[:1200]
                last_terminus = None
                
                # 1a. Look for Adviser (Supports Ms., names with ñ, etc.)
                for m in re.finditer(r'Adviser\s*[:\s]+[A-Za-zñÑ\s\.\-]{2,50}\.', search_window, re.IGNORECASE):
                    last_terminus = m
                    
                # 1b. Fallback to Date, but ONLY if it appears very early (< 400 chars)
                # This prevents matching dates like "July 2024" inside the abstract body.
                if not last_terminus:
                    for m in re.finditer(r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2}\.', search_window[:400], re.IGNORECASE):
                        last_terminus = m

                if last_terminus:
                    abstract_text_raw = abstract_text_raw[last_terminus.end():].strip()

                # ── Step 2: line-by-line skip for remaining boilerplate ────────
                raw_lines     = abstract_text_raw.split('\n')
                cleaned_lines = []
                start_collecting = False

                # We use a set of markers that indicate the DEFINITIVE start of the next section
                # to avoid accidental cut-offs.
                STOP_MARKERS = {
                    "TABLE OF CONTENTS", "ACKNOWLEDGMENT", "LIST OF TABLES",
                    "LIST OF FIGURES", "INTRODUCTION", "CHAPTER I", "CHAPTER 1",
                    "APPROVAL SHEET", "BIOGRAPHICAL DATA", "DEDICATION"
                }

                for line in raw_lines:
                    line = line.strip()
                    if not line:
                        continue

                    if not start_collecting:
                        # ── Explicit Body Start Detection ──
                        # If a line starts with these common phrases, it's DEFINITELY the abstract body.
                        if any(line.lower().startswith(w) for w in ["this study", "the research", "the objective", "this research"]):
                            start_collecting = True
                        
                        elif _is_abstract_boilerplate(line):
                            continue
                        
                        # Softened gate: allow more varied starting sentences.
                        if len(line) < 15 and not any(line.lower().startswith(w) for w in ["this", "the", "in", "with", "a", "an"]):
                            continue
                        
                        start_collecting = True
                    
                    if start_collecting:
                        # Page numbers or small fragments (e.g. "iii", "viii")
                        if re.match(r'^\d+$', line) or re.match(r'^[ivxIVX]+$', line):
                            continue
                        
                        upper_line = line.upper()
                        
                        # Stop ONLY if it's a definitive, standalone section header.
                        if upper_line in STOP_MARKERS:
                            if len(line) < 30:
                                break
                            
                        # Stop at an ALL-CAPS section heading (Chapter II, etc)
                        if re.match(r'^CHAPTER\s+[IVX\d]+', upper_line):
                            break
                            
                        # Keywords often mark the end of the abstract body
                        if re.match(r'^Keywords?\s*:', line, re.IGNORECASE):
                            cleaned_lines.append(line)
                            break

                        cleaned_lines.append(line)

                abstract_text = " ".join(cleaned_lines)

                # Hard stop safety net (still needed for non-line-broken text)
                for stop in STOP_MARKERS:
                    # Look for stop word followed by a newline or significant space
                    # to avoid cutting off mid-sentence words that happen to contain 'Introduction'
                    pattern = rf'\b{re.escape(stop)}\b'
                    match = re.search(pattern, abstract_text.upper())
                    if match and match.start() > 600: # Increase buffer to prevent cutting off early
                        abstract_text = abstract_text[:match.start()].strip()
                        break

                # Strip trailing page numbers or roman footers that may have merged with the last sentence
                abstract_text = re.sub(r'\s+(?:\d+|[ivxIVX]+)\s*$', '', abstract_text)
                
                # Only truncate if extremely long (abstracts shouldn't be > 15k chars)
                abstract_text = abstract_text[:15000].strip()

            if not abstract_text or len(abstract_text) < 100 or len(meta_text) < 200:
                log.warn("Abstract extraction insufficient — no OCR fallback for text-based PDFs")

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
            # Require keyword label at LINE START to avoid matching 'keyword'
            # mid-sentence in abstract body (e.g. 'keyword-based search...')
            detected_keywords = ""
            kw_match = re.search(
                r'(?:^|\n)[Kk]eywords?\s*[:\-\u2013]\s*(.+?)(?:\n\n|\n[A-Z]|$)',
                meta_text, re.DOTALL
            )
            if kw_match:
                raw_kw = re.sub(r'\s+', ' ', kw_match.group(1).strip())
                # Real keyword list has commas/semicolons separating short terms.
                # Body text captured by mistake is long with no separators.
                has_separator = bool(re.search(r'[,;]', raw_kw))
                if has_separator or len(raw_kw) <= 80:
                    detected_keywords = raw_kw[:300]
                else:
                    log.regex("Keyword match rejected — no separator and >80 chars",
                              sample=repr(raw_kw[:60]))

            if not abstract_text or len(abstract_text.strip()) < 50:
                abstract_text = "The author of this study doesn't provide any abstract, perhaps it is still in manuscript phase or incomplete study."

            # ── IMRAD Extraction ──────────────────────────────────────────────
            extracted_imrad = {"sections": {}, "section_pages": {}, "imrad_pages": []}
            detected_subs   = []
            try:
                # 1. Primary extraction (identify sections and pages)
                if session_id: task_manager.update_task(session_id, 45, "Classifying IMRaD sections...")
                extracted_imrad = imrad_service.extract_sections(
                    page_text_map,
                    title=detected_title,
                    authors=final_author,
                    pdf_path=pdf_path
                )

                # 2. Section pages for specialized scans
                full_sec_pages = extracted_imrad.get("full_section_pages", {})
                methods_pages = full_sec_pages.get("methods") or extracted_imrad.get("section_pages", {}).get("methods", [])
                results_pages = (
                    full_sec_pages.get("results_and_discussion")
                    or full_sec_pages.get("results")
                    or extracted_imrad.get("section_pages", {}).get("results_and_discussion", [])
                    or extracted_imrad.get("section_pages", {}).get("results", [])
                )

                detected_subs = imrad_service.detect_subheadings(
                    page_text_map=page_text_map,
                    methods_pages=methods_pages,
                    results_pages=results_pages,
                )
            except Exception as imrad_err:
                log.error("IMRAD extraction failed (non-fatal)", exc=imrad_err)

            # ── Pre-generate IMRAD summaries ──────────────────────────────────
            if session_id: task_manager.update_task(session_id, 85, "Preparing extracted contents...")
            sections_raw: dict = extracted_imrad.get("sections", {})

            sections_summary: dict = {}
            try:
                sections_summary = imrad_summary_service.summarise_all(sections_raw)
                log.success("IMRAD summaries generated",
                            sections=str([k for k, v in sections_summary.items() if v]))
            except Exception as sum_err:
                log.error("IMRAD summary generation failed (non-fatal)", exc=sum_err)

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
                "references":           sections_raw.get("references", ""),
                "section_pages":        extracted_imrad.get("section_pages", {}),
                "media":                extracted_imrad.get("media", {}),
                "imrad_pages":          extracted_imrad.get("imrad_pages", []),
            }

            log.success("Extraction complete", file=os.path.basename(pdf_path))
            return metadata

        except Exception as e:
            log.error("CRITICAL extraction error", exc=e)
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

    def quick_metadata_sync(self, pdf_path: str) -> Dict[str, Any]:
        """
        Ultra-fast metadata extraction using only the first few pages and direct text.
        Used for instant duplicate detection (Guard Rail) before heavy processing starts.
        """
        try:
            reader = PdfReader(pdf_path)
            num_pages = len(reader.pages)
            
            # Extract text from first 3 pages quickly
            meta_text = ""
            for i in range(min(3, num_pages)):
                text = reader.pages[i].extract_text()
                if text: meta_text += text + "\n"
                
            if len(meta_text.strip()) < 50:
                # If pypdf fails (likely a scan), try a light-weight OCR on Page 1 ONLY
                try:
                    import pytesseract
                    from pdf2image import convert_from_path
                    # Use lower DPI for speed
                    imgs = convert_from_path(pdf_path, dpi=120, first_page=1, last_page=1)
                    if imgs:
                        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                        ocr_text = pytesseract.image_to_string(imgs[0], config="--psm 6 --oem 1").strip()
                        if ocr_text: meta_text = ocr_text + "\n"
                except Exception:
                    pass

            if len(meta_text.strip()) < 50:
                return {"title": os.path.basename(pdf_path), "author": "Unknown", "year": "N/A"}

            # Reuse the existing regex strategies for Title, Author, Year
            # (Extracted into this simplified version for the quick check)
            
            # Year
            year_match = re.search(r'\b(20[1-2][0-9])\b', meta_text)
            detected_year = year_match.group(1) if year_match else "N/A"

            # Title
            TITLE_STOP_PATTERNS = [
                r'\b(submitted|presented|in partial|fulfillment|requirements|degree|bachelor|undergraduate|thesis|capstone|adviser|supervisor|prepared)\b',
                r'\b(cavite|university|college|department|campus)\b',
                r'\b(20[1-2][0-9])\b',
            ]
            lines = [l.strip() for l in meta_text.split('\n') if l.strip()]
            title_lines = []
            for line in lines[:15]:
                is_stop = any(re.search(p, line, re.IGNORECASE) for p in TITLE_STOP_PATTERNS)
                if len(line) > 3 and not line.endswith('.') and not is_stop:
                    title_lines.append(line)
                elif title_lines: break
            detected_title = " ".join(title_lines).strip() or os.path.basename(pdf_path)

            # Authors (Strategy 1 & 4 combination)
            detected_authors = []
            all_caps_names = re.findall(
                r'(?:^|\n)([A-Z]{2,20}(?:[ ]+[A-Z]{2,20})?,[ ]+[A-Z]{2,20}(?:[ ]+[A-Z]{2,20}){0,2}(?:[ ]+[A-Z]\.)?)(?=[ ]*$|[ ]*\n)',
                meta_text, re.MULTILINE
            )
            if all_caps_names:
                detected_authors = [m.strip() for m in all_caps_names][:5]
            else:
                by_match = re.search(r'(?:by|submitted by|prepared by)[:\s]+([A-Z][a-zA-Z\s\.\,]+)', meta_text, re.IGNORECASE)
                if by_match:
                    raw_by = by_match.group(1).strip().split('\n')[0]
                    if len(raw_by.split()) >= 2: detected_authors = [raw_by]

            return {
                "title": re.sub(r'\s+', ' ', detected_title),
                "author": " | ".join(detected_authors) if detected_authors else "Unknown",
                "year": detected_year
            }
        except Exception:
            return {"title": os.path.basename(pdf_path), "author": "Unknown", "year": "N/A"}

    async def extract_page_previews(
        self,
        pdf_path: str,
        imrad_pages: Optional[List[int]] = None,
        session_id: Optional[str] = None
    ):
        import asyncio
        return await asyncio.to_thread(self.extract_page_previews_sync, pdf_path, imrad_pages, session_id)

    def extract_page_previews_sync(
        self,
        pdf_path: str,
        imrad_pages: Optional[List[int]] = None,
        session_id: Optional[str] = None
    ):
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
                    log.error(f"Thumbnail render failed", exc=page_err, page=page_num)
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
            log.error("Page preview extraction failed", exc=e)

        return previews

ocr_service = OCRService()