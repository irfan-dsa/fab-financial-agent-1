# src/agents/extraction_agent.py
from __future__ import annotations
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from utils.financial_regex import find_first_number, parse_number
from utils.quarter_utils import parse_quarter_from_text
import re

class ExtractedMetric(BaseModel):
    metric: str
    value: float
    file: str
    page: int
    section: str
    raw_text: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = {}

# Mapping of common metric names to metric keys (expandable)
METRIC_KEYWORDS = {
    "net profit": "net_profit",
    "profit for the period": "net_profit",
    "total assets": "total_assets",
    "customer deposits": "customer_deposits",
    "total deposits": "customer_deposits",
    "total loans": "total_loans",
    "gross loans": "total_loans",
    "shareholders' equity": "shareholders_equity",
    "equity": "shareholders_equity",
    "operating income": "operating_income",
    "net interest income": "net_interest_income",
    "provisions": "provisions",
    "non-performing loans": "npl",
    "npl ratio": "npl_ratio",
}

def _find_metric_key_from_text(text: str) -> Optional[str]:
    """Return the metric key if text contains known keyword."""
    t = text.lower()
    for k, v in METRIC_KEYWORDS.items():
        if k in t:
            return v
    return None

def extract_metrics_from_chunk(chunk: Dict[str, Any]) -> List[ExtractedMetric]:
    """
    Try to extract metric(s) from a chunk produced by the parser.
    chunk: {id, file, page, section, chunk_type, text, table_header, table_row}
    """
    results = []
    text = chunk.get("text", "") or ""
    # 1) If table row, attempt to map header->value pairs
    if chunk.get("chunk_type") == "table_row" and chunk.get("table_header") and chunk.get("table_row"):
        headers = chunk["table_header"]
        row = chunk["table_row"]
        # loop headers and try to extract numeric from each cell
        for h, cell in zip(headers, row):
            key = _find_metric_key_from_text(h)
            if key:
                val = find_first_number(str(cell))
                if val is not None:
                    results.append(ExtractedMetric(
                        metric=key,
                        value=val,
                        file=chunk.get("file"),
                        page=chunk.get("page"),
                        section=chunk.get("section"),
                        raw_text=f"{h}: {cell}",
                        metadata={"chunk_id": chunk.get("id")}
                    ))
    # 2) If text chunk, try to find metrics via keyword proximity
    else:
        key = _find_metric_key_from_text(text)
        if key:
            value = find_first_number(text)
            if value is not None:
                results.append(ExtractedMetric(
                    metric=key,
                    value=value,
                    file=chunk.get("file"),
                    page=chunk.get("page"),
                    section=chunk.get("section"),
                    raw_text=text,
                    metadata={"chunk_id": chunk.get("id")}
                ))
        else:
            # generic detection: try to find numbers with likely labels in neighbors
            # simple heuristic: look for "Net profit" nearby
            for k, key_name in METRIC_KEYWORDS.items():
                if k in text.lower():
                    v = find_first_number(text)
                    if v is not None:
                        results.append(ExtractedMetric(metric=key_name,
                            value=v, file=chunk.get("file"),
                            page=chunk.get("page"), section=chunk.get("section"),
                            raw_text=text, metadata={"chunk_id": chunk.get("id")}))
    return results

# High-level function to scan many chunks
def extract_metrics_from_chunks(chunks: List[Dict[str, Any]]) -> List[ExtractedMetric]:
    out = []
    for c in chunks:
        try:
            ev = extract_metrics_from_chunk(c)
            if ev:
                out.extend(ev)
        except Exception:
            # don't fail entire pipeline on one bad chunk
            continue
    return out
