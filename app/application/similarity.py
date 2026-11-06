from __future__ import annotations

import re
from typing import Dict, List, Optional


def _tokens(text: str) -> set:
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", (text or "").lower()))


def jaccard_similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def best_solution_match(
    student_code: str,
    solution_pack: List[str],
) -> Dict[str, Optional[float]]:
    if not student_code or not solution_pack:
        return {"best_score": None, "best_index": None, "flagged": False}

    best_score = 0.0
    best_index = 0
    for i, sol in enumerate(solution_pack):
        score = jaccard_similarity(student_code, sol)
        if score > best_score:
            best_score = score
            best_index = i

    flagged = best_score >= 0.55
    return {
        "best_score": round(best_score, 4),
        "best_index": best_index,
        "flagged": flagged,
        "threshold": 0.55,
    }
