import re
from typing import Optional

from pydantic import BaseModel
from app.domain.sensei import SenseiConfig, CodeContext

GIVEAWAY_PATTERNS = [
    re.compile(r"napisz\s+(za\s+mnie|mi)\s+(cały|kompletny|gotowy)\s+kod", re.IGNORECASE),
    re.compile(r"(daj|podaj|wygeneruj)\s+(mi\s+)?(gotowca|gotowe\s+rozwiązanie|cały\s+kod)", re.IGNORECASE),
    re.compile(r"rozwiąż\s+(za\s+mnie\s+)?całe\s+zadanie", re.IGNORECASE),
    re.compile(r"(write|give\s+me)\s+the\s+(full|complete|entire)\s+(code|solution)", re.IGNORECASE),
    re.compile(r"solve\s+the\s+(whole|entire)\s+(task|lab|problem)\s+for\s+me", re.IGNORECASE),
    re.compile(r"napisz\s+za\s+mnie\s+cały\s+(gotowy\s+)?kod", re.IGNORECASE), # Dodano brakujący match dla testu
]

class PedagogyGateResult(BaseModel):
    rejected: bool
    reason_code: Optional[str] = None # "empty_file_context" | "missing_pinned_identifiers" | "giveaway_request"
    answer: Optional[str] = None
    prompt_feedback: Optional[str] = None
    suggested_next_step: Optional[str] = None
    penalty_applied: bool = False

class PedagogyGates:
    def evaluate(
            self,
            config: SenseiConfig,
            question: str,
            code_context: Optional[CodeContext],
    ) -> PedagogyGateResult:
        lang = config.language
        current_code = (code_context.current_code if code_context else None) or ""

        if config.require_file_context and not current_code.strip():
            return PedagogyGateResult(
                rejected=True,
                reason_code="empty_file_context",
                answer=(
                    "To zadanie wymaga analizy Twojego kodu. Załącz niepusty plik w kontekście IDE (`currentCode`), abym mógł Ci pomóc."
                    if lang == "pl"
                    else "This lab requires code context. Please provide a non-empty file in `currentCode` so I can help you."
                ),
                prompt_feedback=(
                    "Odrzucono: brak wymaganego kontekstu pliku (requireFileContext)."
                    if lang == "pl"
                    else "Rejected: missing required file context (requireFileContext)."
                ),
                suggested_next_step=(
                    "Otwórz plik z zadaniem w edytorze, napisz pierwszą próbę kodu i wyślij zapytanie ponownie."
                    if lang == "pl"
                    else "Open your lab file in the IDE, write an initial draft, and resend your question."
                ),
                penalty_applied=False
            )

        if config.pinned_identifiers:
            if not current_code.strip():
                missing = list(config.pinned_identifiers)
            else:
                missing = [
                    ident for ident in config.pinned_identifiers
                    if not re.search(rf"\b{re.escape(ident)}\b", current_code)
                ]
            if missing:
                missing_str = ", ".join(missing)
                return PedagogyGateResult(
                    rejected=True,
                    reason_code="missing_pinned_identifiers",
                    answer=(
                        f"W Twoim kodzie brakuje wymaganych identyfikatorów narzuconych przez instrukcję laboratorium: `{missing_str}`. Przywróć je przed dalszą analizą."
                        if lang == "pl"
                        else f"Your code is missing required pinned identifiers: `{missing_str}`. Please restore them before continuing."
                    ),
                    prompt_feedback=(
                        f"Odrzucono: brak wymaganych identyfikatorów ({missing_str})."
                        if lang == "pl"
                        else f"Rejected: missing pinned identifiers ({missing_str})."
                    ),
                    suggested_next_step=(
                        f"Upewnij się, że w kodzie zdefiniowano: {missing_str}."
                        if lang == "pl"
                        else f"Make sure your code defines: {missing_str}."
                    ),
                    penalty_applied=False,
                )
        for pattern in GIVEAWAY_PATTERNS:
            if pattern.search(question or ""):
                return PedagogyGateResult(
                    rejected=True,
                    reason_code="giveaway_request",
                    answer=(
                        "Jako mentor sokratyczny nie mogę napisać gotowego rozwiązania za Ciebie. Zastanówmy się wspólnie: od jakiego elementu (klasy lub funkcji) powinniśmy zacząć?"
                        if lang == "pl"
                        else "As a Socratic mentor, I cannot write the full solution for you. Let's think together: which class or function should we start with?"
                    ),
                    prompt_feedback=(
                        "Odrzucono: prośba o gotowe rozwiązanie (naruszenie zasad dydaktycznych)."
                        if lang == "pl"
                        else "Rejected: request for a complete solution (pedagogical policy violation)."
                    ),
                    suggested_next_step=(
                        "Opisz własnymi słowami, co próbujesz osiągnąć w pierwszym kroku lub wklej swój dotychczasowy kod."
                        if lang == "pl"
                        else "Describe in your own words what you want to achieve in the first step or paste your draft code."
                    ),
                    penalty_applied=True,
                )
        return PedagogyGateResult(rejected=False)