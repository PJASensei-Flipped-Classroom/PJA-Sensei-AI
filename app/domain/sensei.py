from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel
from typing import List, Optional, Literal, Dict

class DomainModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class ReferenceMaterial(DomainModel):
    title: str
    link: str

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

class Checkpoint(DomainModel):
    id: str
    after_goal: str
    hint: Optional[str] = None

class PreLabQuestion(DomainModel):
    id: str
    question: str
    expected_keywords: List[str] = []

class PreLabConfig(DomainModel):
    enabled: bool = False
    max_attempts: int = 3
    hint_after_fail: Optional[str] = None
    questions: List[PreLabQuestion] = []

class SenseiConfig(DomainModel):
    language: Literal["pl", "en"] = "pl"
    evaluation_criteria: str
    max_tokens_per_session: Optional[int] = None
    reference_materials: List[ReferenceMaterial] = []
    learning_context: LearningContext
    agent_persona: AgentPersona
    agent_behavior: AgentBehavior
    ide_restrictions: IdeRestrictions = Field(default_factory=IdeRestrictions)
    checkpoints: List[Checkpoint] = []
    pre_lab: PreLabConfig = Field(default_factory=PreLabConfig)

    @model_validator(mode='after')
    def validate_checkpoints(self) -> 'SenseiConfig':
        goal_ids = {goal.id for goal in self.learning_context.goals}
        for cp in self.checkpoints:
            if cp.after_goal not in goal_ids:
                raise ValueError(f"Checkpoint '{cp.id}' odnosi się do nieistniejącego celu '{cp.after_goal}'")
        return self

class CodeContext(DomainModel):
    selection: Optional[str] = None
    diagnostics: List[str] = []
    open_files: List[str] = []

