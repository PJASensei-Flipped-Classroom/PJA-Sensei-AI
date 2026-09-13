"""System prompts and code-context formatting."""

from __future__ import annotations

import re

from app.domain.conversation import (
    FRUSTRATION_STREAK,
    Conversation,
    consecutive_low_scores,
)
from app.domain.sensei import CodeContext

_MODE_DELTA = {
    "en": {
        "theory": "Mode theory: explain clearly, low Socratic pressure, skip IDE noise unless asked.",
        "debug": "Mode debug: focus on code, selection, diagnostics; guide with questions when stuck.",
        "review": "Mode review: conceptual findings and guiding questions only — no full patches.",
    },
    "pl": {
        "theory": "Tryb theory: jasne wyjaśnienia, mniejszy rygor sokratyczny, bez zbędnej diagnostyki IDE.",
        "debug": "Tryb debug: kod, zaznaczenie, diagnostyki; pytania naprowadzające przy problemach.",
        "review": "Tryb review: uwagi koncepcyjne i pytania — bez pełnego patcha ani gotowego rozwiązania.",
    },
}


def _mode_block(language: str, mode: str) -> str:
    lang = language if language in _MODE_DELTA else "pl"
    mapping = _MODE_DELTA[lang]
    return mapping.get(mode, mapping["debug"])


def format_code_context_block(ctx: CodeContext, language: str = "pl") -> str:
    en = language == "en"
    parts: list[str] = []
    if ctx.workspace_root:
        parts.append(
            f"{'Workspace root' if en else 'Katalog workspace'}: {ctx.workspace_root}"
        )
    parts.append(f"{'File' if en else 'Plik'}: {ctx.current_file_name}")
    parts.append(f"{'Code' if en else 'Kod'}:\n```\n{ctx.current_code}\n```")
    if ctx.selection:
        sel_text = ctx.selection.text or ""
        label = (
            f"Selection lines {ctx.selection.start_line}-{ctx.selection.end_line}"
            if en
            else f"Zaznaczenie linie {ctx.selection.start_line}-{ctx.selection.end_line}"
        )
        parts.append(f"{label}:\n```\n{sel_text}\n```")
    if ctx.diagnostics:
        diag_lines = []
        for d in ctx.diagnostics[:20]:
            loc = f"{d.file or ctx.current_file_name}:{d.line or '?'}"
            diag_lines.append(f"- [{d.severity}] {loc} {d.message}")
        parts.append(
            ("Diagnostics" if en else "Diagnostyki") + ":\n" + "\n".join(diag_lines)
        )
    if ctx.open_files:
        extras = [
            f"### {f.path}\n```\n{f.content[:1500]}\n```" for f in ctx.open_files[:5]
        ]
        parts.append(
            ("Other open files" if en else "Inne otwarte pliki")
            + ":\n"
            + "\n".join(extras)
        )
    logs = ctx.error_logs or ("None" if en else "Brak")
    parts.append(f"{'Error logs' if en else 'Logi błędów'}: {logs}")
    return "\n".join(parts)


def generation_params(mode: str) -> dict:
    if mode == "theory":
        return {"temperature": 0.5, "max_tokens": 280}
    if mode == "review":
        return {"temperature": 0.4, "max_tokens": 400}
    return {"temperature": 0.7, "max_tokens": 350}


