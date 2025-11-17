"""
Direct PDF Financial Extractor - Bypasses vector store chunking issues
Reads directly from PDF files to extract complete financial line items
"""
import sys

sys.path.insert(0, "src")
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pdfplumber

# FAB Income Statement Line Items
FAB_LINE_ITEMS = {
    "Interest income": ["interest income"],
    "Interest expense": ["interest expense"],
    "Net interest income": ["net interest income"],
    "Income from Islamic financing": [
        "income from islamic financing",
        "income from islamic financing and investing products",
    ],
    "Distribution on Islamic deposits": [
        "distribution on islamic deposits",
        "distribution on islamic customers",
    ],
    "Net income from Islamic financing": ["net income from islamic financing"],
    "Total net interest income": ["total net interest income and income from islamic"],
    "Fee and commission income": ["fee and commission income"],
    "Fee and commission expense": ["fee and commission expense"],
    "Net fee and commission income": ["net fee and commission income"],
    "Net foreign exchange gain": ["net foreign exchange gain"],
    "Net gain on investments": ["net gain on investments and derivatives"],
    "Other operating income": ["other operating income"],
    "Operating income": ["operating income"],
    "Gain on disposal": ["gain on disposal of stake in subsidiary"],
    "Operating expenses": ["general, administration and other operating expenses"],
    "Net impairment charge": ["net impairment charge"],
    "Profit before taxation": ["profit before taxation"],
    "Income tax expense": ["income tax expense"],
    "Profit for the period": ["profit for the period", "profit for the year"],
}

PERIOD_NAMES = {
    0: "9M Current Year",
    1: "9M Prior Year",
    2: "3M Current Quarter",
    3: "3M Prior Quarter",
}


def is_financial_value(text: str) -> bool:
    """Check if text is a financial value (not a note reference)."""
    text = text.strip()
    if not text or len(text) < 3:
        return False
    # Exclude small numbers (likely note references)
    if re.match(r"^\d{1,3}$", text):
        return False
    # Must be numeric with commas, parens, or length > 5
    if re.match(r"^[\d,().-]+$", text) and ("," in text or len(text) > 5):
        return True
    return False


def extract_values_from_line(line: str, search_terms: List[str]) -> Optional[List[str]]:
    """Extract all financial values from a line containing a label."""
    for term in search_terms:
        if term.lower() in line.lower():
            # Split line and extract all financial values
            parts = line.split()
            values = [p for p in parts if is_financial_value(p)]
            if (
                len(values) >= 4
            ):  # Should have 4 values (9M curr, 9M prior, 3M curr, 3M prior)
                return values
    return None


def find_income_statement_page(pdf_path: str) -> Optional[int]:
    """Find the page containing the Income Statement."""
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages[:15]):  # Check first 15 pages
            text = page.extract_text()
            if text and "statement of profit or loss" in text.lower():
                return page_num
    return None


def extract_metric_from_pdf(
    pdf_path: str, metric_name: str, period_type: int = 0
) -> Tuple[Optional[str], Dict]:
    """
    Extract a financial metric directly from PDF.

    Args:
        pdf_path: Path to PDF file
        metric_name: Name of metric from FAB_LINE_ITEMS
        period_type: Which period (0-3)

    Returns:
        Tuple of (value, metadata)
    """
    if metric_name not in FAB_LINE_ITEMS:
        return None, {"error": f"Unknown metric: {metric_name}"}

    search_terms = FAB_LINE_ITEMS[metric_name]

    # Find Income Statement page
    page_num = find_income_statement_page(pdf_path)
    if page_num is None:
        return None, {"error": "Income Statement page not found"}

    # Extract from that page
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num]
        text = page.extract_text()

        if not text:
            return None, {"error": "Could not extract text from page"}

        # Try to find values on the same line as the label
        lines = text.split("\n")
        for line in lines:
            values = extract_values_from_line(line, search_terms)
            if values and period_type < len(values):
                return values[period_type], {
                    "page": page_num + 1,
                    "source": Path(pdf_path).name,
                    "period": PERIOD_NAMES[period_type],
                    "method": "direct_pdf",
                }

    return None, {"error": "Metric not found in PDF"}


def get_quarter_pdf_path(
    quarter: str, year: int, data_dir: str = "data/raw"
) -> Optional[str]:
    """Find PDF path for a given quarter and year."""
    pattern = f"FAB-FS-{quarter}-{year}-English*.pdf"
    matches = list(Path(data_dir).glob(pattern))
    return str(matches[0]) if matches else None


def extract_metric(metric_name: str, quarter: str, year: int, period_type: int = 0):
    """
    High-level function to extract a metric.

    Args:
        metric_name: Name from FAB_LINE_ITEMS
        quarter: e.g., "Q3"
        year: e.g., 2023
        period_type: 0-3 for different periods

    Returns:
        Tuple of (value, metadata)
    """
    pdf_path = get_quarter_pdf_path(quarter, year)
    if not pdf_path:
        return None, {"error": f"PDF not found for {quarter} {year}"}

    return extract_metric_from_pdf(pdf_path, metric_name, period_type)


# Testing
if __name__ == "__main__":
    print("DIRECT PDF FINANCIAL EXTRACTOR")
    print("=" * 70)
    print("\nTesting key metrics for Q3 2023:\n")

    test_metrics = [
        "Interest income",
        "Net interest income",
        "Net fee and commission income",
        "Operating income",
        "Profit before taxation",
        "Profit for the period",
    ]

    for metric in test_metrics:
        print(f"\n{metric}:")
        print("-" * 70)

        for period_type in range(4):
            value, metadata = extract_metric(metric, "Q3", 2023, period_type)

            if value:
                print(f"  {PERIOD_NAMES[period_type]:25s}: {value:>15s}")
            else:
                error = metadata.get("error", "NOT FOUND")
                print(f"  {PERIOD_NAMES[period_type]:25s}: {error}")

    print("\n" + "=" * 70)
