# src/agents/temporal_agent.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional
from utils.quarter_utils import normalize_quarter_label, parse_quarter_from_text

def group_chunks_by_period(chunks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group parser chunks into period buckets based on metadata (file names, section, or explicit quarter text).
    Heuristic:
    - If chunk.file contains year/quarter, use that
    - Else if chunk.section contains quarter, parse it
    - Else group under 'unknown-<filename>'
    """
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for c in chunks:
        label = None
        # try file name e.g., FAB_2024_Q3_Financial_Statements.pdf
        fname = c.get("file", "")
        m = parse_quarter_from_text(fname)
        if m:
            q, y = m
            label = normalize_quarter_label(q, y)
        else:
            # try section or text
            sec = c.get("section", "")
            m2 = parse_quarter_from_text(sec)
            if m2:
                q, y = m2
                label = normalize_quarter_label(q, y)
            else:
                label = f"unknown-{fname}"
        groups.setdefault(label, []).append(c)
    return groups

def aggregate_metrics_by_period(extracted_metrics: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    From a flat list of ExtractedMetric objects (or dicts), create a period -> metric -> value map.
    Expects each metric to have metadata.chunk_id that contains period info or file name which includes year/quarter.
    This is a heuristic aggregator: for identical metrics in same period it picks the largest (assumes totals are larger).
    """
    aggregated: Dict[str, Dict[str, float]] = {}
    for em in extracted_metrics:
        # em may be pydantic or dict
        if hasattr(em, "dict"):
            d = em.dict()
        else:
            d = em
        file = d.get("file", "")
        # attempt to parse quarter from file
        q = parse_quarter_from_text(file)
        period = None
        if q:
            q_label, y = q
            period = normalize_quarter_label(q_label, y)
        else:
            # fall back to metadata chunk id or unknown
            metadata = d.get("metadata", {})
            chunk_id = metadata.get("chunk_id", "")
            period = f"unknown-{file}"
        metric = d.get("metric")
        value = d.get("value")
        if period not in aggregated:
            aggregated[period] = {}
        # choose best value if multiple: pick max absolute (totals vs subtotals)
        existing = aggregated[period].get(metric)
        if existing is None:
            aggregated[period][metric] = value
        else:
            # choose value with larger absolute magnitude (heuristic)
            aggregated[period][metric] = value if abs(value) >= abs(existing) else existing
    return aggregated
