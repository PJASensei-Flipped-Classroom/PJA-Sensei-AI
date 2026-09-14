"""Sensei lab configuration and nested domain models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class DomainModel(BaseModel):
    """Bazowy model domenowy obsługujący idiomatyczny snake_case oraz camelCase z JSON."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        frozen=True,
    )


class ReferenceMaterial(DomainModel):
    """Materiał referencyjny (doc/pdf/wideo) do RAG lub samego cytowania."""

    type: Literal["doc", "pdf", "video_timestamp", "slide"] = "doc"
    title: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    timestamp: str | None = None
    page: int | None = Field(default=None, ge=1)


class LearningContext(DomainModel):
    """Cele dydaktyczne i lista materiałów powiązanych z zadaniem."""

    goals: list[str] = Field(default_factory=list)
    reference_materials: list[ReferenceMaterial] = Field(default_factory=list)


class AgentPersona(DomainModel):
    """Persona mentora: rola i ton odpowiedzi."""

    role: str = Field(..., min_length=1)
    tone: str = Field(..., min_length=1)


class AgentBehavior(DomainModel):
    """Zachowanie agenta: tryb (theory/debug/review), model i reguły anty-kodowe."""

    persona: AgentPersona
    code_reveal_fallback: str | None = None
    strict_rules: list[str] = Field(default_factory=list)
    model: str | None = None
    mode: Literal["theory", "debug", "review"] = "debug"


class IdeRestrictions(DomainModel):
    """Ograniczenia IDE: wymóg pliku w czacie, blokada kopiowania z czatu."""

    require_file_context_for_chat: bool = False
    disable_copy_from_chat: bool = False


class Checkpoint(DomainModel):
    """Punkt kontrolny odblokowywany po osiągnięciu wskazanego celu."""

    id: str = Field(..., min_length=1)
    after_goal: str | None = None
    hint: str | None = None


class PreLabQuestion(DomainModel):
    """Pytanie quizu wstępnego z oczekiwanymi słowami kluczowymi."""

    id: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    expected_keywords: list[str] = Field(default_factory=list)


class PreLabConfig(DomainModel):
    """Konfiguracja bramki pre-lab (włącz/wyłącz, limity prób, hint po porażce)."""

    enabled: bool = False
    questions: list[PreLabQuestion] = Field(default_factory=list)
    max_attempts: int | None = Field(default=None, ge=1)
    hint_after_fail: str | None = None


class SenseiConfig(DomainModel):
    """Główna konfiguracja sesji Sensei (camelCase aliasy dla klienta IDE)."""

    learning_context: LearningContext
    agent_behavior: AgentBehavior
    ide_restrictions: IdeRestrictions | None = None
    language: Literal["pl", "en"] = "pl"
    pre_lab: PreLabConfig | None = None
    evaluation_criteria: list[str] = Field(default_factory=list)
    max_tokens_per_session: int | None = Field(default=None, ge=1)
    checkpoints: list[Checkpoint] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_checkpoint_references(self) -> SenseiConfig:
        """Upewnia się, że punkty kontrolne odwołują się do istniejących celów dydaktycznych."""
        valid_goals = set(self.learning_context.goals)
        for cp in self.checkpoints:
            if cp.after_goal and cp.after_goal not in valid_goals:
                raise ValueError(
                    f"Checkpoint '{cp.id}' odwołuje się do nieznanego celu dydaktycznego: '{cp.after_goal}'"
                )
        return self


class CodeSelection(DomainModel):
    """Zaznaczenie tekstu w edytorze (zakres linii + treść)."""

    start_line: int = Field(..., ge=1)
    end_line: int = Field(..., ge=1)
    text: str | None = None


class DiagnosticItem(DomainModel):
    """Diagnoza IDE (błąd/ostrzeżenie) dołączana do kontekstu kodu."""

    file: str | None = None
    severity: Literal["error", "warning", "info", "hint"] = "error"
    message: str = Field(..., min_length=1)
    line: int | None = Field(default=None, ge=1)
    source: str | None = None


class OpenFile(DomainModel):
    """Dodatkowy otwarty plik w workspace (ścieżka + treść)."""

    path: str = Field(..., min_length=1)
    content: str
    language: str | None = None


class CodeContext(DomainModel):
    """Stan edytora przesyłany z klientem przy pytaniu do Sensei."""

    current_file_name: str = Field(..., min_length=1)
    current_code: str
    error_logs: str | None = None
    workspace_root: str | None = None
    selection: CodeSelection | None = None
    diagnostics: list[DiagnosticItem] = Field(default_factory=list)
    open_files: list[OpenFile] = Field(default_factory=list)