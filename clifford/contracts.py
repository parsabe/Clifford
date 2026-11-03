from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def uid() -> str:
    return str(uuid4())


def now() -> datetime:
    return datetime.now(UTC)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Chat(StrictModel):
    text: str = Field(min_length=1, max_length=12000)
    session_id: str | None = None
    mode: Literal["fast", "balanced", "deep", "agentic"] = "balanced"


class Event(BaseModel):
    type: str
    id: str = Field(default_factory=uid)
    timestamp: datetime = Field(default_factory=now)
    session_id: str | None = None
    correlation_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class MemoryInput(StrictModel):
    content: str = Field(min_length=1, max_length=8000)
    category: Literal["working", "episodic", "semantic", "procedural"] = "semantic"
    scope: str = Field(default="personal", max_length=100)
    source: str = Field(default="user", max_length=200)
    expires_at: datetime | None = None
    confidence: float = Field(1, ge=0, le=1)


class ToolCall(StrictModel):
    tool: str
    arguments: dict[str, Any]


class Decision(StrictModel):
    approve: bool


class Step(StrictModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    tool: str
    arguments: dict[str, Any]
    depends_on: list[str] = Field(default_factory=list, max_length=12)


class PlanInput(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    steps: list[Step] = Field(min_length=1, max_length=12)


class PlanRequest(StrictModel):
    objective: str = Field(min_length=1, max_length=4000)
    agent: Literal["planning", "research", "coding", "knowledge", "productivity"] = "planning"


class SpeechInput(StrictModel):
    text: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    session_id: str
    events: list[Event]


class SessionResponse(BaseModel):
    id: str
    owner: str
    created_at: datetime


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    created_at: datetime


class SessionDetail(BaseModel):
    id: str
    messages: list[MessageResponse]


class MemoryResponse(MemoryInput):
    id: str
    owner: str
    created_at: datetime
    updated_at: datetime
    relevance: float | None = None


class TaskResponse(BaseModel):
    id: str
    owner: str
    title: str
    status: str
    steps: list[dict[str, Any]]
    created_at: datetime


class ApprovalResponse(BaseModel):
    id: str
    owner: str
    tool: str
    arguments: dict[str, Any]
    task_id: str | None
    step_id: str | None
    status: str
    created_at: datetime


class ToolResponse(BaseModel):
    status: str
    approval_id: str | None = None
    execution_id: str | None = None
    result: dict[str, Any] | None = None
