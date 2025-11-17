# type: ignore
import json
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, "src")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

MISSING_TSV = Path("src/eval/logs/missing_periods.tsv")
OUT_JSONL = Path("src/eval/ground_truth.jsonl")
RAW_DIR = Path("data/raw")

if not MISSING_TSV.exists():
    print("ERROR: missing_periods.tsv not found at", MISSING_TSV)
    raise SystemExit(1)

from agents import extractor_adapter_hybrid as hybrid
from agents.selector import post_process_proofs_select_best

lines = [
    l.strip()
    for l in MISSING_TSV.read_text(encoding="utf-8", errors="ignore").splitlines()
    if l.strip()
]
if not lines:
    print("NO_MISSING_ENTRIES")
    raise SystemExit(0)

filled = []
skipped = []


def find_files_for_period(period_str):
    """
    period_str examples: 'Q1_2024', 'Q1 2024', 'Q1_2024'
    Return list of Path objects in data/raw matching quarter + year heuristically.
    """
    m = re.search(r"Q([1-4])[_\-\s]?(\d{4})", period_str, re.IGNORECASE)
    candidates = []
    if not m:
        # fallback: try period_str appearing in filename
        for f in RAW_DIR.glob("*"):
            if (
                period_str.replace("_", "-") in f.name
                or period_str.replace("_", " ") in f.name
            ):
                candidates.append(f)
        return candidates
    q = m.group(1)
    year = m.group(2)
    # search filenames that contain Q{q} and year
    for f in RAW_DIR.glob("*"):
        name_upper = f.name.upper()
        if f"Q{q}" in name_upper and year in name_upper:
            candidates.append(f)
    # if nothing found, try looser match: year only
    if not candidates:
        for f in RAW_DIR.glob("*"):
            if year in f.name:
                candidates.append(f)
    return candidates


for ln in lines:
    # parse line: either "file<TAB>period<TAB>metric" OR "period<TAB>metric" OR "Q1_2024 metric"
    filep = None
    period = None
    metric = None
    if "\t" in ln:
        parts = ln.split("\t")
        if len(parts) == 3:
            filep, period, metric = parts
        elif len(parts) == 2:
            # period<TAB>metric
            period, metric = parts
        else:
            # join rest as metric
            filep = parts[0] if parts else None
            period = parts[1] if len(parts) > 1 else None
            metric = "\t".join(parts[2:]) if len(parts) > 2 else None
    else:
        parts = ln.split()
        # if first token looks like Qn or Qn_yyyy
        if parts and re.match(r"^Q[1-4][_\-\s]?\d{4}$", parts[0], re.IGNORECASE):
            period = parts[0]
            metric = " ".join(parts[1:]) if len(parts) > 1 else None
        elif len(parts) >= 2:
            # last token(s) metric, first token maybe filename
            # assume "file period metric" or "period metric"
            if re.search(r"Q[1-4]", parts[1], re.IGNORECASE):
                filep = parts[0]
                period = parts[1]
                metric = " ".join(parts[2:]) if len(parts) > 2 else None
            else:
                period = parts[0]
                metric = " ".join(parts[1:])
        else:
            print("SKIP unparseable line:", ln)
            skipped.append(ln)
            continue

    if not metric or not period:
        print("SKIP incomplete line:", ln)
        skipped.append(ln)
        continue

    file_candidates = []
    if filep:
        # normalize file path
        candidate = Path(filep)
        if not candidate.is_absolute():
            candidate = Path("data/raw") / candidate
        if candidate.exists():
            file_candidates = [candidate]
        else:
            # try matching basename in data/raw
            matches = list(Path("data/raw").glob(f"*{Path(filep).stem}*"))
            file_candidates = matches
    else:
        file_candidates = find_files_for_period(period)

    if not file_candidates:
        print(f"  NO FILE FOUND for period {period} (line: {ln})")
        skipped.append((period, metric))
        continue

    # try each candidate file until we get proofs
    proofs = []
    chosen_file = None
    for f in file_candidates:
        try:
            proofs = hybrid.extract_metric_from_file(
                str(f), metric.strip(), period_label=period.strip()
            )
        except FileNotFoundError:
            continue
        except Exception as e:
            print("  extractor error for", f.name, ":", e)
            continue
        if proofs:
            chosen_file = f
            break

    if not proofs:
        print(
            "  NO_PROOFS_RETURNED for",
            metric,
            "period",
            period,
            "candidates:",
            [p.name for p in file_candidates],
        )
        skipped.append((file_candidates, period, metric))
        continue

    # select best via selector when available
    try:
        best = post_process_proofs_select_best(
            proofs, metric.replace("_", " "), metric, top_n=1, return_all=False
        )
        candidate = best[0] if best else proofs[0]
    except Exception:
        candidate = proofs[0]

    candidate_clean = {}
        # TODO: Fix Path.items() -     for k, v in candidate.items():
        try:
            json.dumps(v)  # test serializable
            candidate_clean[k] = v
        except Exception:
            candidate_clean[k] = str(v)

    entry = {
        "file": chosen_file.name if chosen_file else (filep if filep else None),
        "period": period,
        "metric": metric,
        "proof": candidate_clean,
    }

    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSONL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print("  FILLED ->", entry["file"], entry["period"], entry["metric"])
    filled.append((entry["file"], entry["period"], entry["metric"]))

print("\\nSummary:")
print("  Filled:", len(filled))
print("  Skipped:", len(skipped))
if skipped:
    print("  Skipped sample:")
    for s in skipped[:10]:
        print("   ", s)
