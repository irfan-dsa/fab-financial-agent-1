import json
from pathlib import Path

from agents.extractor_adapter import extract_metric_from_file

# All PDFs in data/raw
PDF_DIR = Path("data/raw")
OUT_FILE = Path("src/eval/ground_truth.jsonl")
OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# Metrics to extract
METRICS = [
    "profit_for_the_period",
    "net_interest_income",
    "interest_income",
    "operating_income",
    "profit_before_taxation",
    "total_assets",
    "total_loans",
    "customer_deposits",
    "shareholder_equity",
]


# Detect quarter from filename
def detect_period(filename: str):
    # Example: FAB-FS-Q3-2023-English.pdf
    import re

    m = re.search(r"Q([1-4])[-_ ]?(\d{4})", filename)
    if not m:
        return None
    return f"Q{m.group(1)} {m.group(2)}"


with OUT_FILE.open("w", encoding="utf8") as out:
    for pdf in sorted(PDF_DIR.glob("*.pdf")):
        period = detect_period(pdf.name)
        if not period:
            print(f"Skipping {pdf.name} (no quarter/year detected)")
            continue

        print(f"\nProcessing: {pdf.name} | Period: {period}")

        for metric in METRICS:
            proofs = extract_metric_from_file(str(pdf), metric, period_label=period)
            for p in proofs:
                rec = {"file": pdf.name, "period": period, "metric": metric, "proof": p}
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")

print("\nGround truth saved to:", OUT_FILE)
