# src/eval/ground_truth_validator.py
import json
from pathlib import Path

GT_FILE = Path("data/ground_truth/financial_metrics.json")
REPORT_DIR = Path("src/eval/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_FILE = REPORT_DIR / "gt_validation_report.json"

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

def load_gt():
    if not GT_FILE.exists():
        raise FileNotFoundError(GT_FILE)
    return json.loads(GT_FILE.read_text(encoding="utf-8"))

def validate(gt):
    report = {"periods": {}, "summary": {"period_count": 0, "missing": 0, "invalid": 0}}
    for period, metrics in sorted(gt.items()):
        period_report = {"missing": [], "invalid": []}
        for m in REQUIRED_METRICS:
            val = metrics.get(m)
            if val is None:
                period_report["missing"].append(m)
                report["summary"]["missing"] += 1
            else:
                # Expect a numeric value_millions field
                vm = val.get("value_millions") if isinstance(val, dict) else None
                if vm is None or not isinstance(vm, (int, float)) or vm <= 0:
                    period_report["invalid"].append({"metric": m, "value_millions": vm})
                    report["summary"]["invalid"] += 1
        report["periods"][period] = period_report
    report["summary"]["period_count"] = len(gt)
    return report

def main():
    gt = load_gt()
    report = validate(gt)
    REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Validation report written to:", REPORT_FILE)
    # print short summary
    print("Periods:", report["summary"]["period_count"])
    print("Missing metrics:", report["summary"]["missing"])
    print("Invalid values:", report["summary"]["invalid"])

if __name__ == "__main__":
    main()
