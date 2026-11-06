from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator
from pydantic.alias_generators import to_camel

# Payload / resource caps (abuse mitigation).
MAX_REFERENCE_MATERIALS = 20
MAX_MATERIAL_CONTENT_CHARS = 100_000
MAX_CODE_CONTEXT_CHARS = 100_000
MAX_QUESTION_CHARS = 8_000
MAX_OPEN_FILES = 50
MAX_DIAGNOSTICS = 100


class DomainModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ReferenceMaterial(DomainModel):
    title: str = Field(max_length=500)
    link: str = Field(max_length=2000)
    content: Optional[str] = Field(default=None, max_length=MAX_MATERIAL_CONTENT_CHARS)


class Goal(DomainModel):
    id: str
    description: str


class LearningContext(DomainModel):
    goals: List[Goal] = Field(min_length=1)


class AgentPersona(DomainModel):
    name: str = "Sensei"
    tone: str = "helpful and socratic"


class AgentBehavior(DomainModel):
    mode: Literal["theory", "debug", "review"] = "theory"


class IdeRestrictions(DomainModel):
    allowed_files: Optional[List[str]] = None
    blocked_files: Optional[List[str]] = None
    require_file_context: bool = False
    pinned_identifiers: List[str] = []


class Checkpoint(DomainModel):
    id: str
    after_goal: str
    hint: Optional[str] = None


HintLevel = Literal["nudge", "concept", "almost"]


class HintStep(DomainModel):
    level: HintLevel = "nudge"
    text: str


class PreLabQuestion(DomainModel):
    id: str
    question: str
    expected_keywords: List[str] = []


class PreLabConfig(DomainModel):
    enabled: bool = False
    max_attempts: int = 3
    hint_after_fail: Optional[str] = None
    questions: List[PreLabQuestion] = []

    @model_validator(mode="after")
    def require_keywords_when_enabled(self) -> "PreLabConfig":
        if not self.enabled:
            return self
        if not self.questions:
            raise ValueError("preLab.enabled requires at least one question")
        for q in self.questions:
            keywords = [k.strip() for k in (q.expected_keywords or []) if str(k).strip()]
            if not keywords:
                raise ValueError(
                    f"preLab question '{q.id}' must have non-empty expectedKeywords when preLab is enabled"
                )
            q.expected_keywords = keywords
        return self


class SenseiConfig(DomainModel):
    language: Literal["pl", "en"] = "pl"
    evaluation_criteria: str
    max_tokens_per_session: Optional[int] = 80_000
    reference_materials: List[ReferenceMaterial] = Field(
        default_factory=list, max_length=MAX_REFERENCE_MATERIALS
    )
    learning_context: LearningContext
    agent_persona: AgentPersona
    agent_behavior: AgentBehavior
    ide_restrictions: IdeRestrictions = Field(default_factory=IdeRestrictions)
    checkpoints: List[Checkpoint] = []
    pre_lab: PreLabConfig = Field(default_factory=PreLabConfig)
    # OLD: require_file_context: bool = False
    # OLD: pinned_identifiers: List[str] = []
    # Removed because: duplicated IdeRestrictions fields and drifted; canonical store is
    # ide_restrictions (legacy top-level keys still accepted via migrate_legacy_top_level_gates).
    hints: List[str] = []
    hint_ladder: List[HintStep] = Field(default_factory=list)
    max_hints: int = 3
    frustration_threshold: int = 2
    focus_mode_seconds: int = 180
    auto_debug_on_errors: bool = True
    solution_pack: List[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_top_level_gates(cls, data: Any) -> Any:
        """Accept legacy top-level requireFileContext / pinnedIdentifiers into ideRestrictions."""
        if not isinstance(data, dict):
            return data
        data = dict(data)

        top_rfc = data.pop("requireFileContext", None)
        if top_rfc is None:
            top_rfc = data.pop("require_file_context", None)
        top_pins = data.pop("pinnedIdentifiers", None)
        if top_pins is None:
            top_pins = data.pop("pinned_identifiers", None)

        if top_rfc is None and top_pins is None:
            return data

        ide_key = (
            "ideRestrictions"
            if "ideRestrictions" in data
            else ("ide_restrictions" if "ide_restrictions" in data else "ideRestrictions")
        )
        ide_raw = data.get(ide_key)
        ide = dict(ide_raw) if isinstance(ide_raw, dict) else {}

        if top_rfc is not None:
            nested_rfc = ide.get("requireFileContext", ide.get("require_file_context", False))
            ide["requireFileContext"] = bool(nested_rfc) or bool(top_rfc)

        if top_pins is not None:
            nested_pins = ide.get("pinnedIdentifiers", ide.get("pinned_identifiers")) or []
            merged = list(dict.fromkeys([*list(nested_pins), *list(top_pins or [])]))
            ide["pinnedIdentifiers"] = merged

        data[ide_key] = ide
        return data

    @field_validator("max_tokens_per_session", mode="before")
    @classmethod
    def default_token_budget(cls, v: Any) -> int:
        if v is None:
            return 80_000
        return v

    @model_validator(mode="after")
    def validate_checkpoints(self) -> "SenseiConfig":
        goal_ids = {goal.id for goal in self.learning_context.goals}
        for cp in self.checkpoints:
            if cp.after_goal not in goal_ids:
                raise ValueError(
                    f"Checkpoint '{cp.id}' odnosi się do nieistniejącego celu '{cp.after_goal}'"
                )
        # OLD:
        # if self.ide_restrictions.require_file_context:
        #     self.require_file_context = True
        # if self.ide_restrictions.pinned_identifiers and not self.pinned_identifiers:
        #     self.pinned_identifiers = list(self.ide_restrictions.pinned_identifiers)
        # Removed because: one-way sync into duplicate top-level fields; migration + computed_field replace it.
        if self.hint_ladder and self.max_hints < 1:
            self.max_hints = len(self.hint_ladder)
        return self

    @computed_field
    @property
    def require_file_context(self) -> bool:
        return self.ide_restrictions.require_file_context

    @computed_field
    @property
    def pinned_identifiers(self) -> List[str]:
        return list(self.ide_restrictions.pinned_identifiers or [])

    def resolved_hint_texts(self) -> List[str]:
        if self.hint_ladder:
            return [h.text for h in self.hint_ladder]
        return list(self.hints)

    def resolved_hint_levels(self) -> List[str]:
        if self.hint_ladder:
            return [h.level for h in self.hint_ladder]
        return ["nudge"] * len(self.hints)


class CodeContext(DomainModel):
    current_file_name: Optional[str] = None
    current_code: Optional[str] = Field(default=None, max_length=MAX_CODE_CONTEXT_CHARS)
    error_logs: Optional[str] = Field(default=None, max_length=MAX_CODE_CONTEXT_CHARS)
    selection: Optional[str] = Field(default=None, max_length=MAX_CODE_CONTEXT_CHARS)
    diagnostics: List[str] = Field(default_factory=list, max_length=MAX_DIAGNOSTICS)
    open_files: List[str] = Field(default_factory=list, max_length=MAX_OPEN_FILES)
