import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

from agents import extractor_adapter_hybrid as h
from agents.selector import post_process_proofs_select_best

MISSING_TSV = Path("src/eval/logs/missing_periods.tsv")
GT_FILE = Path("src/eval/ground_truth.jsonl")
LOG_FILE = Path("src/eval/logs/auto_fill_exact.log")

# prepare log
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
with LOG_FILE.open("w", encoding="utf-8") as lf:
    lf.write("auto_fill_exact started\n")

if not MISSING_TSV.exists():
    print("ERROR: missing_periods.tsv not found at", MISSING_TSV)
    sys.exit(1)

# load existing canonical keys to avoid duplicates (file,period,metric)
existing = set()
if GT_FILE.exists():
    for line in GT_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            j = json.loads(line)
            existing.add((j.get("file"), j.get("period"), j.get("metric")))
        except Exception:
            continue

for raw in MISSING_TSV.read_text(encoding="utf-8").splitlines():
    s = raw.strip()
    if not s:
        continue
    # expecting "Q1_2024<tab>metric_key" or space-separated
    parts = s.split()
    if len(parts) < 2:
        # fallback try split by tab
        parts = s.split("\t")
    period_key = parts[0]
    metric_key = parts[1]
    period = period_key.replace("_", " ")

    files = glob.glob(f"data/raw/*{period}*.pdf")
    if not files:
        with LOG_FILE.open("a", encoding="utf-8") as lf:
            lf.write(f"NOFILE\t{period}\t{metric_key}\n")
        print("NOFILE", period, metric_key)
        continue

    file_path = files[0]
    fname = Path(file_path).name

    # skip if already present
    if (fname, period, metric_key) in existing:
        print("SKIP_EXISTS", fname, period, metric_key)
        with LOG_FILE.open("a", encoding="utf-8") as lf:
            lf.write(f"SKIP_EXISTS\t{fname}\t{period}\t{metric_key}\n")
        continue

    try:
        proofs = h.extract_metric_from_file(file_path, metric_key, period_label=period)
    except Exception as e:
        with LOG_FILE.open("a", encoding="utf-8") as lf:
            lf.write(f"EXTRACT_ERROR\t{fname}\t{period}\t{metric_key}\t{repr(e)}\n")
        print("EXTRACT_ERROR", fname, period, metric_key, e)
        continue

    if not proofs:
        with LOG_FILE.open("a", encoding="utf-8") as lf:
            lf.write(f"NOPROOF\t{fname}\t{period}\t{metric_key}\n")
        print("NOPROOF", fname, period, metric_key)
        continue

    # pick best via selector if available
    best = None
    try:
        best_list = post_process_proofs_select_best(
            proofs, metric_key.replace("_", " "), metric_key, top_n=1, return_all=False
        )
        if best_list:
            best = best_list[0]
    except Exception:
        # fallback to first candidate
        best = proofs[0]

    if not best:
        with LOG_FILE.open("a", encoding="utf-8") as lf:
            lf.write(f"NOPROOF_SEL\t{fname}\t{period}\t{metric_key}\n")
        print("NOPROOF_SEL", fname, period, metric_key)
        continue

    # sanitize best to make JSON-serializable (strip callables etc)
    # (proof items are primitives; ensure no stray non-serializable)
    def sanitize(obj):
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        if isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [sanitize(v) for v in obj]
        return str(obj)

    best_s = sanitize(best)

    gt = {"file": fname, "period": period, "metric": metric_key, "proof": best_s}

    # append to ground truth
    try:
        with GT_FILE.open("a", encoding="utf-8") as outf:
            outf.write(json.dumps(gt, ensure_ascii=False) + "\n")
        existing.add((fname, period, metric_key))
        with LOG_FILE.open("a", encoding="utf-8") as lf:
            lf.write(f"OK\t{fname}\t{period}\t{metric_key}\n")
        print("OK", fname, period, metric_key)
    except Exception as e:
        with LOG_FILE.open("a", encoding="utf-8") as lf:
            lf.write(f"APPEND_ERROR\t{fname}\t{period}\t{metric_key}\t{repr(e)}\n")
        print("APPEND_ERROR", fname, period, metric_key, e)

print("auto_fill_exact completed")
