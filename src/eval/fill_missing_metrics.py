# src/eval/fill_missing_metrics.py
import json
from pathlib import Path
import glob
import re
from typing import Optional

try:
    from agents.extractor_adapter import extract_metric_from_file
except Exception as e:
    raise ImportError(f"Cannot import extract_metric_from_file: {e}")

GT_PATH = Path("data/ground_truth/financial_metrics.json")
OUT_PATH = Path("data/ground_truth/financial_metrics.updated.json")
REPORT_DIR = Path("src/eval/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = REPORT_DIR / "fill_missing_report.json"

REQUIRED_METRICS = [
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

def guess_file_for_period(period_key: str) -> Optional[str]:
    qy = period_key.replace("_", " ")
    candidates = glob.glob("data/raw/*.pdf")
    for c in candidates:
        name = Path(c).name
        if re.search(rf"{qy.replace(' ', '.*')}", name, re.IGNORECASE):
            return c
    return candidates[0] if candidates else None

def main():
    if not GT_PATH.exists():
        raise FileNotFoundError(f"Ground truth file not found: {GT_PATH}")
    gt = json.loads(GT_PATH.read_text(encoding="utf-8"))
    report = {"filled": [], "still_missing": [], "attempts": 0}

    for period_key, metrics in sorted(gt.items()):
        if not isinstance(metrics, dict):
            metrics = {}
            gt[period_key] = metrics

        candidate_files = [
            v.get("source_file") for v in metrics.values()
            if isinstance(v, dict) and v.get("source_file")
        ]
        default_file = candidate_files[0] if candidate_files else None

        for metric in REQUIRED_METRICS:
            current = metrics.get(metric)
            if current is not None:
                continue

            report["attempts"] += 1

            file_path = default_file or guess_file_for_period(period_key)
            if not file_path:
                report["still_missing"].append({
                    "period": period_key,
                    "metric": metric,
                    "reason": "no_file_found"
                })
                continue

            try:
                proofs = extract_metric_from_file(file_path, metric, period_label=None)
            except Exception as ex:
                report["still_missing"].append({
                    "period": period_key,
                    "metric": metric,
                    "reason": f"extract_error: {ex}"
                })
                continue

            if proofs:
                best = proofs[0]
                gt[period_key][metric] = best
                report["filled"].append({
                    "period": period_key,
                    "metric": metric,
                    "file": file_path
                })
            else:
                report["still_missing"].append({
                    "period": period_key,
                    "metric": metric,
                    "reason": "no_proof_found"
                })

    OUT_PATH.write_text(json.dumps(gt, indent=2, ensure_ascii=False), encoding="utf-8")
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Updated ground truth written to: {OUT_PATH}")
    print(f"Fill report written to: {REPORT_PATH}")
    print(f"Filled: {len(report['filled'])}, Still missing: {len(report['still_missing'])}, Attempts: {report['attempts']}")

if __name__ == "__main__":
    main()
