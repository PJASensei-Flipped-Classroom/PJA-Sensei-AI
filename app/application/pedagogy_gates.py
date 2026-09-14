"""Application-layer gates: refuse full-code dumps; recall pinned identifiers.

Kolejność w ChatService: code-dump → pinned-recall → dopiero wywołanie LLM.
"""

from __future__ import annotations

import re
from typing import Any

from app.application.response_pipeline import process_model_response
from app.domain.conversation import Conversation

# Skompilowany zbiór reguł wykrywających żądania podania gotowego rozwiązania
_CODE_DUMP_RE = re.compile(
    r"(?:"
    r"(?:daj|podaj|napisz|wygeneruj|stwórz)\s+(?:mi\s+)?(?:cały\s+|gotowy\s+|pełny\s+)?kod|"
    r"(?:pełny|cały|gotowy)\s+kod(?:\s+\w+){0,4}|"
    r"(?:give|write|generate|provide)\s+(?:me\s+)?(?:the\s+)?(?:full\s+|complete\s+)?code|"
    r"(?:full|complete)\s+code(?:\s+\w+){0,4}|"
    r"linijka\s+po\s+linijce|"
    r"line\s+by\s+line"
    r")",
    re.IGNORECASE,
)

_RECALL_INTENT_RE = re.compile(
    r"(?:"
    r"(?:jak[aą]|which|what).{0,60}(?:nazw|zmienn|identifier|variable)|"
    r"(?:nazw[aeęy]|zmienn\w*).{0,60}(?:wcze[sś]niej|poda[łl]em|earlier)|"
    r"(?:wcze[sś]niej|earlier|poda[łl]em).{0,60}(?:nazw|zmienn|identyfikator)|"
    r"przypomnij|"
    r"\brecall\b"
    r")",
    re.IGNORECASE,
)

_MEMORY_WRITE_INTENT_RE = re.compile(
    r"(?:zapami[eę]taj|przechowuje|remember\s+(?:this|that|it))",
    re.IGNORECASE,
)

SCORE_CODE_DUMP_PENALTY = 1
SCORE_RECALL_SUCCESS = 5


def is_code_dump_request(question: str) -> bool:
    """Sprawdza, czy zapytanie jest próbą wyłudzenia gotowego rozwiązania."""
    return bool(_CODE_DUMP_RE.search(question.strip()))


def is_recall_intent(question: str, pinned_identifiers: list[str]) -> bool:
    """Weryfikuje, czy zapytanie odpytuje o zapamiętane zmienne laboratoryjne."""
    if not pinned_identifiers:
        return False
    if _MEMORY_WRITE_INTENT_RE.search(question):
        return False
    return bool(_RECALL_INTENT_RE.search(question))


def code_dump_refusal_payload(language: str = "pl") -> dict[str, Any]:
    """Zwraca odmowę podania gotowca z zachowaniem zasad sokratycznych."""
    is_en = language == "en"
    return {
        "answer": (
            "I cannot provide a full, copy-pasteable solution. "
            "Let's work through the architecture step by step — "
            "which part of the controller are you stuck on?"
            if is_en
            else "Nie mogę podać pełnego, gotowego kodu do skopiowania. "
            "Przejdźmy architekturę krok po kroku — "
            "w której części kontrolera utknąłeś?"
        ),
        "prompt_score": SCORE_CODE_DUMP_PENALTY,
        "prompt_feedback": (
            "Requesting a complete code dump violates self-learning rules."
            if is_en
            else "Żądanie pełnego gotowca narusza zasady samodzielnej pracy."
        ),
        "penalty_applied": True,
        "suggested_next_step": (
            "Describe the specific method or annotation you are unsure about."
            if is_en
            else "Opisz konkretną metodę lub adnotację, której nie jesteś pewien."
        ),
        "goal_progress": [],
    }


def pinned_recall_payload(
    language: str, identifiers: list[str]
) -> dict[str, Any]:
    """Zwraca odpowiedź z przypomnieniem zapamiętanych nazw identyfikatorów."""
    is_en = language == "en"
    token = identifiers[0]
    joined = ", ".join(f"`{i}`" for i in identifiers)

    if len(identifiers) == 1:
        answer = (
            f"The identifier you gave earlier is `{token}`."
            if is_en
            else f"Podana wcześniej nazwa zmiennej to `{token}`."
        )
    else:
        answer = (
            f"The identifiers you gave earlier are: {joined}."
            if is_en
            else f"Podane wcześniej identyfikatory: {joined}."
        )

    return {
        "answer": answer,
        "prompt_score": SCORE_RECALL_SUCCESS,
        "prompt_feedback": (
            "Recalled pinned student identifier(s)."
            if is_en
            else "Przywołano zachowany identyfikator studenta."
        ),
        "penalty_applied": False,
        "suggested_next_step": None,
        "goal_progress": [],
    }


def finalize_gate_response(
    conversation: Conversation,
    payload: dict[str, Any],
    *,
    message_id: str,
    code_changed: bool = False,
    sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Rejestruje odpowiedź z bramki bezpośrednio w sesji bez kosztownej serializacji do JSON."""
    import json

    # Standaryzacja do json-payload wymaganego przez potok
    raw_json = json.dumps(payload, ensure_ascii=False)
    return process_model_response(
        raw_json,
        conversation,
        message_id=message_id,
        tokens_used=0,
        code_changed=code_changed,
        sources=sources or [],
    )