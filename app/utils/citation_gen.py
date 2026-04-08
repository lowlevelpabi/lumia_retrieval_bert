import re
from typing import List, Dict

class CitationGenerator:
    """
    Utility for generating scholarly citation strings from paper metadata.
    Focuses on APA (6th/7th), IEEE, MLA, and BibTeX for Bachelor's Theses.
    """

    UNIVERSITY = "Cavite State University"

    @staticmethod
    def _parse_authors(author_str: str) -> List[Dict[str, str]]:
        """
        Parses a raw author string into a list of { 'first': str, 'last': str }.
        Handles 'First Last', 'Last, First', and 'Author 1 | Author 2'.
        """
        if not author_str:
            return []

        segments = [s.strip() for s in author_str.split('|') if s.strip()]
        if len(segments) <= 1:
            segments = [s.strip() for s in re.split(r';', author_str) if s.strip()]

        parsed = []
        for s in segments:
            if ',' in s:
                parts = [p.strip() for p in s.split(',', 1)]
                parsed.append({"first": parts[1] if len(parts) > 1 else "", "last": parts[0]})
            else:
                parts = s.split()
                if len(parts) > 1:
                    parsed.append({"first": " ".join(parts[:-1]), "last": parts[-1]})
                else:
                    parsed.append({"first": "", "last": s})
        return parsed

    @classmethod
    def _get_name_apa(cls, author: Dict[str, str]) -> str:
        """Formats 'Last, F. M.' for APA."""
        initials = ""
        if author["first"]:
            initials = " ".join([f"{p[0]}." for p in author["first"].split() if p])
        return f"{author['last']}, {initials}".strip()

    @classmethod
    def _get_name_ieee(cls, author: Dict[str, str]) -> str:
        """Formats 'F. M. Last' for IEEE."""
        initials = ""
        if author["first"]:
            initials = " ".join([f"{p[0]}." for p in author["first"].split() if p])
        return f"{initials} {author['last']}".strip()

    @classmethod
    def _get_name_mla(cls, author: Dict[str, str]) -> str:
        """Formats 'Last, First Name' for MLA."""
        return f"{author['last']}, {author['first']}".strip()

    @classmethod
    def generate_all(cls, title: str, author_str: str, year: str, project_type: str = "Thesis") -> Dict[str, str]:
        """Returns a dictionary of all 6 supported citation formats."""
        authors = cls._parse_authors(author_str)
        if not authors:
            return {}

        t_type_short = "Bachelor's Thesis" if "Thesis" in project_type else "Capstone Project"

        # ── APA author string: Last, F. M., & Last, F. M. ─────────────────────
        apa_parts = []
        for i, a in enumerate(authors):
            name = cls._get_name_apa(a)
            if i == len(authors) - 1 and len(authors) > 1:
                apa_parts.append("& " + name)
            else:
                apa_parts.append(name)
        author_apa = ", ".join(apa_parts)

        # 1. APA 6th — type in parentheses
        #    Last, F. M. (Year). Title (Bachelor's Thesis). Institution.
        apa_6 = f"{author_apa} ({year}). {title} ({t_type_short}). {cls.UNIVERSITY}."

        # 2. APA 7th — type in brackets
        #    Last, F. M. (Year). Title [Bachelor's Thesis]. Institution.
        apa_7 = f"{author_apa} ({year}). {title} [{t_type_short}]. {cls.UNIVERSITY}."

        # 3. APA In-Text
        if len(authors) == 1:
            intext = f"({authors[0]['last']}, {year})"
        elif len(authors) == 2:
            intext = f"({authors[0]['last']} & {authors[1]['last']}, {year})"
        else:
            intext = f"({authors[0]['last']} et al., {year})"

        # 4. IEEE — F. M. Last, "Title," Type, Institution, Year.
        ieee_authors = [cls._get_name_ieee(a) for a in authors]
        author_ieee  = ", ".join(ieee_authors)
        ieee = f"{author_ieee}, \"{title},\" {t_type_short}, {cls.UNIVERSITY}, {year}."

        # 5. MLA — Last, First, et al. "Title." Institution, Type, Year.
        author_mla = cls._get_name_mla(authors[0])
        if len(authors) > 1:
            author_mla += ", et al."
        mla = f"{author_mla}. \"{title}.\" {cls.UNIVERSITY}, {t_type_short}, {year}."

        # 6. BibTeX
        clean_last = re.sub(r'[^a-zA-Z]', '', authors[0]['last'].lower())
        first_word = re.sub(r'[^a-zA-Z]', '', title.split()[0].lower()) if title else "paper"
        cite_key   = f"{clean_last}{year}{first_word}"
        bib_authors = " and ".join([f"{a['last']}, {a['first']}" for a in authors])
        bibtex = (
            f"@thesis{{{cite_key},\n"
            f"  author = {{{bib_authors}}},\n"
            f"  title  = {{{title}}},\n"
            f"  school = {{{cls.UNIVERSITY}}},\n"
            f"  year   = {{{year}}},\n"
            f"  type   = {{{t_type_short}}}\n"
            f"}}"
        )

        return {
            "apa_6":      apa_6,
            "apa_7":      apa_7,
            "apa_intext": intext,
            "ieee":       ieee,
            "mla":        mla,
            "bibtex":     bibtex,
        }