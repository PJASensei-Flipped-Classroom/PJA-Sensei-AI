import re
from pathlib import PurePosixPath
from typing import List, Optional

from pydantic import BaseModel

from app.application.giveaway_patterns import is_giveaway_request
from app.domain.sensei import CodeContext, SenseiConfig

# OLD: GIVEAWAY_PATTERNS = [re.compile(...), ...] local to this module
# Removed because: duplicated security/pipeline patterns; use shared is_giveaway_request().


def _basename(path: Optional[str]) -> str:
    if not path:
        return ""
    return PurePosixPath(path.replace("\\", "/")).name.lower()


def _collect_file_names(code_context: Optional[CodeContext]) -> List[str]:
    names: List[str] = []
    if not code_context:
        return names
    primary = _basename(code_context.current_file_name)
    if primary:
        names.append(primary)
    for path in code_context.open_files or []:
        name = _basename(path)
        if name and name not in names:
            names.append(name)
    return names


# OLD: each gate returned PedagogyGateResult(...) with duplicated PL/EN answer/feedback/next_step.
# Removed because: _reject() builds the same payload once and cuts ~15 lines × 5 gates.
def _reject(
    lang: str,
    reason_code: str,
    answer_pl: str,
    answer_en: str,
    feedback_pl: str,
    feedback_en: str,
    next_pl: str,
    next_en: str,
    penalty: bool = False,
) -> "PedagogyGateResult":
    return PedagogyGateResult(
        rejected=True,
        reason_code=reason_code,
        answer=answer_pl if lang == "pl" else answer_en,
        prompt_feedback=feedback_pl if lang == "pl" else feedback_en,
        suggested_next_step=next_pl if lang == "pl" else next_en,
        penalty_applied=penalty,
    )


class PedagogyGateResult(BaseModel):
    rejected: bool
    reason_code: Optional[str] = None
    answer: Optional[str] = None
    prompt_feedback: Optional[str] = None
    suggested_next_step: Optional[str] = None
    penalty_applied: bool = False


class PedagogyGates:
    @staticmethod
    def evaluate(
        config: SenseiConfig,
        question: str,
        code_context: Optional[CodeContext],
    ) -> PedagogyGateResult:
        lang = config.language
        current_code = (code_context.current_code if code_context else None) or ""
        ide = config.ide_restrictions
        file_names = _collect_file_names(code_context)

        allowed = [a.lower() for a in (ide.allowed_files or []) if a]
        blocked = [b.lower() for b in (ide.blocked_files or []) if b]

        if blocked and file_names:
            hit = [n for n in file_names if n in blocked]
            if hit:
                hit_str = ", ".join(hit)
                return _reject(
                    lang,
                    "blocked_file",
                    f"Plik `{hit_str}` jest zablokowany w konfiguracji laboratorium. Otwórz dozwolony plik zadania.",
                    f"File `{hit_str}` is blocked for this lab. Open an allowed assignment file.",
                    f"Odrzucono: zablokowany plik ({hit_str}).",
                    f"Rejected: blocked file ({hit_str}).",
                    "Przełącz się na plik z listy dozwolonych i wyślij pytanie ponownie.",
                    "Switch to an allowed file and resend your question.",
                )

        if allowed:
            if not file_names:
                return _reject(
                    lang,
                    "file_not_allowed",
                    "Do tej sesji wymagany jest plik z listy dozwolonych. Ustaw `currentFileName` / `openFiles` w kontekście IDE.",
                    "This session requires a file from the allow-list. Set `currentFileName` / `openFiles` in the IDE context.",
                    "Odrzucono: brak nazwy pliku przy aktywnej liście allowedFiles.",
                    "Rejected: missing file name while allowedFiles is configured.",
                    f"Otwórz jeden z plików: {', '.join(allowed)}.",
                    f"Open one of: {', '.join(allowed)}.",
                )
            if not any(n in allowed for n in file_names):
                names_str = ", ".join(file_names)
                return _reject(
                    lang,
                    "file_not_allowed",
                    f"Plik `{names_str}` nie jest na liście dozwolonych. Dozwolone: {', '.join(allowed)}.",
                    f"File `{names_str}` is not allow-listed. Allowed: {', '.join(allowed)}.",
                    f"Odrzucono: plik poza allowedFiles ({names_str}).",
                    f"Rejected: file outside allowedFiles ({names_str}).",
                    f"Przełącz edytor na: {', '.join(allowed)}.",
                    f"Switch the editor to: {', '.join(allowed)}.",
                )

        if config.require_file_context and not current_code.strip():
            return _reject(
                lang,
                "empty_file_context",
                "To zadanie wymaga analizy Twojego kodu. Załącz niepusty plik w kontekście IDE (`currentCode`), abym mógł Ci pomóc.",
                "This lab requires code context. Please provide a non-empty file in `currentCode` so I can help you.",
                "Odrzucono: brak wymaganego kontekstu pliku (requireFileContext).",
                "Rejected: missing required file context (requireFileContext).",
                "Otwórz plik z zadaniem w edytorze, napisz pierwszą próbę kodu i wyślij zapytanie ponownie.",
                "Open your lab file in the IDE, write an initial draft, and resend your question.",
            )

        if config.pinned_identifiers:
            if not current_code.strip():
                missing = list(config.pinned_identifiers)
            else:
                missing = [
                    ident
                    for ident in config.pinned_identifiers
                    if not re.search(rf"\b{re.escape(ident)}\b", current_code)
                ]
            if missing:
                missing_str = ", ".join(missing)
                return _reject(
                    lang,
                    "missing_pinned_identifiers",
                    f"W Twoim kodzie brakuje wymaganych identyfikatorów narzuconych przez instrukcję laboratorium: `{missing_str}`. Przywróć je przed dalszą analizą.",
                    f"Your code is missing required pinned identifiers: `{missing_str}`. Please restore them before continuing.",
                    f"Odrzucono: brak wymaganych identyfikatorów ({missing_str}).",
                    f"Rejected: missing pinned identifiers ({missing_str}).",
                    f"Upewnij się, że w kodzie zdefiniowano: {missing_str}.",
                    f"Make sure your code defines: {missing_str}.",
                )

        if is_giveaway_request(question or ""):
            return _reject(
                lang,
                "giveaway_request",
                "Jako mentor sokratyczny nie mogę napisać gotowego rozwiązania za Ciebie. Zastanówmy się wspólnie: od jakiego elementu (klasy lub funkcji) powinniśmy zacząć?",
                "As a Socratic mentor, I cannot write the full solution for you. Let's think together: which class or function should we start with?",
                "Odrzucono: prośba o gotowe rozwiązanie (naruszenie zasad dydaktycznych).",
                "Rejected: request for a complete solution (pedagogical policy violation).",
                "Opisz własnymi słowami, co próbujesz osiągnąć w pierwszym kroku lub wklej swój dotychczasowy kod.",
                "Describe in your own words what you want to achieve in the first step or paste your draft code.",
                penalty=True,
            )

        return PedagogyGateResult(rejected=False)
