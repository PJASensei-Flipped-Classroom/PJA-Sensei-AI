"""Bramki pedagogiczne warstwy aplikacji: odmowa generowania gotowców oraz przypominanie identyfikatorów."""

from __future__ import annotations

import json
import re
from typing import Any

from app.application.response_pipeline import process_model_response
from app.domain.conversation import Conversation

SCORE_CODE_DUMP_PENALTY = 1
SCORE_RECALL_SUCCESS = 5

# Wyrażenie wykrywające prośby o napisanie całego rozwiązania za studenta
_CODE_DUMP_PATTERN = re.compile(
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

# Wyrażenie wykrywające intencję odpytania o zapamiętane nazwy zmiennych/funkcji
_RECALL_INTENT_PATTERN = re.compile(
    r"(?:"
    r"(?:jak[aą]|which|what).{0,60}(?:nazw|zmienn|identifier|variable)|"
    r"(?:nazw[aeęy]|zmienn\w*).{0,60}(?:wcze[sś]niej|poda[łl]em|earlier)|"
    r"(?:wcze[sś]niej|earlier|poda[łl]em).{0,60}(?:nazw|zmienn|identyfikator)|"
    r"przypomnij|"
    r"\brecall\b"
    r")",
    re.IGNORECASE,
)

# Wyrażenie wykluczające: polecenia zapisu do pamięci (nie mylić z odczytem)
_MEMORY_WRITE_PATTERN = re.compile(
    r"(?:zapami[eę]taj|przechowuje|remember\s+(?:this|that|it))",
    re.IGNORECASE,
)

_CODE_DUMP_MESSAGES: dict[str, dict[str, str]] = {
    "pl": {
        "answer": (
            "Nie mogę podać pełnego, gotowego kodu do skopiowania. "
            "Przejdźmy architekturę krok po kroku — "
            "w której części kontrolera utknąłeś?"
        ),
        "feedback": "Żądanie pełnego gotowca narusza zasady samodzielnej pracy.",
        "next_step": "Opisz konkretną metodę lub adnotację, której nie jesteś pewien.",
    },
    "en": {
        "answer": (
            "I cannot provide a full, copy-pasteable solution. "
            "Let's work through the architecture step by step — "
            "which part of the controller are you stuck on?"
        ),
        "feedback": "Requesting a complete code dump violates self-learning rules.",
        "next_step": "Describe the specific method or annotation you are unsure about.",
    },
}


def is_code_dump_request(question: str) -> bool:
    """Sprawdza, czy zapytanie studenta to próba wyłudzenia gotowego kodu bez wysiłku poznawczego."""
    return bool(_CODE_DUMP_PATTERN.search(question.strip()))


def is_recall_intent(question: str, pinned_identifiers: list[str]) -> bool:
    """Weryfikuje, czy student pyta o zdefiniowaną wcześniej nazwę zmiennej lub identyfikator."""
    if not pinned_identifiers:
        return False
    # Jeśli student każe zapamiętać nowy identyfikator, nie jest to intencja odczytu (recall)
    if _MEMORY_WRITE_PATTERN.search(question):
        return False
    return bool(_RECALL_INTENT_PATTERN.search(question))


def code_dump_refusal_payload(language: str = "pl") -> dict[str, Any]:
    """Generuje odpowiedź odmawiającą gotowca i kierującą na sokratejską ścieżkę nauki."""
    lang_key = "en" if language == "en" else "pl"
    texts = _CODE_DUMP_MESSAGES[lang_key]

    return {
        "answer": texts["answer"],
        "prompt_score": SCORE_CODE_DUMP_PENALTY,
        "prompt_feedback": texts["feedback"],
        "penalty_applied": True,
        "suggested_next_step": texts["next_step"],
        "goal_progress": [],
    }


def pinned_recall_payload(
    language: str,
    identifiers: list[str],
) -> dict[str, Any]:
    """Generuje natychmiastową odpowiedź przypominającą zapamiętane identyfikatory laboratoryjne."""
    is_en = language == "en"
    joined_identifiers = ", ".join(f"`{ident}`" for ident in identifiers)

    if len(identifiers) == 1:
        single_ident = identifiers[0]
        answer = (
            f"The identifier you gave earlier is `{single_ident}`."
            if is_en
            else f"Podana wcześniej nazwa zmiennej to `{single_ident}`."
        )
    else:
        answer = (
            f"The identifiers you gave earlier are: {joined_identifiers}."
            if is_en
            else f"Podane wcześniej identyfikatory: {joined_identifiers}."
        )

    feedback = (
        "Recalled pinned student identifier(s)."
        if is_en
        else "Przywołano zachowany identyfikator studenta."
    )

    return {
        "answer": answer,
        "prompt_score": SCORE_RECALL_SUCCESS,
        "prompt_feedback": feedback,
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
    """Formułuje gotową odpowiedź bramki przez wspólny pipeline odpowiedzi bez odpytywania modelu LLM."""
    raw_json = json.dumps(payload, ensure_ascii=False)
    return process_model_response(
        raw_json,
        conversation,
        message_id=message_id,
        tokens_used=0,
        code_changed=code_changed,
        sources=sources or [],
    )