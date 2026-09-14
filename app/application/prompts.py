"""System prompts and code-context formatting."""

from __future__ import annotations

from typing import Any

from app.application.pedagogy_gates import is_recall_intent
from app.domain.conversation import (
    FRUSTRATION_STREAK,
    Conversation,
    consecutive_low_scores,
)
from app.domain.sensei import CodeContext

_MODE_INSTRUCTIONS = {
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

_PROMPT_TEMPLATES = {
    "en": {
        "role_intro": "You are a programming mentor ({role}), tone: {tone}.",
        "rules_header": "Rules:",
        "refusal_rule": "Refuse full solution dumps; set penalty_applied=true if they demand complete code. Annotation names (e.g. @RestController) are OK.\nNever return complete methods/classes, multi-line fenced implementation blocks, or copy-pasteable patches — conceptual guidance only.",
        "score_header": "Score prompt_score (1–10) by:",
        "score_fallback": "- Clarity of the question\n- Use of code context\n- Progress on goals",
        "score_guidelines": "Vague stuck messages without a concrete error/code detail (\"doesn't work\", \"still broken\") → score ≤ 3. Polite small talk only → ~5.",
        "pedagogy": "Pedagogy: theory → explain directly; small talk → brief and kind; coding stuck → Socratic questions. Reuse exact identifiers the student named (snake_case/camelCase). If a system note lists pinned identifiers and the student asks for one, answer with that exact token. Do not end every reply with a question. Cite materials by title when useful.",
        "frustration": "Student is stuck: give one direct, simple technical hint; ease Socratic pressure.",
        "pin_recall": "CRITICAL recall: the student asks for a name they gave earlier. Your answer MUST contain this exact token verbatim: {joined}",
        "pin_normal": "Pinned identifiers from the student (use verbatim when relevant): {joined}",
        "materials_header": "Materials:",
        "footer": "Respond ONLY with JSON:\n{{\"answer\":\"...\",\"prompt_score\":1-10,\"prompt_feedback\":\"...\",\"penalty_applied\":false,\"suggested_next_step\":\"...\",\"goal_progress\":[{{\"goal\":\"...\",\"status\":\"not_started|in_progress|done\"}}]}}\nLanguage: English only.",
    },
    "pl": {
        "role_intro": "Jesteś mentorem programowania ({role}), ton: {tone}.",
        "rules_header": "Zasady:",
        "refusal_rule": "Odmawiaj gotowych rozwiązań; penalty_applied=true przy żądaniu pełnego kodu. Nazwy adnotacji (np. @RestController) są dozwolone.\nNigdy nie zwracaj kompletnych metod/klas, wieloliniowych bloków implementacji ani gotowych patchy — tylko wskazówki koncepcyjne.",
        "score_header": "Oceń prompt_score (1–10) według:",
        "score_fallback": "- Jasność pytania\n- Użycie kontekstu kodu\n- Postęp względem celów",
        "score_guidelines": "Niejasne „nie działa” / „dalej źle” bez konkretnego błędu lub fragmentu kodu → score ≤ 3. Same uprzejme small-talk → ~5.",
        "pedagogy": "Pedagogika: teoria → wyjaśnij wprost; luźna rozmowa → krótko i życzliwie; problem z kodem → pytania naprowadzające. Używaj dokładnie nazw podanych przez studenta (snake_case/camelCase). Jeśli notatka systemu wymienia zachowane identyfikatory i student o nie pyta, podaj dokładnie ten token. Nie kończ każdej odpowiedzi pytaniem. Cytuj materiały po tytule, gdy pomaga.",
        "frustration": "Student utknął: podaj jedną prostą, bezpośrednią wskazówkę; złagodź rygor sokratyczny.",
        "pin_recall": "KRYTYCZNE przypomnienie: student pyta o nazwę podaną wcześniej. Odpowiedź MUSI zawierać dokładnie ten token: {joined}",
        "pin_normal": "Zachowane identyfikatory studenta (używaj dosłownie, gdy pasują): {joined}",
        "materials_header": "Materiały:",
        "footer": "Odpowiedz WYŁĄCZNIE JSON-em:\n{{\"answer\":\"...\",\"prompt_score\":1-10,\"prompt_feedback\":\"...\",\"penalty_applied\":false,\"suggested_next_step\":\"...\",\"goal_progress\":[{{\"goal\":\"...\",\"status\":\"not_started|in_progress|done\"}}]}}\nJęzyk: wyłącznie polski.",
    },
}


def _mode_block(language: str, mode: str) -> str:
    lang = language if language in _MODE_INSTRUCTIONS else "pl"
    mapping = _MODE_INSTRUCTIONS[lang]
    return mapping.get(mode, mapping["debug"])


def format_code_context_block(ctx: CodeContext, language: str = "pl") -> str:
    """Formatuje stan edytora kodu i narzędzi diagnostycznych do czytelnego bloku tekstu."""
    en = language == "en"
    parts: list[str] = []
    current_file = ctx.current_file_name or ("unknown_file" if en else "nieznany_plik")

    if ctx.workspace_root:
        parts.append(f"{'Workspace root' if en else 'Katalog workspace'}: {ctx.workspace_root}")

    parts.append(f"{'File' if en else 'Plik'}: {current_file}")
    parts.append(f"{'Code' if en else 'Kod'}:\n```\n{ctx.current_code or ''}\n```")

    if ctx.selection and (ctx.selection.text or "").strip():
        label = (
            f"Selection lines {ctx.selection.start_line}-{ctx.selection.end_line}"
            if en
            else f"Zaznaczenie linie {ctx.selection.start_line}-{ctx.selection.end_line}"
        )
        parts.append(f"{label}:\n```\n{ctx.selection.text}\n```")

    if ctx.diagnostics:
        diag_lines = [
            f"- [{d.severity}] {d.file or current_file}:{d.line or '?'}: {d.message}"
            for d in ctx.diagnostics[:20]
        ]
        parts.append(f"{'Diagnostics' if en else 'Diagnostyki'}:\n" + "\n".join(diag_lines))

    if ctx.open_files:
        extras = [
            f"### {f.path}\n```\n{(f.content or '')[:1500]}\n```"
            for f in ctx.open_files[:5]
        ]
        parts.append(f"{'Other open files' if en else 'Inne otwarte pliki'}:\n" + "\n".join(extras))

    logs = ctx.error_logs.strip() if ctx.error_logs else ("None" if en else "Brak")
    parts.append(f"{'Error logs' if en else 'Logi błędów'}: {logs}")

    return "\n".join(parts)


def generation_params(mode: str) -> dict[str, Any]:
    """Zwraca zoptymalizowane hiperparametry generacji w zależności od trybu pracy."""
    match mode:
        case "theory":
            # Budget covers full JSON (answer + score + feedback + goals), not just prose.
            return {"temperature": 0.5, "max_tokens": 700}
        case "review":
            return {"temperature": 0.4, "max_tokens": 1000}
        case _:
            return {"temperature": 0.7, "max_tokens": 900}


def build_system_prompt(conversation: Conversation) -> str:
    """Dynamicznie składa prompt systemowy uwzględniając postępy i stan emocjonalny studenta."""
    config = conversation.config
    lang = config.language if config.language in _PROMPT_TEMPLATES else "pl"
    t = _PROMPT_TEMPLATES[lang]

    rules = "\n".join(f"- {rule}" for rule in config.agent_behavior.strict_rules)
    
    materials_list = []
    for m in config.learning_context.reference_materials:
        meta = []
        if m.timestamp:
            meta.append(f"@{m.timestamp}")
        if m.page:
            meta.append(f"p.{m.page}")
        meta_str = f" ({', '.join(meta)})" if meta else ""
        materials_list.append(f"- {m.title} ({m.url}){meta_str}")
    materials = "\n".join(materials_list)

    criteria_block = "\n".join(f"- {c}" for c in config.evaluation_criteria) if config.evaluation_criteria else t["score_fallback"]
    mode_block = _mode_block(lang, config.agent_behavior.mode or "debug")

    # Wykrywanie intencji przypomnienia w ostatniej wiadomości studenta
    last_user_msg = next(
        (str(m.get("content") or "") for m in reversed(conversation.messages) if m.get("role") == "user"),
        "",
    )
    recall_intent = is_recall_intent(last_user_msg, conversation.pinned_identifiers)

    # Detekcja frustracji
    frustrated = (
        consecutive_low_scores(conversation.prompt_scores) >= FRUSTRATION_STREAK
        and not recall_intent
    )
    frustration_note = t["frustration"] if frustrated else ""

    # Reguły zachowania identyfikatorów
    pin_rule = ""
    if conversation.pinned_identifiers:
        joined = ", ".join(conversation.pinned_identifiers)
        pin_template = t["pin_recall"] if recall_intent else t["pin_normal"]
        pin_rule = pin_template.format(joined=joined)

    role_intro = t["role_intro"].format(
        role=config.agent_behavior.persona.role,
        tone=config.agent_behavior.persona.tone,
    )

    return (
        f"{role_intro}\n"
        f"{mode_block}\n\n"
        f"{t['rules_header']}\n"
        f"{rules}\n"
        f"{t['refusal_rule']}\n\n"
        f"{t['score_header']}\n"
        f"{criteria_block}\n"
        f"{t['score_guidelines']}\n\n"
        f"{t['pedagogy']}\n"
        f"{frustration_note}\n"
        f"{pin_rule}\n\n"
        f"{t['materials_header']}\n"
        f"{materials}\n\n"
        f"{t['footer']}"
    )