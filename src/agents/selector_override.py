from typing import Any, Dict, List

from agents.selector import post_process_proofs_select_best


def select_best_with_phrase_boost(
    proofs: List[Dict[str, Any]],
    canonical_phrase: str,
    metric_key: str,
    top_n: int = 1,
    return_all: bool = False,
):
    # Get baseline scored items
    try:
        scored = post_process_proofs_select_best(
            proofs,
            canonical_phrase,
            metric_key,
            top_n=max(top_n, len(proofs)),
            return_all=True,
        )
    except Exception:
        scored = []
        for p in proofs:
            pp = dict(p)
            pp.setdefault("selection_score", 0)
            scored.append(pp)

    cp = canonical_phrase.lower()

    # Apply boosts
    for p in scored:
        raw = p.get("raw_line", "").lower()
        boost = 0
        reasons = p.setdefault("extraction_reason", [])

        if cp in raw:
            boost += 100
            reasons.append("contains_canonical_phrase")

        if raw.startswith(cp):
            boost += 50
            reasons.append("startswith_canonical")

        # numeric token heuristic
        nums = [
            t
            for t in raw.replace("(", " ").replace(")", " ").split()
            if any(c.isdigit() for c in t)
        ]
        if len(nums) >= 1:
            boost += 5
            reasons.append(f"nums={len(nums)}")

        old_score = p.get("selection_score", 0)
        p["selection_score"] = old_score + boost
        p["confidence"] = min(1.0, old_score / 100 + boost / 200)

    scored.sort(key=lambda x: x.get("selection_score", 0), reverse=True)

    if return_all:
        return scored
    return scored[: max(1, top_n)]
