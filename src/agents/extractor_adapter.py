# type: ignore
# src/agents/extractor_adapter.py
# Clean, minimal adapter for direct PDF metric extraction.
import logging
import re
from pathlib import Path
from typing import Sequence, Any, Dict, List, Optional

# pdf libraries
import pdfplumber

# PyMuPDF (fitz) is optional fallback; import inside function to avoid hard dependency at import time
# local utilities
from utils.proof_utils import build_proof_object, persist_proof

# Fallback keywords for metrics - extend as needed
FALLBACK_KEYWORDS = {
    "net_profit": [
        r"net profit",
        r"profit for the period",
        r"profit attributable",
        r"profit for the year",
        r"profit for the period attributable",
    ],
    "profit_for_the_period": [
        r"profit for the period",
        r"profit for the period attributable",
        r"profit attributable",
    ],
    "net_interest_income": [
        r"net interest income",
        r"net interest",
        r"interest income",
    ],
    "total_assets": [r"total assets", r"assets"],
    "total_loans": [r"total loans", r"loans"],
    "customer_deposits": [r"customer deposits", r"deposits", r"total deposits"],
    "shareholder_equity": [
        r"shareholders'? equity",
        r"shareholder equity",
        r"equity attributable",
        r"total equity attributable",
    ],
    "net_fee_and_commission_income": [
        r"net fee and commission income",
        r"fee and commission income",
        r"fees and commission income",
        r"fees and commissions",
        r"fee income",
    ],
    "interest_expense": [r"interest expense"],
    "interest_income": [r"interest income"],
    "operating_income": [r"operating income", r"total operating income"],
}

# Numeric candidate regex: comma groups or >=5 digits (suitable for AED'000)
NUM_CAND_RE = re.compile(r"([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{5,})")


def _process_text_lines(text: str, keywords: List[str], page_index: int) -> List[tuple]:
    """
    Return list of candidate tuples (score, line, page_no) from text.
    """
    if not text:
        return []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    lowertext = " ".join(lines).lower()
    # Quick keyword filter
    if keywords and not any(re.search(kw, lowertext, re.IGNORECASE) for kw in keywords):
        return []
    candidates = []
    for i, line in enumerate(lines):
        m = NUM_CAND_RE.search(line)
        if not m:
            continue
        score = 0
        context = " ".join(lines[max(0, i - 2) : i + 3]).lower()
        # add score boosts
        if any(re.search(kw, line, re.IGNORECASE) for kw in keywords):
            score += 3
        if any(re.search(kw, context, re.IGNORECASE) for kw in keywords):
            score += 1
        numstr = m.group(1)
        score += len(numstr.replace(",", ""))
        candidates.append((score, line, page_index + 1))
    return candidates


def _page_scan_fallback(
    file_path: str,
    metric: str,
    max_pages: Optional[int] = None,
    require_keyword: bool = True,
) -> List[Dict[str, Any]]:
    """
    Scan PDF pages directly for numeric candidates for `metric`.
    Tries pdfplumber first, falls back to PyMuPDF (fitz) if needed.
    Returns list of proof objects (may be empty).
    """
    p = Path(file_path)
    if not p.exists():
        logging.warning(f"_page_scan_fallback: file not found: {file_path}")
        return []

    keywords = FALLBACK_KEYWORDS.get(metric, [metric.replace("_", " ")])
    proofs: List[Dict[str, Any]] = []

    # 1) Try pdfplumber
    try:
        with pdfplumber.open(str(p)) as doc:
            pages = getattr(doc, "pages", [])
            count = len(pages)
            pages_to_scan = (
                range(count) if max_pages is None else range(min(count, max_pages))
            )
            for i in pages_to_scan:
                try:
                    text = doc.pages[i].extract_text() or ""
                except Exception as e:
                    logging.debug(f"pdfplumber extract_text failed page {i+1}: {e}")
                    continue
                cand = _process_text_lines(text, keywords, i)
                cand.sort(key=lambda x: x[0], reverse=True)
                for score, line, page_no in cand[:4]:
                    try:
                        proof = build_proof_object(
                            metric=metric,
                            raw_line=line,
                            file=str(p),
                            page=page_no,
                            chunk_id=f"{p.name}::p{page_no}",
                            extraction_regex=None,
                            unit_hint="AED'000",
                        )
                        proofs.append(proof)
                        persist_proof(proof)
                    except Exception:
                        continue
                if proofs and require_keyword:
                    return proofs
    except Exception as e:
        logging.debug(f"pdfplumber open failed or produced no usable pages: {e}")

    # 2) PyMuPDF fallback (fitz) - import here to avoid mandatory dependency
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(str(p))
        count = getattr(doc, "page_count", None)
        if count is None:
            count = len(doc)
        pages_to_scan = (
            range(count) if max_pages is None else range(min(count, max_pages))
        )
        for i in pages_to_scan:
            try:
                text = doc.load_page(i).get_text("text") or ""
            except Exception as e:
                logging.debug(f"PyMuPDF failed page {i+1}: {e}")
                continue
            cand = _process_text_lines(text, keywords, i)
            cand.sort(key=lambda x: x[0], reverse=True)
            for score, line, page_no in cand[:4]:
                try:
                    proof = build_proof_object(
                        metric=metric,
                        raw_line=line,
                        file=str(p),
                        page=page_no,
                        chunk_id=f"{p.name}::p{page_no}",
                        extraction_regex=None,
                        unit_hint="AED'000",
                    )
                    proofs.append(proof)
                    persist_proof(proof)
                except Exception:
                    continue
            if proofs and require_keyword:
                doc.close()
                return proofs
        doc.close()
    except Exception as e:
        logging.debug(f"PyMuPDF fallback failed or not installed: {e}")

    return proofs


def extract_metric_from_file(
    file_path: str,
    metric: str,
    period_label: Optional[str] = None,
    require_keyword: bool = True,
) -> List[Dict[str, Any]]:
    """
    High level wrapper used by evaluation scripts.
    Returns list of proof objects (possibly empty). It will try:
      - Named extraction (not implemented here) -> fallback scanning
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"{file_path} does not exist")
    # For now we use the fallback page scanner only (this is robust)
    proofs = _page_scan_fallback(
        path, metric, max_pages=None, require_keyword=require_keyword
    )
    return proofs


# Expose a minimal API
__all__ = ["extract_metric_from_file", "_page_scan_fallback", "FALLBACK_KEYWORDS"]
