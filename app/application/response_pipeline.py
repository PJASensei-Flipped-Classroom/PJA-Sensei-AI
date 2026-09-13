import json
import re
from typing import Any

from app.domain.conversation import Conversation, recent_avg_score

DEFAULT_CODE_FALLBACK_PL = (
    "Zauważyłem próbę wygenerowania gotowego kodu, co narusza zasady samodzielnej pracy. "
    "Zastanówmy się nad architekturą rozwiązania: jakich komponentów potrzebujesz?"
)

DEFAULT_CODE_FALLBACK_EN = (
    "I noticed an attempt to generate complete code, which violates the self-learning rules. "
    "Let's think about the concept together."
)

_CODE_BLOCK_RE = re.compile(r"```([a-zA-Z0-9_-]*)\n(.*?)```", re.DOTALL)

_ANSWER_KEY_RE = re.compile(r'"answer"\s*:\s*"')


class IncrementalAnswerExtractor:
    """Extract the JSON string value of ``answer`` as it streams in character-by-character."""

    def __init__(self) -> None:
        self._raw = ""
        self._emitted = 0

    def feed(self, piece: str) -> str:
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
        return _decode_partial_json_string_field(self._raw)


def _decode_partial_json_string_field(raw: str) -> str:
    """Return decoded contents of the ``answer`` string seen so far (may be incomplete)."""
    match = _ANSWER_KEY_RE.search(raw)
    if not match:
        return ""
    i = match.end()
    out: list[str] = []
    while i < len(raw):
        ch = raw[i]
        if ch == "\\":
            if i + 1 >= len(raw):
                break  # incomplete escape — wait for more bytes
            nxt = raw[i + 1]
            simple = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "/": "/"}
            if nxt in simple:
                out.append(simple[nxt])
                i += 2
                continue
            if nxt == "u":
                if i + 5 >= len(raw):
                    break
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
            break  # end of JSON string
        out.append(ch)
        i += 1
    return "".join(out)


_IMPL_BODY_RE = re.compile(
    r"(public\s+class\s+\w+\s*\{[\s\S]{20,})"
    r"|(public\s+(static\s+)?[\w<>\[\]]+\s+\w+\s*\([^)]*\)\s*\{)"
    r"|(def\s+\w+\s*\([^)]*\)\s*:)"
    r"|(return\s+new\s+\w+\s*\()"
    # for/while header may contain nested () e.g. list.size()
    r"|((?:for|while)\s*\([^\n]*\)\s*\{)",
    re.MULTILINE,
)

_IMPL_LINE_RE = re.compile(
    r"^\s*(public|private|protected)\s+"
    r"|^\s*def\s+\w+"
    r"|^\s*return\s+"
    r"|^\s*(if|for|while)\s*\("
    r"|^\s*\w+\s*=\s*new\s+"
)


def _fenced_block_is_implementation(block_body: str, lang_hint: str) -> bool:
    if lang_hint.lower() in ("diff", "text", "plaintext", "md", "markdown", "json"):
        return False
    lines = [ln for ln in block_body.splitlines() if ln.strip()]
    return len(lines) >= 2


def contains_revealed_code(answer_text: str) -> bool:
    """True if the answer looks like a full implementation dump (fenced or raw)."""
    for match in _CODE_BLOCK_RE.finditer(answer_text):
        lang_hint = match.group(1) or ""
        body = match.group(2) or ""
        if _fenced_block_is_implementation(body, lang_hint):
            return True

    if _IMPL_BODY_RE.search(answer_text):
        return True

    impl_lines = [
        line
        for line in answer_text.splitlines()
        if _IMPL_LINE_RE.search(line)
    ]
    return len(impl_lines) >= 3


def code_reveal_fallback(conversation: Conversation) -> str:
    custom = getattr(conversation.config.agentBehavior, "codeRevealFallback", None)
    if custom:
        return custom
    if conversation.config.language == "pl":
        return DEFAULT_CODE_FALLBACK_PL
    return DEFAULT_CODE_FALLBACK_EN


def _safe_decode_json_string(val: str) -> str:
    """Decode a JSON string body safely; fall back to unescaping quotes only."""
    try:
        return json.loads(f'"{val}"')
    except Exception:
        return val.replace(r"\"", '"')


def parse_model_json(raw_content: str, language: str) -> dict[str, Any]:
    try:
        data = json.loads(raw_content.strip())
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, ValueError):
        pass

    # Non-recursive brace match (Python re has no (?R))
    json_match = re.search(r"\{.*?\}", raw_content, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(0).strip())
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, ValueError):
            pass

    ans_match = re.search(r'"answer"\s*:\s*"((?:\\.|[^"\\])*)"', raw_content)
    score_match = re.search(r'"prompt_score"\s*:\s*(\d+)', raw_content)
    feedback_match = re.search(
        r'"prompt_feedback"\s*:\s*"((?:\\.|[^"\\])*)"', raw_content
    )
    penalty_match = re.search(
        r'"penalty_applied"\s*:\s*(true|false)', raw_content, re.IGNORECASE
    )

    if ans_match:
        return {
            "answer": _safe_decode_json_string(ans_match.group(1)),
            "prompt_score": int(score_match.group(1)) if score_match else 5,
            "prompt_feedback": (
                _safe_decode_json_string(feedback_match.group(1))
                if feedback_match
                else ""
            ),
            "penalty_applied": (
                penalty_match.group(1).lower() == "true" if penalty_match else False
            ),
        }

    return {
        "answer": raw_content,
        "prompt_score": 3,
        "prompt_feedback": (
            "Zadawaj pytania precyzyjniej, załączając fragmenty kodu."
            if language == "pl"
            else "Please ask more specific questions."
        ),
        "penalty_applied": False,
    }


