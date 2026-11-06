from typing import Optional, List, Dict, Any
from pydantic import AliasChoices, BaseModel, Field, ConfigDict, field_validator, model_validator

from app.domain.sensei import (
    CodeContext,
    SenseiConfig,
    MAX_CODE_CONTEXT_CHARS,
    MAX_DIAGNOSTICS,
    MAX_OPEN_FILES,
    MAX_QUESTION_CHARS,
)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        serialize_by_alias=False,
    )


class CodeContextDTO(ApiModel):
    current_code: Optional[str] = Field(
        default=None, alias="currentCode", max_length=MAX_CODE_CONTEXT_CHARS
    )
    code_snippet: Optional[str] = Field(
        default=None, alias="codeSnippet", max_length=MAX_CODE_CONTEXT_CHARS
    )
    current_file_name: Optional[str] = Field(default=None, alias="currentFileName", max_length=500)
    file_path: Optional[str] = Field(default=None, alias="filePath", max_length=500)
    selection: Optional[str] = Field(default=None, max_length=MAX_CODE_CONTEXT_CHARS)
    selected_text: Optional[str] = Field(
        default=None, alias="selectedText", max_length=MAX_CODE_CONTEXT_CHARS
    )
    error_logs: Optional[str] = Field(
        default=None, alias="errorLogs", max_length=MAX_CODE_CONTEXT_CHARS
    )
    diagnostics: List[str] = Field(default_factory=list, max_length=MAX_DIAGNOSTICS)
    open_files: List[str] = Field(
        default_factory=list, alias="openFiles", max_length=MAX_OPEN_FILES
    )

    @model_validator(mode="after")
    def normalize(self) -> "CodeContextDTO":
        self.current_code = self.current_code or self.code_snippet
        self.current_file_name = self.current_file_name or self.file_path
        self.selection = self.selection or self.selected_text
        return self

    def to_domain(self) -> CodeContext:
        return CodeContext(
            current_code=self.current_code,
            current_file_name=self.current_file_name,
            selection=self.selection,
            error_logs=self.error_logs,
            diagnostics=list(self.diagnostics or []),
            open_files=list(self.open_files or []),
        )


class PrelabQuestionDTO(ApiModel):
    id: str
    question: str
    hint: Optional[str] = None


class PrelabStatusResponse(ApiModel):
    enabled: bool = False
    passed: bool = False
    # OLD: completed: bool = False
    # Removed because: always mirrored passed/prelab_completed; clients use passed.
    questions: List[PrelabQuestionDTO] = Field(default_factory=list)
    attempts: int = 0
    max_attempts: Optional[int] = None
    remaining_attempts: Optional[int] = None
    hint_after_fail: Optional[str] = None


class PrelabSubmitResponse(ApiModel):
    passed: bool
    unlocked: bool = False
    failed_ids: List[str] = Field(default_factory=list)
    feedback: Optional[str] = None
    attempts: int = 0
    remaining_attempts: Optional[int] = None
    prelab_completed: bool = False


class PrelabAnswerItem(ApiModel):
    id: str = "q1"
    answer: str = Field(max_length=MAX_QUESTION_CHARS)

    @field_validator("answer", mode="before")
    @classmethod
    def validate_answer_text(cls, v: Any) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Pre-Lab answer cannot be empty.")
        return v.strip()


class PrelabSubmitRequest(ApiModel):
    answers: List[PrelabAnswerItem]

    @model_validator(mode="before")
    @classmethod
    def normalize_answers(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            raise ValueError("Invalid request body.")
        if "answers" in data:
            return data
        raw = data.get("answer")
        if isinstance(raw, str) and raw.strip():
            return {"answers": [{"id": "q1", "answer": raw.strip()}]}
        raise ValueError("Missing 'answers' (or legacy 'answer').")


class ConfigValidationRequest(ApiModel):
    config: Dict[str, Any]


class ConversationStartRequest(ApiModel):
    config: SenseiConfig


class MessageRequest(ApiModel):
    question: str = Field(max_length=MAX_QUESTION_CHARS)
    code_context: Optional[CodeContextDTO] = Field(default=None, alias="codeContext")
    client_message_id: Optional[str] = Field(default=None, alias="clientMessageId", max_length=200)

    @field_validator("question", mode="before")
    @classmethod
    def validate_non_empty_question(cls, v: Any) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Message cannot be empty.")
        return v.strip()


class GoalProgressEntryDTO(ApiModel):
    goal: str
    status: str


class NextCheckpointDTO(ApiModel):
    id: str
    hint: Optional[str] = None
    # AliasChoices keeps Python ctor as after_goal (IDE-friendly) while accepting afterGoal from JSON.
    after_goal: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("after_goal", "afterGoal"),
    )
    unlocked: bool = False


class MessageResponse(ApiModel):
    message_id: str
    answer: str
    prompt_score: int
    prompt_feedback: str
    tokens_used: int
    penalty_applied: bool
    sources: List[str] = Field(default_factory=list)
    suggested_next_step: Optional[str] = None
    goal_progress: List[GoalProgressEntryDTO] = Field(default_factory=list)
    lab_score: int = 0
    next_checkpoint: Optional[NextCheckpointDTO] = None
    model: str = "default"
    debug_info: Optional[Dict[str, Any]] = None
    tutoring_mode: Optional[str] = None
    checkpoint_celebration: Optional[str] = None
    concept_card: Optional[Dict[str, Any]] = None
    in_focus_mode: bool = False


class EventRequest(ApiModel):
    type: str = Field(max_length=100)
    meta: Optional[Dict[str, Any]] = None


class HintRevealResponse(ApiModel):
    hint: str
    hints_used: int
    max_hints: int
    hints_remaining: int
    frustration_streak_reset: bool = True
    forced: bool = False
    hint_level: Optional[str] = None


class FeedbackRequest(ApiModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)


class FeedbackResponse(ApiModel):
    status: str
    message_id: str
    rating: int


class SessionSummaryResponse(ApiModel):
    conversation_id: str
    summary: str
    lab_score: int
    goal_progress: List[GoalProgressEntryDTO]
    tokens_used: int
    messages_count: int
    hints_used: int
    events_count: int
    completed: bool


class RagMaterialPreviewDTO(ApiModel):
    title: str
    link: str


class RagPreviewDTO(ApiModel):
    chunks_ingested: int = 0
    materials: List[RagMaterialPreviewDTO] = Field(default_factory=list)
