# src/utils/financial_regex.py
from __future__ import annotations

import re
from typing import Optional

# Common patterns for numbers in financial statements
_RE_NUMBER = re.compile(
    r"""
    [-+]?                # optional sign
    (?:
      \d{1,3}(?:,\d{3})+(?:\.\d+)?   # 1,234 or 1,234.56
      |\d+(?:\.\d+)?                 # 1234 or 1234.56
      |\.\d+                         # .123
    )
    (?:\s*[MB]illion)?   # optional million/billion words (rare)
    """,
    re.VERBOSE | re.IGNORECASE,
)

_RE_PERCENT = re.compile(r"([-+]?\d+(?:\.\d+)?)\s*%")

# Helpers


def clean_number_token(token: str) -> Optional[str]:
    """
    Remove currency symbols and whitespace, normalize commas, parentheses for negative numbers.
    Returns cleaned numeric string or None if not recognized.
    """
    if token is None:
        return None
    t = token.strip()
    # handle parentheses as negative
    if t.startswith("(") and t.endswith(")"):
        t = "-" + t[1:-1]
    # remove currency symbols
    t = re.sub(r"[^\d\.\-MBmb,]", "", t)
    # normalize common words (million/billion)
    t = t.replace(" ", "")
    # if contains letters like M/B, keep them for caller to scale
    return t if t else None


def parse_number(token: str) -> Optional[float]:
    """
    Parse a numeric token to float. Handles commas, parentheses, M/B shorthand.
    Examples:
      "1,234" -> 1234.0
      "(1,234)" -> -1234.0
      "12.5M" -> 12500000.0
    """
    if not token:
        return None
    t = clean_number_token(token)
    if not t:
        return None
    # scale for million/billion if present
    scale = 1.0
    if t.lower().endswith("m"):
        scale = 1_000_000.0
        t = t[:-1]
    elif t.lower().endswith("b"):
        scale = 1_000_000_000.0
        t = t[:-1]
    # remove commas
    t = t.replace(",", "")
    try:
        return float(t) * scale
    except ValueError:
        return None


def find_first_number(text: str) -> Optional[float]:
    """
    Find the first numeric-like token in text and return parsed float.
    """
    if not text:
        return None
    m = _RE_NUMBER.search(text)
    if not m:
        # try percent
        pm = _RE_PERCENT.search(text)
        if pm:
            try:
                return float(pm.group(1))
            except Exception:
                return None
        return None
    token = m.group(0)
    return parse_number(token)
