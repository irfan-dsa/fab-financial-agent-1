# src/eval/normalize_ground_truth.py
import json
from pathlib import Path

IN_FILE = Path("src/eval/ground_truth.jsonl")
OUT_DIR = Path("data/ground_truth")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "financial_metrics.json"

def load_lines(path):
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            yield json.loads(line)

def normalize():
    out = {}
    for rec in load_lines(IN_FILE):
        period = rec.get("period")  # e.g. "Q3 2023"
        metric = rec.get("metric")
        proof = rec.get("proof")
        if not period or not metric:
            continue
        key = period.replace(" ", "_")  # Q3_2023
        out.setdefault(key, {})
        # If multiple proofs for same metric, keep first (highest-confidence)
        if metric in out[key]:
            continue
        out[key][metric] = proof
    with OUT_FILE.open("w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print("Wrote canonical ground truth to:", OUT_FILE)

if __name__ == "__main__":
    normalize()
