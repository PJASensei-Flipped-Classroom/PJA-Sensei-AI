from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


# --- DTO: Kontekst Kodu ---

class CodeContextDTO(BaseModel):
    # Kod programu i zaznaczenia (obsługa camelCase i snake_case)
    code_snippet: Optional[str] = Field(default=None, alias="codeSnippet")
    current_code: Optional[str] = Field(default=None, alias="currentCode")
    selection: Optional[str] = None
    selected_text: Optional[str] = Field(default=None, alias="selectedText")

    # Ścieżki i nazwy plików
    file_path: Optional[str] = Field(default=None, alias="filePath")
    current_file_name: Optional[str] = Field(default=None, alias="currentFileName")
    language: Optional[str] = None
    cursor_position: Optional[int] = Field(default=None, alias="cursorPosition")
    active_tab: Optional[str] = Field(default=None, alias="activeTab")
    open_files: Optional[List[str]] = Field(default=None, alias="openFiles")

    # Diagnostyka i błędy kompilacji
    error_logs: Optional[str] = Field(default=None, alias="errorLogs")
    diagnostics: Optional[List[str]] = None
    compiler_output: Optional[str] = Field(default=None, alias="compilerOutput")

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    def __getattr__(self, item: str) -> Any:
        return None

    @model_validator(mode="after")
    def sync_aliases(self) -> "CodeContextDTO":
        code = self.current_code or self.code_snippet
        self.current_code = code
        self.code_snippet = code

        fname = self.current_file_name or self.file_path
        self.current_file_name = fname
        self.file_path = fname

        sel = self.selection or self.selected_text
        self.selection = sel
        self.selected_text = sel

        return self


# --- DTO: Pre-Lab ---

class PrelabQuestionDTO(BaseModel):
    id: str
    question: str
    hint: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class PrelabStatusResponse(BaseModel):
    enabled: bool = False
    passed: bool = False
    completed: bool = False
    questions: List[PrelabQuestionDTO] = []
    attempts: int = 0
    max_attempts: Optional[int] = None
    remaining_attempts: Optional[int] = None
    hint_after_fail: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class PrelabSubmitResponse(BaseModel):
    passed: bool
    unlocked: bool = False
    failed_ids: List[str] = []
    score: Optional[float] = None
    feedback: Optional[str] = None
    attempts: int = 0
    remaining_attempts: Optional[int] = None
    prelab_completed: bool = False

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class PrelabAnswerItem(BaseModel):
    id: str = "q1"
    answer: str

    @field_validator("answer", mode="before")
    @classmethod
    def validate_answer_text(cls, v: Any) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Odpowiedź Pre-Lab nie może być pusta.")
        return v.strip()


class PrelabSubmitRequest(BaseModel):
    answers: List[PrelabAnswerItem]

    @model_validator(mode="before")
    @classmethod
    def normalize_answers(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            raise ValueError("Nieprawidłowy format żądania.")

        raw = data.get("answers") if "answers" in data else data.get("answer")
        if raw is None:
            raise ValueError("Brak pola 'answers' lub 'answer'.")

        if isinstance(raw, str):
            if not raw.strip():
                raise ValueError("Odpowiedź Pre-Lab nie może być pusta.")
            return {"answers": [{"id": "q1", "answer": raw.strip()}]}

        if isinstance(raw, list):
            if not raw:
                raise ValueError("Lista odpowiedzi Pre-Lab nie może być pusta.")
            normalized = []
            for idx, item in enumerate(raw, start=1):
                if isinstance(item, str):
                    if not item.strip():
                        raise ValueError("Odpowiedź Pre-Lab nie może być pusta.")
                    normalized.append({"id": f"q{idx}", "answer": item.strip()})
                elif isinstance(item, dict):
                    ans_text = str(item.get("answer", item.get("text", ""))).strip()
                    if not ans_text:
                        raise ValueError("Odpowiedź Pre-Lab nie może być pusta.")
                    normalized.append({"id": item.get("id", f"q{idx}"), "answer": ans_text})
                else:
                    normalized.append(item)
            return {"answers": normalized}

        return data


# --- DTO: Konfiguracja i Start Sesji ---

class ConfigValidationRequest(BaseModel):
    config: Dict[str, Any]


class ConversationStartRequest(BaseModel):
    config: Dict[str, Any]


# --- DTO: Czat i Wiadomości ---

class MessageRequest(BaseModel):
    question: str
    code_context: Optional[CodeContextDTO] = Field(default=None, alias="codeContext")
    client_message_id: Optional[str] = Field(default=None, alias="clientMessageId")

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    @field_validator("question", mode="before")
    @classmethod
    def validate_non_empty_question(cls, v: Any) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Wiadomość nie może być pusta.")
        return v.strip()


class GoalProgressEntryDTO(BaseModel):
    goal: str
    status: str


class NextCheckpointDTO(BaseModel):
    id: str
    hint: Optional[str] = None
    after_goal: Optional[str] = Field(default=None, alias="afterGoal")
    unlocked: bool = False
    status: Optional[str] = "locked"

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class MessageResponse(BaseModel):
    message_id: str
    answer: str
    prompt_score: int
    prompt_feedback: str
    tokens_used: int
    penalty_applied: bool
    sources: List[str] = []
    suggested_next_step: Optional[str] = None
    goal_progress: List[GoalProgressEntryDTO] = []
    lab_score: int = 0
    next_checkpoint: Optional[Union[NextCheckpointDTO, str]] = None
    model: str = "default"
    debug_info: Optional[Dict[str, Any]] = None


# --- DTO: Zdarzenia IDE, Wskazówki, Feedback, Podsumowanie ---

class EventRequest(BaseModel):
    type: str
    meta: Optional[Dict[str, Any]] = None


class HintRevealResponse(BaseModel):
    hint: str
    hints_used: int
    max_hints: int
    hints_remaining: int
    frustration_streak_reset: bool = True


class FeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    status: str
    message_id: str
    rating: int


class SessionSummaryResponse(BaseModel):
    conversation_id: str
    summary: str
    lab_score: int
    goal_progress: List[GoalProgressEntryDTO]
    tokens_used: int
    messages_count: int
    hints_used: int
    events_count: int
    completed: bool