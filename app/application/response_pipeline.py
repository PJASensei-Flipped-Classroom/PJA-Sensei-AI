"""Response post-processing pipeline: streaming extraction, safety gates, JSON recovery, and history compression."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.domain.conversation import Conversation, recent_avg_score

logger = logging.getLogger(__name__)

DEFAULT_CODE_FALLBACK_PL = (
    "Zauważyłem próbę wygenerowania gotowego kodu, co narusza zasady samodzielnej pracy. "
    "Zastanówmy się nad architekturą rozwiązania: jakich komponentów potrzebujesz?"
)
DEFAULT_CODE_FALLBACK_EN = (
    "I noticed an attempt to generate complete code, which violates the self-learning rules. "
    "Let's think about the concept together."
)

EMPTY_ANSWER_FALLBACK_PL = (
    "Cześć! Napisz konkretne pytanie o zadanie lub wklej fragment kodu, nad którym pracujesz."
)
EMPTY_ANSWER_FALLBACK_EN = (
    "Hi! Ask a concrete question about the assignment or paste the code you're working on."
)

_CODE_BLOCK_RE = re.compile(r"```([a-zA-Z0-9_-]*)\n(.*?)```", re.DOTALL)
_ANSWER_KEY_RE = re.compile(r'"answer"\s*:\s*"')

_IMPL_BODY_RE = re.compile(
    r"(public\s+class\s+\w+\s*\{[\s\S]{20,})"
    r"|(public\s+(static\s+)?[\w<>\[\]]+\s+\w+\s*\([^)]*\)\s*\{)"
    r"|(def\s+\w+\s*\([^)]*\)\s*:)"
    r"|(return\s+new\s+\w+\s*\()"
    r"|((?:for|while)\s*\([^\n]*\)\s*\{)",
    re.MULTILINE,
)

_IMPL_LINE_RE = re.compile(
    r"^\s*(?:public|private|protected)\s+"
    r"|^\s*def\s+\w+"
    r"|^\s*return\s+"
    r"|^\s*(?:if|for|while)\s*\("
    r"|^\s*\w+\s*=\s*new\s+"
    r"|^\s*(?:import|from)\s+\w+"
    r"|^\s*@\w+\s*$",
    re.MULTILINE,
)

_IDENTIFIER_RE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9_]{3,}\b")
_IDENTIFIER_STOP = frozenset(
    {
        "File",
        "Code",
        "Plik",
        "Kod",
        "None",
        "Brak",
        "Student",
        "question",
        "Pytanie",
        "studenta",
        "Error",
        "logs",
        "Logi",
        "class",
        "Test",
        "java",
        "Java",
    }
)


class IncrementalAnswerExtractor:
    """Wyciąga na bieżąco wartość tekstową pola 'answer' ze strumienia JSON."""

    def __init__(self) -> None:
        self._raw = ""
        self._emitted = 0

    def feed(self, piece: str) -> str:
        """Dokłada fragment strumienia; zwraca tylko nowo zdekodowany przyrost answer."""
        if not piece:
            return ""
        self._raw += piece
        partial = _decode_partial_json_string_field(self._raw)
        if len(partial) <= self._emitted:
            return ""
        delta = partial[self._emitted :]
        self._emitted = len(partial)
        return delta

    @property
    def answer_so_far(self) -> str:
        """Aktualnie zdekodowana wartość answer (może być niekompletna)."""
        return _decode_partial_json_string_field(self._raw)


def _decode_partial_json_string_field(raw: str) -> str:
    """Bezpiecznie dekoduje niekompletny ciąg znaków JSON ze strumienia."""
    match = _ANSWER_KEY_RE.search(raw)
    if not match:
        return ""
    i = match.end()
    out: list[str] = []
    raw_len = len(raw)
    simple_escapes = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "/": "/"}

    while i < raw_len:
        ch = raw[i]
        if ch == "\\":
            if i + 1 >= raw_len:
                break  # Urwana sekwencja ucieczki na końcu bufora
            nxt = raw[i + 1]
            if nxt in simple_escapes:
                out.append(simple_escapes[nxt])
                i += 2
                continue
            if nxt == "u":
                if i + 5 >= raw_len:
                    break  # Urwany kod \uXXXX
                hexpart = raw[i + 2 : i + 6]
                try:
                    out.append(chr(int(hexpart, 16)))
                    i += 6
                    continue
                except ValueError:
                    out.append(nxt)
                    i += 2
                    continue
            out.append(nxt)
            i += 2
            continue

        if ch == '"':
            break  # Prawidłowy koniec wartości JSON string
        out.append(ch)
        i += 1

    return "".join(out)


def contains_revealed_code(answer_text: str) -> bool:
    """Weryfikuje, czy model nie wygenerował niedozwolonej implementacji kodu."""
    for match in _CODE_BLOCK_RE.finditer(answer_text):
        lang = (match.group(1) or "").lower()
        body = match.group(2) or ""
        if lang not in ("diff", "text", "plaintext", "md", "markdown", "json"):
            lines = [ln for ln in body.splitlines() if ln.strip()]
            if len(lines) >= 2:
                return True

    if _IMPL_BODY_RE.search(answer_text):
        return True

    impl_lines = [
        line for line in answer_text.splitlines() if _IMPL_LINE_RE.search(line)
    ]
    return len(impl_lines) >= 2


def parse_model_json(raw_content: str, language: str = "pl") -> dict[str, Any]:
    """Kaskadowe parsowanie odpowiedzi JSON z obsługą błędów formatowania LLM."""
    cleaned = raw_content.strip()

    # 1. Próba bezpośredniego parsowania
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. Próba znalezienia pierwszego zbalansowanego obiektu JSON
    json_match = re.search(r"\{[\s\S]*\}", cleaned)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, ValueError):
            pass

    # 3. Ratunkowa ekstrakcja kluczowych pól wyrażeniami regularnymi
    ans_match = re.search(r'"answer"\s*:\s*"((?:\\.|[^"\\])*)"', cleaned)
    score_match = re.search(r'"prompt_score"\s*:\s*(\d+)', cleaned)
    feedback_match = re.search(
        r'"prompt_feedback"\s*:\s*"((?:\\.|[^"\\])*)"', cleaned
    )
    penalty_match = re.search(
        r'"penalty_applied"\s*:\s*(true|false)', cleaned, re.IGNORECASE
    )

    if ans_match:
        try:
            answer_val = json.loads(f'"{ans_match.group(1)}"')
        except Exception:
            answer_val = ans_match.group(1).replace(r"\"", '"')

        feedback_val = ""
        if feedback_match:
            try:
                feedback_val = json.loads(f'"{feedback_match.group(1)}"')
            except Exception:
                feedback_val = feedback_match.group(1).replace(r"\"", '"')

        return {
            "answer": answer_val,
            "prompt_score": int(score_match.group(1)) if score_match else 5,
            "prompt_feedback": feedback_val,
            "penalty_applied": (
                penalty_match.group(1).lower() == "true" if penalty_match else False
            ),
        }

    # 3b. Ucięty JSON: wyciągnij częściowe pole answer (bez zamykającego cudzysłowu)
    partial_answer = _decode_partial_json_string_field(cleaned)
    if partial_answer.strip():
        feedback_val = ""
        if feedback_match:
            try:
                feedback_val = json.loads(f'"{feedback_match.group(1)}"')
            except Exception:
                feedback_val = feedback_match.group(1).replace(r"\"", '"')
        if not feedback_val:
            feedback_val = (
                "Zadawaj pytania precyzyjniej, załączając fragmenty kodu."
                if language == "pl"
                else "Please ask more specific questions."
            )
        return {
            "answer": partial_answer.strip(),
            "prompt_score": int(score_match.group(1)) if score_match else 5,
            "prompt_feedback": feedback_val,
            "penalty_applied": False,
        }

    # 4. Fallback ostateczny (nie zwracaj surowego JSON-a jako answer)
    if cleaned.lstrip().startswith("{") and '"answer"' in cleaned:
        fallback_answer = (
            EMPTY_ANSWER_FALLBACK_PL if language == "pl" else EMPTY_ANSWER_FALLBACK_EN
        )
    else:
        fallback_answer = cleaned
    return {
        "answer": fallback_answer,
        "prompt_score": 3,
        "prompt_feedback": (
            "Zadawaj pytania precyzyjniej, załączając fragmenty kodu."
            if language == "pl"
            else "Please ask more specific questions."
        ),
        "penalty_applied": False,
    }


def process_model_response(
    raw_content: str,
    conversation: Conversation,
    *,
    message_id: str,
    tokens_used: int,
    code_changed: bool,
    sources: list[dict[str, Any]] | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Końcowy potok walidujący odpowiedź, wymuszający kary i utrwalający stan sesji."""
    lang = conversation.config.language
    result_data = parse_model_json(raw_content, lang)
    answer_text = str(result_data.get("answer", raw_content)).strip()
    score = int(result_data.get("prompt_score", 3))
    feedback_text = str(result_data.get("prompt_feedback", "")).strip()
    penalty_applied = bool(result_data.get("penalty_applied", False))
    suggested_next_step = (
        str(result_data.get("suggested_next_step") or "").strip() or None
    )

    # Gdy answer to nadal blob JSON — wyciągnij samo pole tekstowe.
    if answer_text.lstrip().startswith("{") and '"answer"' in answer_text:
        extracted = _decode_partial_json_string_field(answer_text).strip()
        if extracted:
            answer_text = extracted

    # Modele czasem zostawiają treść tylko w prompt_feedback — sync wymaga min_length=1.
    if not answer_text:
        answer_text = feedback_text or (
            EMPTY_ANSWER_FALLBACK_PL if lang == "pl" else EMPTY_ANSWER_FALLBACK_EN
        )

    # Bezpiecznik anty-kodowy (Hard safety override)
    if contains_revealed_code(answer_text):
        custom_fallback = conversation.config.agent_behavior.code_reveal_fallback
        fallback = custom_fallback or (
            DEFAULT_CODE_FALLBACK_PL if lang == "pl" else DEFAULT_CODE_FALLBACK_EN
        )
        answer_text, score, penalty_applied = fallback, 1, True

    # Standaryzacja celów dydaktycznych
    goal_progress: list[dict[str, str]] = []
    raw_progress = result_data.get("goal_progress")
    if isinstance(raw_progress, list):
        for item in raw_progress:
            if isinstance(item, dict) and (g := str(item.get("goal", "")).strip()):
                st = str(item.get("status", "not_started")).strip()
                goal_progress.append(
                    {
                        "goal": g,
                        "status": st
                        if st in ("not_started", "in_progress", "done")
                        else "not_started",
                    }
                )

    conversation.messages.append(
        {
            "role": "assistant",
            "content": answer_text,
            "message_id": message_id,
            "penalty_applied": penalty_applied,
            "prompt_score": score,
            "sources": sources or [],
            "suggested_next_step": suggested_next_step,
            "goal_progress": goal_progress,
            "model": model,
        }
    )
    conversation.prompt_scores.append(score)
    conversation.tokens_used_total += int(tokens_used or 0)
    conversation.touch()

    return {
        "message_id": message_id,
        "answer": answer_text,
        "prompt_score": score,
        "prompt_feedback": feedback_text,
        "penalty_applied": penalty_applied,
        "tokens_used": tokens_used,
        "is_cached": False,
        "sources": sources or [],
        "suggested_next_step": suggested_next_step,
        "goal_progress": goal_progress,
        "next_checkpoint": None,
        "model": model,
        "debug_info": {
            "is_frustrated": conversation.is_frustrated,
            "avg_score": round(recent_avg_score(conversation.prompt_scores), 2),
            "code_changed": code_changed,
        },
    }


