# type: ignore
import json
import os
import re
from pathlib import Path

from agents.extractor_adapter import extract_metric_from_file

RAW_DIR = Path("data/raw")
OUT_DIR = Path("data/ground_truth")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "financial_metrics.json"

METRICS = [
    "profit_for_the_period",
    "interest_income",
    "net_interest_income",
    "net_fee_and_commission_income",
    "operating_income",
    "profit_before_taxation",
    "total_assets",
    "total_loans",
    "customer_deposits",
    "shareholder_equity",
]


def detect_qy_from_filename(name):
    m = re.search(r"Q([1-4])[-_ ]?(\d{4})", name, re.IGNORECASE)
    return f"Q{m.group(1)}_{m.group(2)}" if m else None


ground_truth: Dict[str, Any] = {}

for pdf in RAW_DIR.glob("*.pdf"):
    qy = detect_qy_from_filename(pdf.name)
    if not qy:
        print(f"Skipping (no quarter detected): {pdf.name}")
        continue

    ground_truth.setdefault(qy, {})
    print(f"\nExtracting from {pdf.name} => {qy}")

    for metric in METRICS:
        try:
            proofs = extract_metric_from_file(str(pdf), metric)
            if proofs:
                best = proofs[0]
                ground_truth[qy][metric] = {
                    "value_millions": best["value_millions"],
                    "value_thousands": best["value_thousands"],
                    "page": best["page"],
                    "source_file": best["source_file"],
                    "file_sha256": best["file_sha256"],
                }
                print(f"  ? {metric}: {best['value_millions']}")
            else:
                ground_truth[qy][metric] = None
                print(f"  ? {metric}: NOT FOUND")
        except Exception as ex:
            ground_truth[qy][metric] = None
            print(f"  ERROR {metric}: {ex}")

with OUT_FILE.open("w", encoding="utf-8") as f:
    json.dump(ground_truth, f, indent=2)

print("\nGround truth saved to:", OUT_FILE)
