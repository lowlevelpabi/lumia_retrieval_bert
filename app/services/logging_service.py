import sys
import textwrap
import re
import os
from datetime import datetime
from typing import Any, Optional

LOG_FILE = "system_logs.txt"
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# ── ANSI colour codes (disabled automatically on non-TTY) ─────────────────────
_TTY = sys.stdout.isatty()

def _c(code: str) -> str:
    return f"\033[{code}m" if _TTY else ""

RESET  = _c("0")
BOLD   = _c("1")
DIM    = _c("2")

# Regex channel  — blue family
RX_HEADER = _c("38;5;75")   # bright blue
RX_LABEL  = _c("38;5;39")   # medium blue
RX_DETAIL = _c("38;5;117")  # light blue

# ML channel — green family
ML_HEADER = _c("38;5;82")   # bright green
ML_LABEL  = _c("38;5;46")   # medium green
ML_DETAIL = _c("38;5;120")  # light green

# Shared
INFO_C    = _c("38;5;250")  # light gray
WARN_C    = _c("38;5;220")  # amber
ERR_C     = _c("38;5;196")  # red
OK_C      = _c("38;5;48")   # teal-green
SEC_C     = _c("38;5;135")  # purple
DIM_C     = _c("2")

# ── Badge templates ───────────────────────────────────────────────────────────
_BADGES = {
    "REGEX":   f"{RX_HEADER}{BOLD} REGEX {RESET}",
    "ML":      f"{ML_HEADER}{BOLD}  ML   {RESET}",
    "INFO":    f"{INFO_C}{BOLD} INFO  {RESET}",
    "WARN":    f"{WARN_C}{BOLD} WARN  {RESET}",
    "ERROR":   f"{ERR_C}{BOLD} ERROR {RESET}",
    "OK":      f"{OK_C}{BOLD}  OK   {RESET}",
}


def _fmt_kv(pairs: dict, color: str) -> str:
    """Format key=value pairs with muted keys and colored values."""
    parts = []
    for k, v in pairs.items():
        parts.append(f"{DIM_C}{k}={RESET}{color}{v}{RESET}")
    return "  " + "  ".join(parts) if parts else ""


def _now() -> str:
    return f"{DIM_C}{datetime.now().strftime('%H:%M:%S')}{RESET}"


def _write_to_file(text: str) -> None:
    """Appends cleaned log text to the system_logs.txt file."""
    try:
        # Strip ANSI colors before writing to file for readability
        clean_text = ANSI_ESCAPE.sub('', text)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            # Add date to the file log for better long-term tracking
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {clean_text}\n")
    except Exception:
        pass # Never let logging failures break the main application logic


def _print(badge: str, msg: str, detail: str = "", indent: int = 0) -> None:
    pad = "  " * indent
    line = f"{_now()} {badge} {pad}{msg}"
    if detail:
        line += f"  {DIM_C}{detail}{RESET}"
    print(line)
    _write_to_file(f"{badge} {pad}{msg} {detail}".strip())


# ── Public logger ─────────────────────────────────────────────────────────────

