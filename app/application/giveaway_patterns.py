"""Shared detection of student requests for a full graded solution."""
# OLD: SOLUTION_GIVEAWAY_REGEXES (security.py) + GIVEAWAY_PATTERNS (pedagogy_gates.py)
#      + GIVEAWAY_REQUEST_RE (response_pipeline.py)
# Removed because: three slightly different pattern sets caused inconsistent block vs reject vs penalty.
import re
from typing import List, Pattern

GIVEAWAY_REGEXES: List[Pattern[str]] = [
    re.compile(
        r"napisz\s+(za\s+mnie|mi)\s+(?:cały\s+)?(?:kompletny\s+|gotowy\s+)?kod",
        re.IGNORECASE,
    ),
    re.compile(
        r"(daj|podaj|wygeneruj)\s+(mi\s+)?(gotowca|gotowe\s+rozwiązanie|cały\s+kod)",
        re.IGNORECASE,
    ),
    re.compile(r"rozwiąż\s+(za\s+mnie\s+)?całe\s+zadanie", re.IGNORECASE),
    re.compile(
        r"(napisz|podaj|wklej)\s+(mi\s+)?(całe|pełne|gotowe)\s+(rozwiązanie|zadanie|kod)",
        re.IGNORECASE,
    ),
    re.compile(r"rozwiązanie\s+krok\s+po\s+kroku\s+z\s+pełnym\s+kodem", re.IGNORECASE),
    re.compile(
        r"(write|give\s+me)\s+the\s+(full|complete|entire)\s+(code|solution)",
        re.IGNORECASE,
    ),
    re.compile(
        r"solve\s+the\s+(whole|entire)\s+(task|lab|problem)\s+for\s+me",
        re.IGNORECASE,
    ),
    re.compile(
        r"(write|give|paste)\s+(me\s+)?(the\s+)?(full|complete|entire|ready)\s+(solution|assignment|code)",
        re.IGNORECASE,
    ),
    re.compile(r"step\s+by\s+step\s+with\s+full\s+code", re.IGNORECASE),
    re.compile(
        r"(napisz\s+za\s+mnie|daj\s+gotow|cały\s+kod|gotowe\s+rozwiązanie|"
        r"write\s+the\s+full\s+code|give\s+me\s+the\s+full\s+code)",
        re.IGNORECASE,
    ),
]


def is_giveaway_request(text: str) -> bool:
    q = text or ""
    return any(pattern.search(q) for pattern in GIVEAWAY_REGEXES)
