"""Sensei lab configuration and nested domain models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReferenceMaterial(BaseModel):
    type: Literal["doc", "pdf", "video_timestamp", "slide"] = "doc"
    title: str
    url: str
    timestamp: str | None = None
    page: int | None = None


class LearningContext(BaseModel):
    goals: list[str]
    referenceMaterials: list[ReferenceMaterial]


class AgentPersona(BaseModel):
    role: str
    tone: str


class AgentBehavior(BaseModel):
    persona: AgentPersona
    codeRevealFallback: str | None = None
    strictRules: list[str]
    model: str | None = None
    mode: Literal["theory", "debug", "review"] = "debug"


class IdeRestrictions(BaseModel):
    requireFileContextForChat: bool = False
    disableCopyFromChat: bool = False


class Checkpoint(BaseModel):
    id: str
    after_goal: str | None = None
    hint: str | None = None


class PreLabQuestion(BaseModel):
    id: str
    prompt: str
    expected_keywords: list[str] = Field(default_factory=list)


class PreLabConfig(BaseModel):
    enabled: bool = False
    questions: list[PreLabQuestion] = Field(default_factory=list)
    max_attempts: int | None = None
    hint_after_fail: str | None = None


class SenseiConfig(BaseModel):
    learningContext: LearningContext
    agentBehavior: AgentBehavior
    ideRestrictions: IdeRestrictions | None = None
    language: Literal["pl", "en"] = "pl"
    preLab: PreLabConfig | None = None
    evaluationCriteria: list[str] = Field(default_factory=list)
    maxTokensPerSession: int | None = None
    checkpoints: list[Checkpoint] = Field(default_factory=list)


class CodeSelection(BaseModel):
    start_line: int
    end_line: int
    text: str | None = None


class DiagnosticItem(BaseModel):
    file: str | None = None
    severity: Literal["error", "warning", "info", "hint"] = "error"
    message: str
    line: int | None = None
    source: str | None = None


class OpenFile(BaseModel):
    path: str
    content: str
    language: str | None = None


class CodeContext(BaseModel):
    current_file_name: str
    current_code: str
    error_logs: str | None = None
    workspace_root: str | None = None
    selection: CodeSelection | None = None
    diagnostics: list[DiagnosticItem] = Field(default_factory=list)
    open_files: list[OpenFile] = Field(default_factory=list)
