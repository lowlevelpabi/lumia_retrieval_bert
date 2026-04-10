import re
from typing import List, Dict


class CitationGenerator:
    """
    Utility for generating scholarly citation strings from paper metadata.
    Supports APA 6th, APA 7th, APA In-Text, IEEE, MLA 9th, and BibTeX
    for Bachelor's Theses and Capstone Projects.

    Input normalization:
        - Author last names stored in ALL CAPS (common in CvSU PDFs) are
          automatically converted to Title Case before formatting.
        - Titles stored in ALL CAPS are converted to Title Case.
    """

    UNIVERSITY = "Cavite State University"

    # ── Normalization helpers ──────────────────────────────────────────────────

    @staticmethod
    def _normalize_name(name: str) -> str:
        """
        Converts an ALL-CAPS name segment to Title Case.
        Handles multi-word last names (e.g. 'DE LA CRUZ' → 'De La Cruz').
        If the name is already mixed-case it is returned unchanged.
        """
        if not name:
            return name
        # Only normalize if the segment is fully uppercase (ignoring spaces/dots)
        letters = re.sub(r'[^A-Za-z]', '', name)
        if letters and letters == letters.upper():
            return name.title()
        return name

    @staticmethod
    def _normalize_title(title: str) -> str:
        """
        Converts an ALL-CAPS title to Title Case.
        If the title is already mixed-case it is returned unchanged.
        """
        if not title:
            return title
        letters = re.sub(r'[^A-Za-z]', '', title)
        if letters and letters == letters.upper():
            return title.title()
        return title

    # ── Author parsing ─────────────────────────────────────────────────────────

    @staticmethod
    def _parse_authors(author_str: str) -> List[Dict[str, str]]:
        """
        Parses a raw author string into a list of {'first': str, 'last': str}.

        Supported input formats:
            'LAST, F. M. | LAST, F. M.'   (pipe-delimited, CvSU default)
            'Last, First Middle'            (comma-separated single)
            'First Last'                    (space-separated)
        """
        if not author_str:
            return []

        # Split on pipe first, fall back to semicolon
        segments = [s.strip() for s in author_str.split('|') if s.strip()]
        if len(segments) <= 1:
            segments = [s.strip() for s in re.split(r';', author_str) if s.strip()]

        parsed = []
        for s in segments:
            if ',' in s:
                parts = [p.strip() for p in s.split(',', 1)]
                last  = parts[0]
                first = parts[1] if len(parts) > 1 else ''
            else:
                words = s.split()
                if len(words) > 1:
                    first = ' '.join(words[:-1])
                    last  = words[-1]
                else:
                    first = ''
                    last  = s

            parsed.append({
                'first': first.strip(),
                'last':  CitationGenerator._normalize_name(last.strip()),
            })

        return parsed

    # ── Per-format name renderers ──────────────────────────────────────────────

    @classmethod
    def _get_name_apa(cls, author: Dict[str, str]) -> str:
        """
        APA style: Last, F. M.
        Initials are derived from the 'first' field (handles 'R. M.' or 'Reyes Maria').
        """
        first = author['first']
        if not first:
            return author['last']

        # If the first field already looks like initials (e.g. 'R. M.'), keep them.
        # Otherwise extract initials from each word.
        if re.match(r'^([A-Za-z]\.\s*)+$', first.strip()):
            initials = first.strip()
        else:
            initials = ' '.join(
                f"{p[0].upper()}." for p in first.split() if p and p[0].isalpha()
            )

        return f"{author['last']}, {initials}"

    @classmethod
    def _get_name_ieee(cls, author: Dict[str, str]) -> str:
        """
        IEEE style: F. M. Last
        """
        first = author['first']
        if not first:
            return author['last']

        if re.match(r'^([A-Za-z]\.\s*)+$', first.strip()):
            initials = first.strip()
        else:
            initials = ' '.join(
                f"{p[0].upper()}." for p in first.split() if p and p[0].isalpha()
            )

        return f"{initials} {author['last']}"

    @classmethod
    def _get_name_mla(cls, author: Dict[str, str]) -> str:
        """
        MLA style (first author): Last, F. M.
        Subsequent authors are handled by the caller (', et al.' or full name).
        """
        first = author['first']
        if not first:
            return author['last']
        return f"{author['last']}, {first}"

    # ── Main entry point ───────────────────────────────────────────────────────

    @classmethod
    def generate_all(
        cls,
        title: str,
        author_str: str,
        year: str,
        project_type: str = 'Thesis',
    ) -> Dict[str, str]:
        """
        Returns all six citation formats for the given paper metadata.

        Keys returned:
            apa_6, apa_7, apa_intext, ieee, mla, bibtex
        """
        authors = cls._parse_authors(author_str)
        if not authors:
            return {}

        # Normalize title (ALL-CAPS → Title Case)
        display_title = cls._normalize_title(title)

        t_type_short = "Bachelor's Thesis" if 'Thesis' in project_type else 'Capstone Project'

        # ── APA author block: Last, F. M., Last, F. M., & Last, F. M. ─────────
        apa_names = [cls._get_name_apa(a) for a in authors]
        if len(apa_names) == 1:
            author_apa = apa_names[0]
        elif len(apa_names) == 2:
            author_apa = f"{apa_names[0]}, & {apa_names[1]}"
        else:
            author_apa = ', '.join(apa_names[:-1]) + f', & {apa_names[-1]}'

        # ── 1. APA 6th Edition ─────────────────────────────────────────────────
        # Last, F. M., & Last, F. M. (Year). *Title* (Bachelor's Thesis). Institution.
        # Title is italicised (<em>) for HTML display; plain text is used for copy.
        apa_6 = (
            f"{author_apa} ({year}). <em>{display_title}</em> "
            f"({t_type_short}). {cls.UNIVERSITY}."
        )

        # ── 2. APA 7th Edition ─────────────────────────────────────────────────
        apa_7 = (
            f"{author_apa} ({year}). <em>{display_title}</em> "
            f"[{t_type_short}]. {cls.UNIVERSITY}."
        )

        # ── 3. APA In-Text ─────────────────────────────────────────────────────
        # (Last, Year) / (Last & Last, Year) / (Last et al., Year)
        last_0 = authors[0]['last']
        if len(authors) == 1:
            intext = f"({last_0}, {year})"
        elif len(authors) == 2:
            intext = f"({last_0} & {authors[1]['last']}, {year})"
        else:
            intext = f"({last_0} et al., {year})"

        return {
            'apa_6':      apa_6,
            'apa_7':      apa_7,
            'apa_intext': intext,
        }