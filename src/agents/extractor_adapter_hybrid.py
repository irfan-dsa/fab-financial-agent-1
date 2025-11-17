# src/agents/extractor_adapter_hybrid.py
"""
Hybrid Financial Metric Extractor - PRODUCTION VERSION
Uses working direct PDF extraction as primary method
"""
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import fallback components
from agents.extractor_adapter import _page_scan_fallback
from utils.proof_utils import build_proof_object, persist_proof

# Metric name mapping
METRIC_MAPPING = {
    "net_fee_and_commission_income": "Net fee and commission income",
    "net_interest_income": "Net interest income",
    "interest_income": "Interest income",
    "interest_expense": "Interest expense",
    "operating_income": "Operating income",
    "net_profit": "Profit for the period",
    "profit_for_the_period": "Profit for the period",
    "profit_before_taxation": "Profit before taxation",
    "income_tax_expense": "Income tax expense",
}


def _get_direct_extractor():
    """Import direct extractor fresh each time to avoid caching issues"""
    if "direct_pdf_extractor" in sys.modules:
        del sys.modules["direct_pdf_extractor"]

    import direct_pdf_extractor

    return direct_pdf_extractor


def _parse_quarter_from_filename(filename: str) -> Tuple[Optional[str], Optional[int]]:
    import re

    match = re.search(r"Q(\d)-(\d{4})", filename)
    if match:
        return f"Q{match.group(1)}", int(match.group(2))
    return None, None


def extract_metric_from_file(
    file_path: str,
    metric: str,
    period_label: Optional[str] = None,
    require_keyword: bool = True,
) -> List[Dict[str, Any]]:
    """
    Hybrid extraction: Direct PDF first, fallback to scanning
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"{file_path} does not exist")

    proofs = []
    mapped_metric = METRIC_MAPPING.get(metric)

    if mapped_metric:
        try:
            extractor = _get_direct_extractor()

            if mapped_metric in extractor.FAB_LINE_ITEMS:
                quarter, year = _parse_quarter_from_filename(path.name)

                if quarter and year:
                    logging.info(
                        f"Direct extraction for {metric} from {quarter} {year}"
                    )

                    for period_type in range(4):
                        value, metadata = extractor.extract_metric_from_pdf(
                            str(path), mapped_metric, period_type
                        )

                        if value and "error" not in metadata:
                            period_name = metadata.get(
                                "period", f"Period {period_type}"
                            )
                            proof = build_proof_object(
                                metric=metric,
                                raw_line=f"{mapped_metric} ({period_name}): {value}",
                                file=str(path),
                                page=metadata.get("page", 0),
                                chunk_id=f"{path.name}::direct::p{period_type}",
                                extraction_regex=None,
                                unit_hint="AED'000",
                            )
                            proofs.append(proof)
                            persist_proof(proof)

                    if proofs:
                        logging.info(f"Direct extraction SUCCESS: {len(proofs)} values")
                        return proofs

        except Exception as e:
            logging.warning(f"Direct extraction failed: {e}")

    logging.info(f"Fallback scanner for {metric}")
    return _page_scan_fallback(
        str(path), metric, max_pages=None, require_keyword=require_keyword
    )


__all__ = ["extract_metric_from_file"]