def build_system_prompt(conversation: Conversation) -> str:
    config = conversation.config
    lang = config.language
    rules = "\n".join(f"- {rule}" for rule in config.agentBehavior.strictRules)
    materials = "\n".join(
        f"- {m.title} ({m.url})"
        + (f" @{m.timestamp}" if m.timestamp else "")
        + (f" p.{m.page}" if m.page else "")
        for m in config.learningContext.referenceMaterials
    )
    criteria = config.evaluationCriteria or []
    if criteria:
        criteria_block = "\n".join(f"- {c}" for c in criteria)
    elif lang == "en":
        criteria_block = (
            "- Clarity of the question\n- Use of code context\n- Progress on goals"
        )
    else:
        criteria_block = (
            "- Jasność pytania\n- Użycie kontekstu kodu\n- Postęp względem celów"
        )

    mode = config.agentBehavior.mode or "debug"
    mode_block = _mode_block(lang, mode)

    last_user = ""
    for m in reversed(conversation.messages):
        if m.get("role") == "user":
            last_user = str(m.get("content") or "")
            break
    recall_intent = bool(
        conversation.pinned_identifiers
        and re.search(
            r"(nazw[aeę]|zmienn|identifier|variable|wcze[sś]niej|poda[łl]em|remember|earlier)",
            last_user,
            re.IGNORECASE,
        )
    )

    frustrated = (
        consecutive_low_scores(conversation.prompt_scores) >= FRUSTRATION_STREAK
        and not recall_intent
    )
    if frustrated:
        frustration = (
            "Student is stuck: give one direct, simple technical hint; ease Socratic pressure."
            if lang == "en"
            else "Student utknął: podaj jedną prostą, bezpośrednią wskazówkę; złagodź rygor sokratyczny."
        )
    else:
        frustration = ""

    if conversation.pinned_identifiers:
        joined = ", ".join(conversation.pinned_identifiers)
        pin_rule = (
            f"Pinned identifiers from the student (use verbatim when relevant): {joined}"
            if lang == "en"
            else f"Zachowane identyfikatory studenta (używaj dosłownie, gdy pasują): {joined}"
        )
    else:
        pin_rule = ""

    if lang == "en":
        return f"""You are a programming mentor ({config.agentBehavior.persona.role}), tone: {config.agentBehavior.persona.tone}.
{mode_block}

Rules:
{rules}
Refuse full solution dumps; set penalty_applied=true if they demand complete code. Annotation names (e.g. @RestController) are OK.

Score prompt_score (1–10) by:
{criteria_block}
Vague stuck messages without a concrete error/code detail ("doesn't work", "still broken") → score ≤ 3. Polite small talk only → ~5.

Pedagogy: theory → explain directly; small talk → brief and kind; coding stuck → Socratic questions. Reuse exact identifiers the student named (snake_case/camelCase). If a system note lists pinned identifiers and the student asks for one, answer with that exact token. Do not end every reply with a question. Cite materials by title when useful.
{frustration}
{pin_rule}

Materials:
{materials}

Respond ONLY with JSON:
{{"answer":"...","prompt_score":1-10,"prompt_feedback":"...","penalty_applied":false,"suggested_next_step":"...","goal_progress":[{{"goal":"...","status":"not_started|in_progress|done"}}]}}
Language: English only.
"""

    return f"""Jesteś mentorem programowania ({config.agentBehavior.persona.role}), ton: {config.agentBehavior.persona.tone}.
{mode_block}

Zasady:
{rules}
Odmawiaj gotowych rozwiązań; penalty_applied=true przy żądaniu pełnego kodu. Nazwy adnotacji (np. @RestController) są dozwolone.

Oceń prompt_score (1–10) według:
{criteria_block}
Niejasne „nie działa” / „dalej źle” bez konkretnego błędu lub fragmentu kodu → score ≤ 3. Same uprzejme small-talk → ~5.

Pedagogika: teoria → wyjaśnij wprost; luźna rozmowa → krótko i życzliwie; problem z kodem → pytania naprowadzające. Używaj dokładnie nazw podanych przez studenta (snake_case/camelCase). Jeśli notatka systemu wymienia zachowane identyfikatory i student o nie pyta, podaj dokładnie ten token. Nie kończ każdej odpowiedzi pytaniem. Cytuj materiały po tytule, gdy pomaga.
{frustration}
{pin_rule}

Materiały:
{materials}

Odpowiedz WYŁĄCZNIE JSON-em:
{{"answer":"...","prompt_score":1-10,"prompt_feedback":"...","penalty_applied":false,"suggested_next_step":"...","goal_progress":[{{"goal":"...","status":"not_started|in_progress|done"}}]}}
Język: wyłącznie polski.
"""