def llm_error_fallback(message_id: str, language: str) -> dict[str, Any]:
    """Przyjazna odpowiedź zastępcza przy nie-429 błędzie dostawcy LLM."""
    is_en = language == "en"
    return {
        "message_id": message_id,
        "answer": (
            "Sorry, the model server hit a temporary technical issue. Please try asking again."
            if is_en
            else "Przepraszam, serwer modelu napotkał chwilowy problem techniczny. Spróbuj powtórzyć pytanie."
        ),
        "prompt_score": 5,
        "prompt_feedback": "External LLM API error." if is_en else "Błąd zewnętrznego API LLM.",
        "penalty_applied": False,
        "tokens_used": 0,
        "is_cached": False,
        "sources": [],
        "suggested_next_step": None,
        "goal_progress": [],
        "next_checkpoint": None,
        "model": None,
    }


PROVIDER_RATE_LIMITED_ID = "provider_rate_limited"


def rate_limit_fallback(_message_id: str, language: str) -> dict[str, Any]:
    """User-facing response when provider 429 persists after retry/fallback.

    ``message_id`` is the sentinel ``provider_rate_limited`` (same pattern as
    ``blocked`` / ``rejected``) so clients and live tests can detect the stub.
    The unused uuid argument is kept so call sites stay positional-compatible.
    """
    is_en = language == "en"
    return {
        "message_id": PROVIDER_RATE_LIMITED_ID,
        "answer": (
            "The AI provider is temporarily rate-limited. Please wait a moment and try again."
            if is_en
            else "Dostawca AI chwilowo ograniczył liczbę zapytań. Poczekaj chwilę i spróbuj ponownie."
        ),
        "prompt_score": 5,
        "prompt_feedback": (
            "Provider rate limit (429)."
            if is_en
            else "Limit zapytań u dostawcy (429)."
        ),
        "penalty_applied": False,
        "tokens_used": 0,
        "is_cached": False,
        "sources": [],
        "suggested_next_step": None,
        "goal_progress": [],
        "next_checkpoint": None,
        "model": None,
    }


