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
                r'\b(cavite|university|college|department|campus)\b',
                # "imus" only stops when paired with campus/city context —
                # NOT when it appears in a title phrase like "FOR PESO IMUS"
                r'\bimus\s+campus\b',
                r'^imus\s*city',
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
            # Step 1: truncate cover_text at the first biographical/back-matter
            # boundary. Everything after "BIOGRAPHICAL DATA", "BIOGRAPHY",
            # "ACKNOWLEDGMENT", page-number-only lines like "iii", or approval
            # sheet anchors is noise — addresses, dates, and place names in bios
            # look exactly like author names to any regex.
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

            print(f"[OCR] Author scan region: {len(cover_text)} chars "
                  f"({'truncated at: ' + repr(end_match.group().strip()[:30]) if end_match else 'full cover'})")

            detected_authors = []

            # Strategy 1: ALL CAPS "LAST, FIRST [MIDDLE] [MI.]"
            # Tightened regex: last name is 2–20 chars (prevents long noise words
            # like DEVELOPMENTAL prepending to a real name), and the whole match
            # must sit on its own line (anchored by line boundaries or newlines).
            # e.g. BILLONES, PRINCE ISIAH R.  /  DELA CRUZ, JUAN CARLO
            all_caps_names = re.findall(
                # Use [ ]+ (literal space) not \s+ so the regex never
                # crosses newlines and merges two author names into one.
                r'(?:^|\n)([A-Z]{2,20}(?:[ ]+[A-Z]{2,20})?,[ ]+[A-Z]{2,20}(?:[ ]+[A-Z]{2,20}){0,2}(?:[ ]+[A-Z]\.)?)(?=[ ]*$|[ ]*\n)',
                cover_text, re.MULTILINE
            )
            # re.findall with a group returns only the group — strip whitespace
            all_caps_names = [m.strip() for m in all_caps_names]
            if all_caps_names:
                NAME_NOISE = re.compile(
                    r'\b(UNIVERSITY|COLLEGE|DEPARTMENT|CAMPUS|CAVITE|BACHELOR|SCIENCE|'
                    r'THESIS|CAPSTONE|SUBMITTED|PARTIAL|FULFILLMENT|REQUIREMENTS|'
                    r'DEVELOPMENTAL|APPROVAL|PROPOSAL|RESEARCH|DEGREE|COURSE|'
                    r'ADVISER|CHAIRPERSON|COORDINATOR|ADMINISTRATOR|CRITIC)\b'
                )
                # Deduplicate while preserving order
                seen_upper = set()
                filtered = []
                for n in all_caps_names:
                    clean = re.sub(r'\s+', ' ', n).strip()
                    key   = clean.upper()
                    if not NAME_NOISE.search(clean) and len(clean.split()) >= 2 and key not in seen_upper:
                        filtered.append(clean)
                        seen_upper.add(key)
                if filtered:
                    detected_authors = filtered[:5]

            # Strategy 2: Title Case "Last, First [Middle] [MI.]"
            # e.g. Dela Cruz, Juan Carlo M.  /  Santos, Maria Anna
            # Geography filter blocks place names that match the Last, First pattern
            # e.g. "Imus, Cavite" / "Santa Cruz, Manila" / "City, Metro Manila"
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

            # Strategy 3: Names above a "Month Year" date line
            # Scans upward from the date — collects consecutive name-shaped lines
            # even if they have no trailing initial (handles missing MI. format)
            if not detected_authors:
                date_match = re.search(
                    r'(?:January|February|March|April|May|June|July|August|September|'
                    r'October|November|December)\s+20\d{2}',
                    cover_text
                )
                if date_match:
                    chunk_before_date = cover_text[max(0, date_match.start() - 600) : date_match.start()]
                    lines_before = [l.strip() for l in chunk_before_date.split('\n') if l.strip()]
                    NAME_LINE_RE = re.compile(
                        r'^[A-Z][a-zA-Z\-\.]+(?:\s+[A-Z][a-zA-Z\-\.]+){1,5}(?:\s+[A-Z]\.)?$'
                    )
                    NOISE_LINE_RE = re.compile(
                        r'\b(University|College|Department|Campus|Cavite|Bachelor|'
                        r'Science|Thesis|Capstone|Submitted|Partial|Fulfillment|'
                        r'Requirements|Prepared|Supervision|Adviser|April|January|'
                        r'February|March|May|June|July|August|September|October|'
                        r'November|December)\b',
                        re.IGNORECASE
                    )
                    for line in reversed(lines_before):
                        if NAME_LINE_RE.match(line) and not NOISE_LINE_RE.search(line):
                            detected_authors.insert(0, re.sub(r'\s+', ' ', line))
                        elif detected_authors:
                            # Stop only if we already collected some names — avoids
                            # breaking too early on blank institutional lines
                            break
                    detected_authors = detected_authors[:5]

            # Strategy 4: "LAST, FIRST" style anywhere near "by" / "Submitted by"
            # Handles formats that introduce authors with an explicit label
            if not detected_authors:
                by_match = re.search(
                    r'(?:by|submitted by|presented by|prepared by)[:\s]+'
                    r'([A-Z][a-zA-Z\s\.\,]+?)'
                    r'(?=\n|submitted|prepared|adviser|department|college|cavite|\Z)',
                    cover_text, re.IGNORECASE
                )
                if by_match:
                    raw_by = by_match.group(1).strip()
                    # Split on newlines or common separators to get individual names
                    candidates = [l.strip() for l in re.split(r'[\n;]', raw_by) if l.strip()]
                    for c in candidates[:5]:
                        if len(c.split()) >= 2:
                            detected_authors.append(re.sub(r'\s+', ' ', c))

            # Strategy 5: Look for "Contribution No." block — authors appear just before it
            # Many CvSU theses have "...prepared under the supervision of -. Contribution No.__"
            # and the authors are the 2–4 lines immediately before that block
            if not detected_authors:
                contrib_match = re.search(
                    r'Contribution\s+No\.?',
                    cover_text, re.IGNORECASE
                )
                if contrib_match:
                    chunk = cover_text[max(0, contrib_match.start() - 500) : contrib_match.start()]
                    clines = [l.strip() for l in chunk.split('\n') if l.strip()]
                    NAME_LINE_RE2 = re.compile(
                        r'^[A-Z][a-zA-Z\-\.]+(?:\s+[A-Z][a-zA-Z\-\.]+){1,5}(?:\s+[A-Z]\.)?$'
                    )
                    NOISE_LINE_RE2 = re.compile(
                        r'\b(University|College|Department|Campus|Cavite|Bachelor|'
                        r'Science|Thesis|Capstone|Submitted|Partial|Fulfillment|'
                        r'Requirements|Prepared|Supervision|Adviser|undergraduate)\b',
                        re.IGNORECASE
                    )
                    for line in reversed(clines):
                        if NAME_LINE_RE2.match(line) and not NOISE_LINE_RE2.search(line):
                            detected_authors.insert(0, re.sub(r'\s+', ' ', line))
                        elif detected_authors:
                            break
                    detected_authors = detected_authors[:5]

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
            # Two boilerplate formats exist in CvSU theses:
            #
            #   Format A — separator line present:
            #       ABSTRACT
            #       ─────────────────────────────────
            #       [Actual abstract prose starts here]
            #
            #   Format B — no separator (the problematic one shown in the image):
            #       ABSTRACT
            #
            #       Author1, Author2, Author3
            #       Title of Study. Degree. Institution. Month Year. Adviser: Name.
            #
            #       [Actual abstract prose starts here]
            #
            # In Format B the entire header block is 1–3 lines of continuous text.
            # The approach:
            #   Step 1 — strip the boilerplate PARAGRAPH as a whole chunk using
            #            a terminus pattern (Adviser: ...) so we skip it entirely
            #            even when it contains no newlines.
            #   Step 2 — fall back to the line-by-line skip for any remaining
            #            boilerplate lines that appear after the chunk.

            # ── Boilerplate terminus patterns ─────────────────────────────────
            # The inline boilerplate paragraph always ends with one of these:
            #   "Adviser: Name."  /  "Adviser's Name."  /  "Month YYYY."
            # Everything from the ABSTRACT keyword up to and including the
            # terminus is discarded before the line-by-line pass runs.
            # Takes the LAST terminus match — Adviser: always follows the date
            # so we correctly skip past both when both are present.
            BOILERPLATE_TERMINUS_RE = re.compile(
                r'(?:'
                r'Adviser\s*[:\s]+[A-Za-z][A-Za-z\s\.]{2,50}\.|'
                r'(?:January|February|March|April|May|June|July|August|'
                r'September|October|November|December)\s+20\d{2}\.'
                r')',
                re.IGNORECASE
            )

            # ── Line-level skip patterns ───────────────────────────────────────
            ABSTRACT_SKIP_PATTERNS = [
                r"An undergraduate thesis(?:\s+outline)?\s+submitted",
                r"Cavite\s+State\s+University",
                r"CvSU",
                r"Imus\s+Campus",
                r"Imus\s+City",
                r"in\s+partial\s+fulfillment",
                r"requirements\s+for\s+the\s+degree",
                r"Bachelor\s+of\s+Science",
                r"Prepared\s+under\s+the\s+supervision",
                r"Adviser\s*:",
                r"Department\s+of\s+[A-Za-z\s]+",
                r"College\s+of\s+[A-Za-z\s]+",
                r"Contribution\s+No\.?",
                r"undergraduate\s+thesis",
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
                    found_start = match.end()
                    break

            if found_start != -1:
                abstract_text_raw = meta_text[found_start:].strip()

                # ── Step 1: strip inline boilerplate paragraph (Format B) ─────
                # Find the last occurrence of a boilerplate terminus within the
                # first 1200 chars (the header block is never longer than that).
                # If found, discard everything up to and including that terminus.
                search_window = abstract_text_raw[:1200]
                last_terminus = None
                for m in BOILERPLATE_TERMINUS_RE.finditer(search_window):
                    last_terminus = m
                if last_terminus:
                    print(f"[OCR] Abstract boilerplate paragraph stripped "
                          f"(terminus: {repr(last_terminus.group()[:60])})")
                    abstract_text_raw = abstract_text_raw[last_terminus.end():].strip()

                # ── Step 2: line-by-line skip for remaining boilerplate ────────
                raw_lines     = abstract_text_raw.split('\n')
                cleaned_lines = []
                start_collecting = False

                for line in raw_lines:
                    line = line.strip()
                    if not start_collecting:
                        if _is_abstract_boilerplate(line):
                            continue
                        # Require ≥40 chars — prevents stray title fragments from
                        # triggering collection prematurely
                        if len(line) < 40:
                            continue
                        start_collecting = True
                    if start_collecting:
                        if re.match(r'^\d+$', line) or re.match(r'^[ivxIVX]+$', line):
                            continue
                        # Stop at an ALL-CAPS section heading
                        if re.match(r'^[A-Z][A-Z\s]{4,}$', line) and len(line) < 60:
                            break
                        cleaned_lines.append(line)

                abstract_text = " ".join(cleaned_lines)

                # Hard stop at known section boundaries
                for stop in [
                    "TABLE OF CONTENTS", "ACKNOWLEDGMENT", "LIST OF TABLES",
                    "LIST OF FIGURES", "INTRODUCTION", "CHAPTER I", "CHAPTER 1",
                ]:
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
                    print(f"[OCR] Keyword match rejected (no separator, >80 chars): "
                          f"{repr(raw_kw[:60])}")

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
                # Only apply the cut if there is enough content before it.
                # MIN_INTRO_BEFORE_CUT: the opening paragraph must be at least
                # this many characters — if the sub-section heading appears
                # earlier than this, the document's introduction IS the sub-sections
                # (no separate opening paragraph) and we should not cut.
                MIN_INTRO_BEFORE_CUT = 400
                if cut_pos < len(intro_raw) and cut_pos >= MIN_INTRO_BEFORE_CUT:
                    print(f"[OCR] Introduction inline-trimmed at pos {cut_pos} "
                          f"('{intro_raw[cut_pos:cut_pos+40].strip()}')")
                    sections_raw["introduction"] = intro_raw[:cut_pos].rstrip(" .,;")
                elif cut_pos < MIN_INTRO_BEFORE_CUT:
                    print(f"[OCR] Introduction inline-trim SKIPPED — "
                          f"cut_pos={cut_pos} < {MIN_INTRO_BEFORE_CUT} "
                          f"(sub-section heading is the opening, keeping full intro)")
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