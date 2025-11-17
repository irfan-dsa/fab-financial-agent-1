# src/utils/quarter_utils.py
from __future__ import annotations

import re
from typing import Optional, Tuple

_QUARTER_RE = re.compile(r"(Q[1-4])\s*[^\d\s]*\s*(\d{4})", re.IGNORECASE)
_YEAR_ONLY_RE = re.compile(r"\b(20\d{2})\b")


def parse_quarter_from_text(text: str) -> Optional[Tuple[str, int]]:
    """
    Attempt to extract (quarter, year) from a string.
    Examples:
      "Q3 2024" -> ("Q3", 2024)
      "Quarter 4 2023" -> ("Q4", 2023)
    """
    if not text:
        return None
    m = _QUARTER_RE.search(text)
    if m:
        q = m.group(1).upper()
        y = int(m.group(2))
        return (q, y)
    # fallback: look for year only
    ym = _YEAR_ONLY_RE.search(text)
    if ym:
        return (None, int(ym.group(1)))
    return None


def normalize_quarter_label(q: Optional[str], y: int) -> str:
    """Return normalized label like '2024-Q3' given quarter string and year."""
    qlabel = q if q else "Q?"
    return f"{y}-{qlabel.upper()}"
