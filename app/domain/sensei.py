from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel
from typing import List, Optional, Literal, Any

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
    # OLD: title: str
    # OLD: link: str
    title: str = Field(max_length=500)
    link: str = Field(max_length=2000)
    # OLD: content: Optional[str] = None
    # Why: inline RAG material / titles / links could be arbitrarily large → memory DoS on ingest.
    # Wrong: no upper bound at the domain boundary.
    # Better: reject oversized fields at validation (max_length).
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
    """Ordered hint ladder step (preferred over flat `hints` when non-empty)."""
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
        # Why: empty expectedKeywords made any non-empty answer pass (prelab_service).
        # Wrong: enabled prelab with blank keywords = accidental open gate / misconfig.
        # Better: fail config validation at start so labs cannot ship broken prelab.
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
    # OLD: max_tokens_per_session: Optional[int] = None
    # Why: None meant “no budget check” → unbounded Ollama spend / easy DoS.
    # Wrong: chat_service only enforced budget when the field was set.
    # Better: default 80k tokens; null from clients is coerced to that default (Spring can still raise the cap).
    max_tokens_per_session: Optional[int] = 80_000
    # OLD: reference_materials: List[ReferenceMaterial] = []
    # Why: many materials × fetch/chunk blows memory and start latency.
    # Wrong: unlimited list length on session create.
    # Better: hard cap on material count at validation.
    reference_materials: List[ReferenceMaterial] = Field(default_factory=list, max_length=MAX_REFERENCE_MATERIALS)
    learning_context: LearningContext
    agent_persona: AgentPersona
    agent_behavior: AgentBehavior
    ide_restrictions: IdeRestrictions = Field(default_factory=IdeRestrictions)
    checkpoints: List[Checkpoint] = []
    pre_lab: PreLabConfig = Field(default_factory=PreLabConfig)
    require_file_context: bool = False
    pinned_identifiers: List[str] = []
    hints: List[str] = []
    # NEW: structured ladder; when non-empty, reveal/force use these instead of flat `hints`.
    hint_ladder: List[HintStep] = Field(default_factory=list)
    max_hints: int = 3
    frustration_threshold: int = 2
    # Soft window after IDE compile/test failure: fewer frustration penalties (not giveaway).
    focus_mode_seconds: int = 180
    # Auto-switch mentor prompt into debug when error_logs/diagnostics present.
    auto_debug_on_errors: bool = True
    # Optional reference solutions for professor-only similarity checks (never shown to students).
    solution_pack: List[str] = Field(default_factory=list, max_length=20)

    @field_validator("max_tokens_per_session", mode="before")
    @classmethod
    def default_token_budget(cls, v: Any) -> int:
        # Explicit null from clients must not mean unlimited.
        if v is None:
            return 80_000
        return v

    @model_validator(mode='after')
    def validate_checkpoints(self) -> 'SenseiConfig':
        goal_ids = {goal.id for goal in self.learning_context.goals}
        for cp in self.checkpoints:
            if cp.after_goal not in goal_ids:
                raise ValueError(f"Checkpoint '{cp.id}' odnosi się do nieistniejącego celu '{cp.after_goal}'")
        if self.ide_restrictions.require_file_context:
            self.require_file_context = True
        if self.ide_restrictions.pinned_identifiers and not self.pinned_identifiers:
            self.pinned_identifiers = list(self.ide_restrictions.pinned_identifiers)
        # OLD: max_hints only limited flat hints length implicitly
        if self.hint_ladder and self.max_hints < 1:
            self.max_hints = len(self.hint_ladder)
        return self

    def resolved_hint_texts(self) -> List[str]:
        """Prefer ladder texts; fall back to legacy flat hints."""
        if self.hint_ladder:
            return [h.text for h in self.hint_ladder]
        return list(self.hints)

    def resolved_hint_levels(self) -> List[str]:
        if self.hint_ladder:
            return [h.level for h in self.hint_ladder]
        return ["nudge"] * len(self.hints)

class CodeContext(DomainModel):
    current_file_name: Optional[str] = None
    # OLD: current_code: Optional[str] = None
    # OLD: error_logs: Optional[str] = None
    # OLD: selection: Optional[str] = None
    # OLD: diagnostics: List[str] = []
    # OLD: open_files: List[str] = []
    # Why: IDE can paste entire repos into codeContext → huge prompts + RAM.
    # Wrong: no size/cardinality limits on domain CodeContext.
    # Better: max_length on strings and list sizes so abuse fails at validation (422).
    current_code: Optional[str] = Field(default=None, max_length=MAX_CODE_CONTEXT_CHARS)
    error_logs: Optional[str] = Field(default=None, max_length=MAX_CODE_CONTEXT_CHARS)
    selection: Optional[str] = Field(default=None, max_length=MAX_CODE_CONTEXT_CHARS)
    diagnostics: List[str] = Field(default_factory=list, max_length=MAX_DIAGNOSTICS)
    open_files: List[str] = Field(default_factory=list, max_length=MAX_OPEN_FILES)
