import sys, json
from pathlib import Path
sys.path.insert(0, 'src')
from agents import extractor_adapter_hybrid as h

gt_path = Path('src/eval/ground_truth.jsonl')
if not gt_path.exists():
    print('ERROR: ground_truth.jsonl not found'); sys.exit(1)

lines = [l for l in gt_path.read_text(encoding='utf-8').splitlines() if l.strip()]
first = None
for l in lines:
    o = json.loads(l)
    if ('proof' not in o) or (o.get('proof') in (None, {}, [])):
        first = o
        break

if not first:
    print('NO_MISSING_ENTRIES'); sys.exit(0)

file = first['file']
period = first.get('period') or first.get('quarter') or ''
metric = first['metric']

print('SAMPLE:', file, period, metric)
proofs = h.extract_metric_from_file(file, metric, period_label=period)
print('PROOFS_RETURNED:', len(proofs))
print(json.dumps(proofs, ensure_ascii=False, indent=2))
