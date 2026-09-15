"""Formatowanie promptów systemowych oraz kontekstu edytora kodu dla modelu LLM."""

from __future__ import annotations

from typing import Any

from app.application.pedagogy_gates import is_recall_intent
from app.domain.conversation import (
    FRUSTRATION_STREAK,
    Conversation,
    consecutive_low_scores,
)
from app.domain.sensei import CodeContext

_MODE_INSTRUCTIONS: dict[str, dict[str, str]] = {
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

_PROMPT_TEMPLATES: dict[str, dict[str, str]] = {
    "en": {
        "role_intro": "You are a programming mentor ({role}), tone: {tone}.",
        "rules_header": "Rules:",
        "refusal_rule": (
            "Refuse full solution dumps; set penalty_applied=true if they demand complete code. "
            "Annotation names (e.g. @RestController) are OK.\n"
            "Never return complete methods/classes, multi-line fenced implementation blocks, "
            "or copy-pasteable patches — conceptual guidance only."
        ),
        "score_header": "Score prompt_score (1–10) by:",
        "score_fallback": "- Clarity of the question\n- Use of code context\n- Progress on goals",
        "score_guidelines": (
            'Vague stuck messages without a concrete error/code detail ("doesn\'t work", "still broken") '
            "→ score ≤ 3. Polite small talk only → ~5. "
            "Clear theory question about the assignment → score 7–9. "
            "Student demonstrates finishing the lab goals (controller + JSON) → score 10 and mark all goals done."
        ),
        "pedagogy": (
            "Pedagogy: theory → explain directly; small talk → brief and kind; "
            "coding stuck → Socratic questions. Reuse exact identifiers the student named (snake_case/camelCase). "
            "If a system note lists pinned identifiers and the student asks for one, answer with that exact token. "
            "Do not end every reply with a question. Cite materials by title when useful.\n"
            "Always return goal_progress for EVERY configured learning goal. "
            "Promote status: not_started → in_progress → done only when the student shows real progress "
            "(e.g. mentions/uses @RestController; discusses returning JSON / ResponseEntity / @GetMapping). "
            "When ALL goals are done, set prompt_score=10 and congratulate briefly — that means the lab objective is met."
        ),
        "frustration": "Student is stuck: give one direct, simple technical hint; ease Socratic pressure.",
        "pin_recall": "CRITICAL recall: the student asks for a name they gave earlier. Your answer MUST contain this exact token verbatim: {joined}",
        "pin_normal": "Pinned identifiers from the student (use verbatim when relevant): {joined}",
        "materials_header": "Materials:",
        "footer": (
            "Respond ONLY with JSON:\n"
            '{{"answer":"...","prompt_score":1-10,"prompt_feedback":"...","penalty_applied":false,'
            '"suggested_next_step":"...","goal_progress":[{{"goal":"...","status":"not_started|in_progress|done"}}]}}\n'
            "Language: English only (Latin alphabet). Never mix Polish, Russian, or Cyrillic into answer/prompt_feedback."
        ),
    },
    "pl": {
        "role_intro": "Jesteś mentorem programowania ({role}), ton: {tone}.",
        "rules_header": "Zasady:",
        "refusal_rule": (
            "Odmawiaj gotowych rozwiązań; penalty_applied=true przy żądaniu pełnego kodu. "
            "Nazwy adnotacji (np. @RestController) są dozwolone.\n"
            "Nigdy nie zwracaj kompletnych metod/klas, wieloliniowych bloków implementacji "
            "ani gotowych patchy — tylko wskazówki koncepcyjne."
        ),
        "score_header": "Oceń prompt_score (1–10) według:",
        "score_fallback": "- Jasność pytania\n- Użycie kontekstu kodu\n- Postęp względem celów",
        "score_guidelines": (
            "Niejasne „nie działa” / „dalej źle” bez konkretnego błędu lub fragmentu kodu "
            "→ score ≤ 3. Same uprzejme small-talk → ~5. "
            "Jasne pytanie teoretyczne o zadanie → score 7–9. "
            "Student wykazuje domknięcie celów labu (kontroler + JSON) → score 10 i wszystkie cele status=done."
        ),
        "pedagogy": (
            "Pedagogika: teoria → wyjaśnij wprost; luźna rozmowa → krótko i życzliwie; "
            "problem z kodem → pytania naprowadzające. Używaj dokładnie nazw podanych przez studenta (snake_case/camelCase). "
            "Jeśli notatka systemu wymienia zachowane identyfikatory i student o nie pyta, podaj dokładnie ten token. "
            "Nie kończ każdej odpowiedzi pytaniem. Cytuj materiały po tytule, gdy pomaga.\n"
            "Język odpowiedzi: wyłącznie współczesny polski techniczny (alfabet łaciński). "
            "Zakazane: cyrylica, rosyjski, ukraiński oraz mieszanie języków w polu answer "
            "(np. „написании” zamiast „napisaniu”). Identyfikatory kodu zostaw po angielsku.\n"
            "ZAWSZE zwracaj goal_progress dla KAŻDEGO celu z konfiguracji. "
            "Podnoś status: not_started → in_progress → done tylko przy realnym postępie "
            "(np. student ma/opisuje @RestController; mówi o zwrocie JSON / ResponseEntity / @GetMapping). "
            "Gdy WSZYSTKIE cele są done, ustaw prompt_score=10 i krótko pogratuluj — to oznacza osiągnięcie celu labu (10/10)."
        ),
        "frustration": "Student utknął: podaj jedną prostą, bezpośrednią wskazówkę; złagodź rygor sokratyczny.",
        "pin_recall": "KRYTYCZNE przypomnienie: student pyta o nazwę podaną wcześniej. Odpowiedź MUSI zawierać dokładnie ten token: {joined}",
        "pin_normal": "Zachowane identyfikatory studenta (używaj dosłownie, gdy pasują): {joined}",
        "materials_header": "Materiały:",
        "footer": (
            "Odpowiedz WYŁĄCZNIE JSON-em:\n"
            '{{"answer":"...","prompt_score":1-10,"prompt_feedback":"...","penalty_applied":false,'
            '"suggested_next_step":"...","goal_progress":[{{"goal":"...","status":"not_started|in_progress|done"}}]}}\n'
            "Język: wyłącznie polski, alfabet łaciński. Żadnej cyrylicy ani wtrąceń rosyjskich w answer/prompt_feedback."
        ),
    },
}


def _get_mode_instruction(language: str, mode: str) -> str:
    """Zwraca instrukcję trybu dydaktycznego dopasowaną do języka sesji."""
    lang_key = language if language in _MODE_INSTRUCTIONS else "pl"
    mode_map = _MODE_INSTRUCTIONS[lang_key]
    return mode_map.get(mode, mode_map["debug"])


def _format_reference_materials(materials: list[Any]) -> str:
    """Formatuje listę materiałów źródłowych wraz ze znacznikami czasu i stronami."""
    formatted_lines: list[str] = []
    for mat in materials:
        metadata_tokens: list[str] = []
        if mat.timestamp:
            metadata_tokens.append(f"@{mat.timestamp}")
        if mat.page:
            metadata_tokens.append(f"p.{mat.page}")

        meta_suffix = f" ({', '.join(metadata_tokens)})" if metadata_tokens else ""
        formatted_lines.append(f"- {mat.title} ({mat.url}){meta_suffix}")
    return "\n".join(formatted_lines)


def format_code_context_block(ctx: CodeContext, language: str = "pl") -> str:
    """Formatuje stan edytora kodu, diagnostyki i błędy terminala do czytelnego bloku tekstu."""
    is_en = language == "en"
    blocks: list[str] = []

    current_file = ctx.current_file_name or ("unknown_file" if is_en else "nieznany_plik")

    if ctx.workspace_root:
        blocks.append(f"{'Workspace root' if is_en else 'Katalog workspace'}: {ctx.workspace_root}")

    blocks.append(f"{'File' if is_en else 'Plik'}: {current_file}")
    blocks.append(f"{'Code' if is_en else 'Kod'}:\n```\n{ctx.current_code or ''}\n```")

    if ctx.selection and (ctx.selection.text or "").strip():
        label = (
            f"Selection lines {ctx.selection.start_line}-{ctx.selection.end_line}"
            if is_en
            else f"Zaznaczenie linie {ctx.selection.start_line}-{ctx.selection.end_line}"
        )
        blocks.append(f"{label}:\n```\n{ctx.selection.text}\n```")

    if ctx.diagnostics:
        diag_lines = [
            f"- [{d.severity}] {d.file or current_file}:{d.line or '?'}: {d.message}"
            for d in ctx.diagnostics[:20]
        ]
        blocks.append(f"{'Diagnostics' if is_en else 'Diagnostyki'}:\n" + "\n".join(diag_lines))

    if ctx.open_files:
        extra_files = [
            f"### {f.path}\n```\n{(f.content or '')[:1500]}\n```"
            for f in ctx.open_files[:5]
        ]
        blocks.append(f"{'Other open files' if is_en else 'Inne otwarte pliki'}:\n" + "\n".join(extra_files))

    error_logs = ctx.error_logs.strip() if ctx.error_logs else ("None" if is_en else "Brak")
    blocks.append(f"{'Error logs' if is_en else 'Logi błędów'}: {error_logs}")

    return "\n".join(blocks)


def generation_params(mode: str) -> dict[str, Any]:
    """Zwraca hiperparametry generacji LLM dopasowane do profilu poznawczego trybu."""
    match mode:
        case "theory":
            return {"temperature": 0.5, "max_tokens": 700}
        case "review":
            return {"temperature": 0.4, "max_tokens": 1000}
        case _:
            return {"temperature": 0.55, "max_tokens": 900}


def build_system_prompt(conversation: Conversation) -> str:
    """Dynamicznie składa prompt systemowy, uwzględniając stan zadania, postępy i frustrację."""
    config = conversation.config
    lang = config.language if config.language in _PROMPT_TEMPLATES else "pl"
    tmpl = _PROMPT_TEMPLATES[lang]

    # Persona i tryb
    role_intro = tmpl["role_intro"].format(
        role=config.agent_behavior.persona.role,
        tone=config.agent_behavior.persona.tone,
    )
    mode_text = _get_mode_instruction(lang, config.agent_behavior.mode or "debug")

    # Zasady i kryteria oceny
    rules_text = "\n".join(f"- {r}" for r in config.agent_behavior.strict_rules)
    criteria_text = (
        "\n".join(f"- {c}" for c in config.evaluation_criteria)
        if config.evaluation_criteria
        else tmpl["score_fallback"]
    )

    # Detekcja intencji studenta i stanu emocjonalnego
    last_user_text = next(
        (str(m.get("content") or "") for m in reversed(conversation.messages) if m.get("role") == "user"),
        "",
    )
    has_recall_intent = is_recall_intent(last_user_text, conversation.pinned_identifiers)

    is_frustrated = (
        consecutive_low_scores(conversation.prompt_scores) >= FRUSTRATION_STREAK
        and not has_recall_intent
    )

    # Budowanie sekcji opcjonalnych
    optional_sections: list[str] = [tmpl["pedagogy"]]
    if is_frustrated:
        optional_sections.append(tmpl["frustration"])

    if conversation.pinned_identifiers:
        joined_idents = ", ".join(conversation.pinned_identifiers)
        pin_template = tmpl["pin_recall"] if has_recall_intent else tmpl["pin_normal"]
        optional_sections.append(pin_template.format(joined=joined_idents))

    materials_text = _format_reference_materials(config.learning_context.reference_materials)

    prompt_parts = [
        f"{role_intro}\n{mode_text}",
        f"{tmpl['rules_header']}\n{rules_text}\n{tmpl['refusal_rule']}",
        f"{tmpl['score_header']}\n{criteria_text}\n{tmpl['score_guidelines']}",
        "\n".join(optional_sections),
        f"{tmpl['materials_header']}\n{materials_text}",
        tmpl["footer"],
    ]

    return "\n\n".join(part for part in prompt_parts if part.strip())