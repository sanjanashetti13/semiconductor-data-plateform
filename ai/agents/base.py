"""Shared agent contracts for the multi-agent orchestration layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    """Structured output from one specialized agent."""

    agent: str
    success: bool
    summary: str
    data: Any = None
    sql: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class AgentTask:
    """One step in a planner execution plan."""

    agent: str
    goal: str
    tool_hint: str | None = None


@dataclass
class ExecutionPlan:
    """Planner output — ordered agent invocations (no SQL execution)."""

    tasks: list[AgentTask]
    rationale: str
    response_style: str = "standard"  # direct | standard | detailed


@dataclass
class OrchestratorRequest:
    """Inbound request for the multi-agent orchestrator."""

    question: str
    session_id: str | None = None
    history: list[dict[str, str]] = field(default_factory=list)
    power_bi_url: str | None = None


@dataclass
class OrchestratorResponse:
    """Final merged answer plus developer-mode telemetry."""

    answer: str
    sql: str | None = None
    follow_ups: list[str] = field(default_factory=list)
    category: str | None = None
    row_count: int = 0
    data_source: str | None = None
    tool: str = "multi_agent"
    tool_label: str = "Multi-Agent Orchestrator"
    validation_result: str | None = None
    router_decision: str | None = None
    agents_used: list[str] = field(default_factory=list)
    planner_rationale: str | None = None
    execution_graph: list[str] = field(default_factory=list)
    execution_time: float = 0.0
    intermediate: list[AgentResult] = field(default_factory=list)
