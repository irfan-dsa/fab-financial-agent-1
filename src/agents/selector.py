import re
from typing import Any, Dict, List


def post_process_proofs_select_best(
    proofs: List[Dict[str, Any]],
    canonical_phrase: str,
    metric_key: str,
    top_n: int = 1,
    return_all: bool = False,
    min_confidence: float = 0.45,
) -> List[Dict[str, Any]]:
    """
    Deterministic scorer/selector.
    """

    def score_proof(p: Dict[str, Any]):
        reasons = []
        score = 0
        line = (p.get("raw_line") or "").lower()
        canon = (canonical_phrase or "").lower()

        if canon and canon in line:
            score += 60
            reasons.append("exact_phrase")
            if line.strip().startswith(canon):
                score += 25
                reasons.append("startswith")

        alias = metric_key.replace("_", " ")
        if alias and alias in line:
            score += 10
            reasons.append("alias")

        nums = re.findall(r"[0-9]{1,3}(?:,[0-9]{3})+|[0-9]{5,}", line)
        if nums:
            score += min(15, 5 * len(nums))
            reasons.append(f"nums={len(nums)}")

        if "interest" in line and ("fee" not in line and "commission" not in line):
            score -= 40
            reasons.append("interest_penalty")

        score = max(-100, min(100, score))
        confidence = max(0.0, score) / 100.0
        return int(score), round(float(confidence), 3), reasons

    scored = []
    for p in proofs or []:
        s, conf, reasons = score_proof(p)
        p2 = dict(p)
        p2["selection_score"] = max(0, s)
        p2["confidence"] = conf
        p2["extraction_reason"] = reasons
        scored.append(p2)

    scored.sort(
        key=lambda x: (x.get("selection_score", 0), x.get("value_millions", 0)),
        reverse=True,
    )

    if return_all:
        return scored

    if not scored:
        return []

    if scored[0]["confidence"] >= min_confidence:
        return scored[:top_n]

    return scored[: max(1, top_n + 1)]