def collect_identifier_tokens(text: str, *, limit: int = 12) -> list[str]:
    """Ekstrahuje nazwy zmiennych i metod (snake_case/camelCase) z wypowiedzi studenta."""
    found: list[str] = []
    seen: set[str] = set()
    for tok in _IDENTIFIER_RE.findall(text or ""):
        if tok in _IDENTIFIER_STOP or tok.lower() in seen:
            continue
        is_snake = "_" in tok
        is_camel = tok[0].islower() and any(c.isupper() for c in tok[1:])
        if is_snake or is_camel:
            seen.add(tok.lower())
            found.append(tok)
            if len(found) >= limit:
                break
    return found


def format_pinned_identifiers_note(identifiers: list[str], language: str) -> str:
    """Formatuje instrukcję systemową wymuszającą zapamiętanie nazw zmiennych."""
    if not identifiers:
        return ""
    joined = ", ".join(identifiers)
    if language == "en":
        return f"Pinned student identifiers (repeat exactly if asked): {joined}"
    return f"Zachowane identyfikatory studenta (powtórz dokładnie, gdy pyta): {joined}"


def compress_history(
    messages: list[dict[str, Any]],
    language: str,
    max_length: int = 16,
    pinned_identifiers: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Kompresuje historię czatu, zachowując kontekst początkowy, najświeższe wiadomości i identyfikatory."""
    if len(messages) <= max_length:
        return messages

    head: list[dict[str, Any]] = [messages[0]]
    if len(messages) > 1 and messages[1].get("role") == "assistant":
        head.append(messages[1])

    recent_count = 8
    recent_slice = messages[-recent_count:]
    if (
        recent_slice
        and recent_slice[0].get("role") == "assistant"
        and len(messages) > recent_count
    ):
        recent_slice = messages[-(recent_count + 1) :]

    head_ids = {id(m) for m in head}
    recent_slice = [m for m in recent_slice if id(m) not in head_ids]

    # Zbieranie identyfikatorów z ucinanych wiadomości
    blob = "\n".join(
        str(m.get("content") or "") for m in messages[:6] if m.get("role") == "user"
    )
    pinned_tokens = collect_identifier_tokens(blob)
    if pinned_identifiers:
        pinned_tokens = list(dict.fromkeys(pinned_tokens + list(pinned_identifiers)))

    is_en = language == "en"
    note_body = (
        "[System note: Middle conversation turns trimmed for performance. "
        "Initial context and pinned student identifiers are preserved.]"
        if is_en
        else "[Notatka systemu: Środkowa część rozmowy została skrócona. "
        "Początkowe ustalenia i zachowane identyfikatory zostały zachowane.]"
    )

    if pinned_tokens:
        recall_instruction = (
            "When the student asks for a name they gave earlier, "
            "repeat it EXACTLY from the list below — do not invent a substitute."
            if is_en
            else "Gdy student pyta o nazwę podaną wcześniej, "
            "powtórz ją DOKŁADNIE z listy poniżej — nie wymyślaj zamiennika."
        )
        tokens_str = ", ".join(pinned_tokens)
        note_body = f"{note_body}\n{recall_instruction}\nIdentifikatory: {tokens_str}"

    return head + [{"role": "system", "content": note_body}] + recent_slice