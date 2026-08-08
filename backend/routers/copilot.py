"""Copilot REST routes — thin wrappers over the existing AI package."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException

from ai.config import get_settings
from ai.database import execute_query
from ai.orchestrator import run_orchestrator
from ai.tools import TOOL_DATA_SOURCES, TOOL_DESCRIPTIONS, TOOL_REGISTRY
from backend.schemas import (
    ChatRequest,
    ChatResponse,
    DatasetInfo,
    HealthResponse,
    HistoryMessage,
    ToolInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["copilot"])

TOOL_LABELS: dict[str, str] = {
    "knowledge": "Knowledge",
    "overall_summary": "Overall Summary",
    "monthly_yield": "Monthly Yield",
    "sensor_comparison": "Sensor Comparison",
    "best_month": "Best Month",
    "worst_month": "Worst Month",
    "recommendations": "Recommendations",
}

FOLLOW_UPS: dict[str, list[str]] = {
    "knowledge": [
        "Give overall production summary",
        "What is the SECOM dataset?",
        "How does the architecture work?",
    ],
    "overall_summary": [
        "Show monthly yield",
        "Which month had the lowest yield?",
        "Give recommendations",
    ],
    "monthly_yield": [
        "Which month performed best?",
        "Which month had the lowest yield?",
        "Explain what yield means",
    ],
    "sensor_comparison": [
        "Give recommendations",
        "What do sensors measure in semiconductor manufacturing?",
        "Give overall production summary",
    ],
    "best_month": [
        "Which month had the lowest yield?",
        "Show monthly yield",
        "Why does monthly yield matter?",
    ],
    "worst_month": [
        "Which month performed best?",
        "Give recommendations",
        "Explain more.",
    ],
    "recommendations": [
        "Compare Sensor 160 and Sensor 162",
        "Give overall production summary",
        "What is pass vs fail in SECOM?",
    ],
}

DEFAULT_FOLLOW_UPS = [
    "Give overall production summary",
    "What is the SECOM dataset?",
    "Give recommendations",
]

ERROR_SUGGESTIONS = [
    "Give overall production summary",
    "What is the SECOM dataset?",
    "Compare Sensor 160 and Sensor 162",
    "How does the project architecture work?",
]


def _build_contextual_question(question: str, history: list[HistoryMessage]) -> str:
    """Attach recent turns so short follow-ups like 'Why?' remain grounded."""
    if not history:
        return question

    recent = history[-6:]
    lines = [f"{item.role}: {item.content}" for item in recent]
    return (
        "You are continuing an analytics conversation.\n"
        "Use the prior turns only as context for the current question.\n\n"
        "Prior turns:\n"
        + "\n".join(lines)
        + f"\n\nCurrent user question: {question}"
    )


def _estimate_confidence(answer: str, tool: str | None) -> str:
    """Lightweight confidence badge for the UI."""
    if not tool or not answer.strip():
        return "Low"
    if len(answer) >= 220 and tool in TOOL_REGISTRY:
        return "High"
    if len(answer) >= 100:
        return "Medium"
    return "Low"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness probe for the API service."""
    return HealthResponse(status="healthy")


@router.get("/tools", response_model=list[str])
def list_tools() -> list[str]:
    """Return registered AI tool names from the existing tool registry."""
    return sorted(TOOL_REGISTRY.keys())


@router.get("/tools/details", response_model=list[ToolInfo])
def list_tool_details() -> list[ToolInfo]:
    """Return tool names with labels and descriptions for the product UI."""
    return [
        ToolInfo(
            name=name,
            label=TOOL_LABELS.get(name, name.replace("_", " ").title()),
            description=TOOL_DESCRIPTIONS.get(name, name),
        )
        for name in sorted(TOOL_REGISTRY.keys())
    ]


@router.get("/dataset", response_model=DatasetInfo)
def dataset_info() -> DatasetInfo:
    """Return SECOM / warehouse metadata for the workspace header."""
    settings = get_settings()
    row_count: int | None = None
    sensor_count: int | None = 590

    try:
        rows = execute_query("SELECT COUNT(*) FROM fact_sensor_readings;")
        if rows:
            row_count = int(rows[0][0])
    except Exception:  # noqa: BLE001
        logger.warning("Unable to read fact_sensor_readings row count", exc_info=True)

    return DatasetInfo(
        name="SECOM",
        row_count=row_count,
        sensor_count=sensor_count,
        database=settings.sql_database,
        table="fact_sensor_readings",
    )


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    """
    Route a user question through the existing AI copilot.

    Flow: question (+ history) → router → tool → adaptive answer.
    """
    question = payload.question.strip()
    if not question:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Question cannot be empty.",
                "suggestions": ERROR_SUGGESTIONS,
            },
        )

    history_payload = [
        {"role": m.role, "content": m.content} for m in (payload.history or [])
    ]
    settings = get_settings()
    started = time.perf_counter()

    try:
        orch = run_orchestrator(question, history=history_payload)
    except ValueError as exc:
        logger.warning("Copilot configuration/value error: %s", type(exc).__name__)
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Unable to process that request. Check configuration and try again.",
                "suggestions": ERROR_SUGGESTIONS,
            },
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Copilot chat failed")
        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "Unable to retrieve manufacturing insights. "
                    "Try one of the suggested questions below."
                ),
                "suggestions": ERROR_SUGGESTIONS,
            },
        ) from exc

    elapsed = round(time.perf_counter() - started, 2)
    # Prefer orchestrator timing; fall back to router wall clock
    execution_time = orch.execution_time or elapsed
    tool = orch.agents_used[0] if orch.agents_used else orch.tool
    # Map first specialized agent / tool hint into familiar Mode-1 labels when possible
    tool_key = tool if tool in TOOL_LABELS else "multi_agent"
    answer = orch.answer
    data_source = orch.data_source or TOOL_DATA_SOURCES.get(tool_key)

    return ChatResponse(
        answer=answer,
        tool=tool_key if tool_key in TOOL_LABELS else orch.tool,
        tool_label=TOOL_LABELS.get(tool_key) or orch.tool_label,
        data_source=data_source,
        response_mode=None,
        execution_time=execution_time,
        model=settings.groq_model,
        confidence=_estimate_confidence(answer, tool_key if tool_key in TOOL_REGISTRY else "knowledge"),
        follow_ups=orch.follow_ups or DEFAULT_FOLLOW_UPS,
    )
