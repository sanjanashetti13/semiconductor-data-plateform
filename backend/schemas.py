"""Pydantic request/response schemas for the Copilot API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HistoryMessage(BaseModel):
    """A prior turn used for conversational follow-ups."""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Natural-language question for the manufacturing copilot."""

    question: str = Field(..., min_length=1, description="User manufacturing question")
    history: list[HistoryMessage] = Field(
        default_factory=list,
        description="Recent conversation turns for follow-up context",
    )


class ChatResponse(BaseModel):
    """Enriched LLM answer for the enterprise chat UI."""

    answer: str
    tool: str | None = Field(default=None, description="Tool selected by the AI router")
    tool_label: str | None = Field(default=None, description="Human-friendly tool name")
    data_source: str | None = Field(default=None, description="Evidence source used")
    response_mode: str | None = Field(
        default=None,
        description="Adaptive answer sizing: quick | standard | detailed",
    )
    execution_time: float = Field(..., description="Wall-clock seconds for the request")
    model: str = Field(..., description="LLM model used for explanation")
    confidence: Literal["High", "Medium", "Low"] = "High"
    follow_ups: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Service health probe."""

    status: str = "healthy"


class ToolInfo(BaseModel):
    """Registered analytics tool metadata for the UI."""

    name: str
    label: str
    description: str


class DatasetInfo(BaseModel):
    """Lightweight dataset metadata for the workspace header."""

    name: str
    row_count: int | None = None
    sensor_count: int | None = None
    database: str
    table: str = "fact_sensor_readings"


class ErrorDetail(BaseModel):
    """Structured error payload with recovery suggestions."""

    message: str
    suggestions: list[str] = Field(default_factory=list)


class SqlConnectRequest(BaseModel):
    """User-provided Azure SQL connection for the generic SQL Agent."""

    server: str = Field(..., min_length=1)
    database: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    driver: str = "ODBC Driver 18 for SQL Server"


class SqlConnectResponse(BaseModel):
    """Opaque session established after a successful connection + schema inspect."""

    session_id: str
    database: str
    server: str
    table_count: int
    schema_preview: str


class SqlAgentChatRequest(BaseModel):
    """Natural-language question for the generic SQL Agent."""

    question: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    history: list[HistoryMessage] = Field(default_factory=list)


class SqlAgentChatResponse(BaseModel):
    """SQL Agent answer with optional developer metadata."""

    answer: str
    sql: str | None = None
    tool: str = "sql_agent"
    tool_label: str = "Generic SQL Agent"
    data_source: str | None = None
    execution_time: float
    model: str
    row_count: int = 0
    follow_ups: list[str] = Field(default_factory=list)
    category: str | None = None
    router_decision: str | None = None
    validation_result: str | None = None
    agents_used: list[str] = Field(default_factory=list)
    planner_rationale: str | None = None
    execution_graph: list[str] = Field(default_factory=list)
