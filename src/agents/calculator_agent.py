# src/agents/calculator_agent.py
from __future__ import annotations
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import math

class ProofObject(BaseModel):
    formula: str
    inputs: Dict[str, Any]
    output: Any
    note: Optional[str] = None

def yoy_change(old: float, new: float) -> ProofObject:
    """
    Year-over-year percentage change: (new - old) / old * 100
    """
    if old == 0:
        return ProofObject(formula="(new - old) / old * 100", inputs={"old": old, "new": new}, output=None,
                           note="division_by_zero")
    pct = ((new - old) / old) * 100.0
    return ProofObject(formula="(new - old) / old * 100", inputs={"old": old, "new": new}, output=round(pct, 6))

def qoq_change(prev: float, curr: float) -> ProofObject:
    """
    Quarter-over-quarter percentage change
    """
    if prev == 0:
        return ProofObject(formula="(curr - prev) / prev * 100", inputs={"prev": prev, "curr": curr}, output=None,
                           note="division_by_zero")
    pct = ((curr - prev) / prev) * 100.0
    return ProofObject(formula="(curr - prev) / prev * 100", inputs={"prev": prev, "curr": curr}, output=round(pct, 6))

def roe(net_income: float, avg_equity: float) -> ProofObject:
    """
    Return on Equity: Net Income / Average Shareholder's Equity * 100
    """
    if avg_equity == 0:
        return ProofObject(formula="net_income / avg_equity * 100", inputs={"net_income": net_income, "avg_equity": avg_equity},
                           output=None, note="division_by_zero")
    val = (net_income / avg_equity) * 100.0
    return ProofObject(formula="net_income / avg_equity * 100", inputs={"net_income": net_income, "avg_equity": avg_equity},
                       output=round(val, 6))

def loan_to_deposit(loans: float, deposits: float) -> ProofObject:
    if deposits == 0:
        return ProofObject(formula="loans / deposits", inputs={"loans": loans, "deposits": deposits}, output=None,
                           note="division_by_zero")
    val = loans / deposits
    return ProofObject(formula="loans / deposits", inputs={"loans": loans, "deposits": deposits}, output=round(val, 6))

def safe_sum(values: List[float]) -> float:
    return float(sum(v for v in values if v is not None))

# Higher-level compute: ROE series from extracted metrics
def compute_roe_series(extracted_metrics: List[Dict[str, Any]]) -> Dict[str, ProofObject]:
    """
    Example: expects dict keyed by 'YYYY-QX' with metrics inside
    e.g., {'2024-Q1': {'net_income': 1000, 'shareholders_equity': 12000}, ...}
    This function returns per-period ROE proof objects.
    """
    results = {}
    for period, metrics in extracted_metrics.items():
        ni = metrics.get("net_income") or metrics.get("net_profit") or metrics.get("netprofit")
        eq = metrics.get("shareholders_equity") or metrics.get("equity")
        if ni is None or eq is None:
            continue
        results[period] = roe(float(ni), float(eq))
    return results
