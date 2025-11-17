# src/utils/proof_utils.py
from __future__ import annotations
import re
from typing import Dict, Any, Optional
from decimal import Decimal
from pathlib import Path
import json
import hashlib
import time

# Match numeric groups like "3", "3,261,682", "2023"
NUM_RE = re.compile(r"([0-9][0-9,]*)")

def parse_int_from_text(s: str) -> Optional[int]:
    """
    Robustly parse an integer quantity from a text line.

    Strategy:
      - Find all digit groups (e.g., '3', '3,261,682', '2023')
      - If any group contains a comma, prefer the first such group (common thousands format)
      - Otherwise prefer the longest digit group (most digits)
      - Return None if nothing found
    """
    if not s:
        return None

    s_norm = s.replace("’", "'")
    groups = NUM_RE.findall(s_norm)
    if not groups:
        return None

    # prefer groups with comma (thousands separator)
    for g in groups:
        if "," in g:
            try:
                return int(g.replace(",", ""))
            except Exception:
                continue

    # otherwise pick the longest numeric group (most digits)
    # remove any non-digit chars just in case, though NUM_RE should only capture digits/commas
    def digit_len(x: str) -> int:
        return len(re.sub(r"\D", "", x))

    best = max(groups, key=digit_len)
    try:
        return int(best.replace(",", ""))
    except Exception:
        return None

def thousands_to_millions(n_thousands: int) -> float:
    return float(Decimal(n_thousands) / Decimal(1000))

def compute_sha256(filepath: str) -> str:
    p = Path(filepath)
    if not p.exists():
        return ""
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def build_proof_object(
    metric: str,
    raw_line: str,
    file: str,
    page: Optional[int],
    chunk_id: Optional[str],
    extraction_regex: Optional[str] = None,
    unit_hint: str = "AED'000",
) -> Dict[str, Any]:
    """
    Returns a standardized proof object for one extracted numeric metric.
    """
    n_thousands = parse_int_from_text(raw_line)
    if n_thousands is None:
        raise ValueError("no numeric value parsed")

    value_millions = thousands_to_millions(n_thousands)
    sha256 = compute_sha256(file) if file else ""
    now_ts = time.time()

    proof = {
        "metric": metric,
        "raw_line": raw_line.strip(),
        "value_thousands": int(n_thousands),
        "value_millions": float(round(value_millions, 6)),
        "unit": "AED millions",
        "unit_hint": unit_hint,
        "source_file": file,
        "page": page,
        "chunk_id": chunk_id,
        "extraction_regex": extraction_regex,
        "file_sha256": sha256,
        "extracted_at": now_ts
    }
    return proof

def persist_proof(proof: Dict[str, Any], out_path: str = "data/out/metrics.jsonl") -> None:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(proof, ensure_ascii=False) + "\n")
