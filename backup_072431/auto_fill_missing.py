import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, "src")

# imports from your codebase
try:
    from agents import extractor_adapter_hybrid as hybrid
    from agents.selector import post_process_proofs_select_best
except Exception as e:
    print("ERROR importing hybrid/selector:", e)
    raise

IN_FILE = Path("src/eval/ground_truth.jsonl")
BACKUP = Path("src/eval/ground_truth.jsonl.bak")
OUT_JSON = Path("data/ground_truth/financial_metrics.fixed.json")
LOG = Path("src/eval/logs/auto_fill_missing.log")

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
LOG.parent.mkdir(parents=True, exist_ok=True)

# backup original if not already backed up
if IN_FILE.exists() and not BACKUP.exists():
    BACKUP.write_text(IN_FILE.read_text(encoding="utf-8"), encoding="utf-8")

lines = []
if not IN_FILE.exists():
    print("Input file missing:", IN_FILE)
    sys.exit(1)

for ln in IN_FILE.read_text(encoding="utf-8").splitlines():
    if not ln.strip():
        continue
    try:
        j = json.loads(ln)
        lines.append(j)
    except:
        print("Skipping invalid JSON line in ground_truth.jsonl")

filled = 0
attempted = 0
results = []

for entry in lines:
    file_path = entry.get("file")
    metric = entry.get("metric")
    period_label = entry.get("period")

    if entry.get("proof"):
        results.append(entry)
        continue

    attempted += 1
    try:
        proofs = hybrid.extract_metric_from_file(
            str(file_path), metric, period_label=period_label
        )

        if not proofs:
            entry["proof"] = None
            entry["fill_meta"] = {"status": "no_candidates"}
            results.append(entry)
            continue

        if isinstance(proofs, dict):
            proofs = [proofs]

        try:
            best = post_process_proofs_select_best(
                proofs, metric.replace("_", " "), metric, top_n=1, return_all=False
            )
            chosen = best[0] if isinstance(best, list) and best else best
        except:
            chosen = proofs[0]

        if chosen:
            entry["proof"] = {
                "metric": metric,
                "raw_line": chosen.get("raw_line"),
                "value_thousands": chosen.get("value_thousands"),
                "value_millions": chosen.get("value_millions"),
                "unit": chosen.get("unit", "AED millions"),
                "unit_hint": chosen.get("unit_hint", "AED'000"),
                "source_file": chosen.get("source_file", file_path),
                "page": chosen.get("page"),
                "chunk_id": chosen.get("chunk_id"),
                "selection_score": chosen.get("selection_score"),
                "confidence": chosen.get("confidence"),
                "extracted_at": chosen.get("extracted_at", time.time()),
            }
            entry["fill_meta"] = {"status": "filled", "method": "hybrid+selector"}
            filled += 1
        else:
            entry["proof"] = None
            entry["fill_meta"] = {"status": "no_best"}
    except Exception as e:
        entry["proof"] = None
        entry["fill_meta"] = {
            "status": "error",
            "error": str(e),
            "trace": traceback.format_exc()[:300],
        }

    results.append(entry)

# write canonical json
canonical = {}
for e in results:
    period = e.get("period", "UNKNOWN")
    metric = e.get("metric")
    canonical.setdefault(period, {})[metric] = e.get("proof")

OUT_JSON.write_text(
    json.dumps(canonical, indent=2, ensure_ascii=False), encoding="utf-8"
)
LOG.write_text(
    json.dumps({"attempted": attempted, "filled": filled}, indent=2), encoding="utf-8"
)

print(f"Attempted={attempted}, Filled={filled}")