def apply_code_penalty(
    answer_text: str,
    score: int,
    penalty_applied: bool,
    conversation: Conversation,
) -> tuple[str, int, bool]:
    if contains_revealed_code(answer_text):
        return code_reveal_fallback(conversation), 1, True
    return answer_text, score, penalty_applied


def process_model_response(
    raw_content: str,
    conversation: Conversation,
    *,
    message_id: str,
    tokens_used: int,
    code_changed: bool,
    was_frustrated: bool,
    sources: list[dict] | None = None,
) -> dict[str, Any]:
    lang = conversation.config.language
    result_data = parse_model_json(raw_content, lang)

    answer_text = str(result_data.get("answer", raw_content)).strip()
    score = int(result_data.get("prompt_score", 3))
    feedback_text = str(result_data.get("prompt_feedback", "")).strip()
    penalty_applied = bool(result_data.get("penalty_applied", False))
    suggested_next_step = str(result_data.get("suggested_next_step") or "").strip() or None

    goals = conversation.config.learningContext.goals or []
    raw_progress = result_data.get("goal_progress") or []
    goal_progress: list[dict[str, str]] = []
    if isinstance(raw_progress, list):
        for item in raw_progress:
            if not isinstance(item, dict):
                continue
            goal = str(item.get("goal", "")).strip()
            status = str(item.get("status", "not_started")).strip()
            if status not in ("not_started", "in_progress", "done"):
                status = "not_started"
            if goal:
                goal_progress.append({"goal": goal, "status": status})
    if not goal_progress and goals:
        goal_progress = [{"goal": g, "status": "in_progress"} for g in goals[:3]]

    answer_text, score, penalty_applied = apply_code_penalty(
        answer_text, score, penalty_applied, conversation
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
        "debug_info": {
            # Current streak after this score (was_frustrated is pre-turn pedagogy only).
            "is_frustrated": conversation.is_frustrated,
            "avg_score": round(recent_avg_score(conversation.prompt_scores), 2),
            "code_changed": code_changed,
        },
    }


def llm_error_fallback(message_id: str, language: str) -> dict[str, Any]:
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
    }


_IDENTIFIER_RE = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]{3,}\b")

_IDENTIFIER_STOP = {
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


def collect_identifier_tokens(text: str, *, limit: int = 12) -> list[str]:
    """Prefer snake_case / camelCase tokens that look like student-named identifiers."""
    found: list[str] = []
    seen: set[str] = set()
    for tok in _IDENTIFIER_RE.findall(text or ""):
        if tok in _IDENTIFIER_STOP or tok.lower() in seen:
            continue
        if "_" in tok or (any(c.isupper() for c in tok[1:]) and tok[0].islower()):
            seen.add(tok.lower())
            found.append(tok)
        if len(found) >= limit:
            break
    return found


def _extract_pinned_facts(early_messages: list[dict], language: str, limit: int = 12) -> str:
    """Pull student-stated identifiers from early turns so compression does not erase them."""
    blob = "\n".join(
        str(m.get("content") or "")
        for m in early_messages
        if m.get("role") == "user"
    )
    found = collect_identifier_tokens(blob, limit=limit)
    if not found:
        return ""
    label = "Pinned student identifiers:" if language == "en" else "Zachowane identyfikatory studenta:"
    return f"{label} {', '.join(found)}"


def format_pinned_identifiers_note(identifiers: list[str], language: str) -> str:
    if not identifiers:
        return ""
    joined = ", ".join(identifiers)
    if language == "en":
        return (
            "Pinned student identifiers (repeat exactly if asked): "
            f"{joined}"
        )
    return (
        "Zachowane identyfikatory studenta (powtórz dokładnie, gdy pyta): "
        f"{joined}"
    )

def compress_history(
    messages: list[dict], language: str, max_length: int = 16
) -> list[dict]:
    if len(messages) <= max_length:
        return messages

    head: list[dict] = [messages[0]]
    if len(messages) > 1 and messages[1].get("role") == "assistant":
        head.append(messages[1])

    recent_count = 8
    recent_slice = messages[-recent_count:]
    if recent_slice and recent_slice[0].get("role") == "assistant" and len(messages) > recent_count:
        recent_slice = messages[-(recent_count + 1) :]

    # Avoid duplicating messages already kept in the head
    head_ids = {id(m) for m in head}
    recent_slice = [m for m in recent_slice if id(m) not in head_ids]

    pinned = _extract_pinned_facts(messages[:6], language)
    if language == "en":
        note_body = (
            "[System note: Middle conversation turns trimmed for performance. "
            "Initial context preserved.]"
        )
    else:
        note_body = (
            "[Notatka systemu: Środkowa część rozmowy została skrócona. "
            "Początkowe ustalenia zostały zachowane.]"
        )
    if pinned:
        if language == "en":
            recall = (
                "When the student asks for a name they gave earlier, "
                "repeat it EXACTLY from the list below — do not invent a substitute."
            )
        else:
            recall = (
                "Gdy student pyta o nazwę podaną wcześniej, "
                "powtórz ją DOKŁADNIE z listy poniżej — nie wymyślaj zamiennika."
            )
        note_body = f"{note_body}\n{recall}\n{pinned}"

    info_note = {"role": "system", "content": note_body}
    return head + [info_note] + recent_slice