class _Logger:
    """Singleton structured logger. Import the `log` instance, not this class."""

    # ── Section dividers ──────────────────────────────────────────────────────

    def section(self, title: str, char: str = "─") -> None:
        """Print a bold section header that visually separates pipeline stages."""
        width = 60
        bar   = char * width
        print(f"\n{SEC_C}{BOLD}{bar}{RESET}")
        print(f"{SEC_C}{BOLD}  {title}{RESET}")
        print(f"{SEC_C}{bar}{RESET}")
        
        _write_to_file(f"\n{'=' * width}\n  {title}\n{'=' * width}")

    def subsection(self, title: str) -> None:
        """Lighter divider for sub-stages within a section."""
        print(f"\n{DIM_C}  ┄┄ {title} ┄┄{RESET}")
        _write_to_file(f"--- {title} ---")

    # ── REGEX channel ─────────────────────────────────────────────────────────

    def regex(self, msg: str, **kv: Any) -> None:
        """Log a regex / rule-based event."""
        detail = _fmt_kv(kv, RX_DETAIL)
        _print(_BADGES["REGEX"], f"{RX_LABEL}{msg}{RESET}", detail)

    def regex_hit(self, page: int, line: str, target: float,
                  fp: float, final: float) -> None:
        """
        Compact one-liner for a scored heading candidate (inner scoring loop).
        Printed for every line that clears the fuzzy threshold.
        """
        # Colour-code the final score
        if final >= 0.88:
            score_c = OK_C
        elif final >= 0.80:
            score_c = RX_LABEL
        else:
            score_c = WARN_C

        clipped = line[:40].ljust(40)
        kv = (
            f"{DIM_C}pg={RESET}{RX_DETAIL}{page:<3}{RESET}  "
            f"{DIM_C}line={RESET}{RX_DETAIL}\"{clipped}\"{RESET}  "
            f"{DIM_C}target={RESET}{RX_DETAIL}{target:.2f}{RESET}  "
            f"{DIM_C}fp={RESET}{WARN_C}{fp:.2f}{RESET}  "
            f"{DIM_C}final={RESET}{score_c}{BOLD}{final:.2f}{RESET}"
        )
        print(f"  {DIM_C}│{RESET}  {_BADGES['REGEX']} {kv}")
        
        _file_kv = f"pg={page} line=\"{clipped}\" target={target:.2f} fp={fp:.2f} final={final:.2f}"
        _write_to_file(f"  │  REGEX {_file_kv}")

    def regex_skip(self, page: int, reason: str) -> None:
        """Log a skipped page (TOC / appendix / rubric)."""
        print(
            f"  {DIM_C}│{RESET}  {_BADGES['REGEX']} "
            f"{DIM_C}pg={RESET}{RX_DETAIL}{page:<3}{RESET}  "
            f"{WARN_C}skip — {reason}{RESET}"
        )
        _write_to_file(f"  │  REGEX pg={page} skip — {reason}")

    def regex_accept(self, section: str, page: int, score: float,
                     reason: str = "early accept") -> None:
        """Log a section page that was accepted (early or first-candidate)."""
        _print(
            _BADGES["REGEX"],
            f"{RX_LABEL}✔  '{section}' → page {page}{RESET}",
            _fmt_kv({"score": f"{score:.2f}", "via": reason}, RX_DETAIL),
        )

    def regex_not_found(self, section: str) -> None:
        _print(_BADGES["REGEX"], f"{WARN_C}✘  '{section}' not found{RESET}")

    # ── ML channel ────────────────────────────────────────────────────────────

    def ml(self, msg: str, **kv: Any) -> None:
        """Generic ML event log."""
        detail = _fmt_kv(kv, ML_DETAIL)
        _print(_BADGES["ML"], f"{ML_LABEL}{msg}{RESET}", detail)

    def ml_load(self, model: str, tier: str) -> None:
        """Log a successful model load."""
        _print(
            _BADGES["ML"],
            f"{ML_LABEL}Model loaded{RESET}",
            _fmt_kv({"tier": tier, "model": model}, ML_DETAIL),
        )

    def ml_load_fail(self, model: str, exc: Exception) -> None:
        _print(
            _BADGES["ML"],
            f"{WARN_C}Model unavailable — {model}{RESET}",
            _fmt_kv({"reason": str(exc)[:80]}, WARN_C),
        )

    def ml_classify(self, task: str, label: str, score: float,
                    tier: Optional[str] = None) -> None:
        """Log a classification result (department, degree, heading, etc.)."""
        kv: dict = {"label": label, "score": f"{score:.2f}"}
        if tier:
            kv["tier"] = tier
        _print(
            _BADGES["ML"],
            f"{ML_LABEL}{task}{RESET}",
            _fmt_kv(kv, ML_DETAIL),
        )

    def ml_keywords(self, keywords: list) -> None:
        joined = ", ".join(keywords)
        _print(
            _BADGES["ML"],
            f"{ML_LABEL}Keywords extracted{RESET}",
            _fmt_kv({"kw": joined[:80]}, ML_DETAIL),
        )

    def ml_summary(self, section: str, chars: int) -> None:
        _print(
            _BADGES["ML"],
            f"{ML_LABEL}Summary ready — '{section}'{RESET}",
            _fmt_kv({"chars": chars}, ML_DETAIL),
        )

    def ml_warn(self, msg: str, **kv: Any) -> None:
        detail = _fmt_kv(kv, WARN_C)
        _print(_BADGES["WARN"], f"{WARN_C}{msg}{RESET}", detail)

    # ── Shared channels ───────────────────────────────────────────────────────

    def info(self, msg: str, **kv: Any) -> None:
        detail = _fmt_kv(kv, INFO_C)
        _print(_BADGES["INFO"], f"{INFO_C}{msg}{RESET}", detail)

    def warn(self, msg: str, **kv: Any) -> None:
        detail = _fmt_kv(kv, WARN_C)
        _print(_BADGES["WARN"], f"{WARN_C}{msg}{RESET}", detail)

    def error(self, msg: str, exc: Optional[Exception] = None, **kv: Any) -> None:
        if exc:
            kv["exc"] = f"{type(exc).__name__}: {str(exc)[:100]}"
        detail = _fmt_kv(kv, ERR_C)
        _print(_BADGES["ERROR"], f"{ERR_C}{msg}{RESET}", detail)

    def success(self, msg: str, **kv: Any) -> None:
        detail = _fmt_kv(kv, OK_C)
        _print(_BADGES["OK"], f"{OK_C}{BOLD}{msg}{RESET}", detail)


log = _Logger()