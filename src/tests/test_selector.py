import sys, json
sys.path.insert(0, "src")
from agents import extractor_adapter_hybrid as hybrid
from agents.selector import post_process_proofs_select_best

def test_net_fee_selector_q1_2024():
    p = "data/raw/FAB-FS-Q1-2024-English.pdf"
    proofs = hybrid.extract_metric_from_file(p, "net_fee_and_commission_income", period_label="Q1 2024")
    # ensure we got candidates
    assert isinstance(proofs, list) and len(proofs) >= 1, "No proofs returned for test file"
    best = post_process_proofs_select_best(proofs, "Net fee and commission income", "net_fee_and_commission_income", top_n=1, return_all=False)
    assert isinstance(best, list) and len(best) >= 1
    top = best[0]
    # expected top candidate starts with canonical phrase, exact match, confidence high
    assert "net fee and commission income" in top["raw_line"].lower() or "net fee and commission" in top["raw_line"].lower()
    assert top["confidence"] >= 0.45, f"Top candidate confidence too low: {top['confidence']}"
