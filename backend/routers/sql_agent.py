"""Generic AI SQL Agent routes — connect any Azure SQL and ask NL questions."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from ai.config import get_settings
from ai.memory import clear_memory
from ai.sql_agent import (
    SqlConnectionConfig,
    create_session,
    delete_session,
    get_session,
    set_schema,
    test_connection,
)
from ai.sql_agent.errors import (
    FRIENDLY_CONNECT_ERROR,
    FRIENDLY_PROFILE_ERROR,
    FRIENDLY_QUERY_ERROR,
    FRIENDLY_SESSION_ERROR,
    sanitize_user_message,
)
from ai.odbc_compat import OdbcUnavailableError
from ai.sql_agent.profiler import (
    ProfileBuildError,
    build_database_profile,
    profile_schema_preview,
    set_profile,
)
from ai.sql_agent.validator import UnsafeSqlError
from backend.schemas import (
    SqlAgentChatRequest,
    SqlAgentChatResponse,
    SqlConnectRequest,
    SqlConnectResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sql-agent", tags=["sql-agent"])

ERROR_SUGGESTIONS = [
    "List the tables in this database",
    "Show columns for a main table",
    "What is this database about?",
]


@router.post("/connect", response_model=SqlConnectResponse)
def connect_database(payload: SqlConnectRequest) -> SqlConnectResponse:
    """
    Test Azure SQL credentials, build a Database Profile, and create a session.

    Passwords are stored in memory only and are never logged or returned.
    """
    config = SqlConnectionConfig(
        server=payload.server.strip(),
        database=payload.database.strip(),
        username=payload.username.strip(),
        password=payload.password,
        driver=payload.driver.strip() or "ODBC Driver 18 for SQL Server",
    )

    try:
        test_connection(config)
    except OdbcUnavailableError as exc:
        logger.error("ODBC unavailable on this host: %s", exc)
        raise HTTPException(
            status_code=503,
            detail={
                "message": str(exc),
                "suggestions": [
                    "Deploy on Azure App Service with ODBC Driver 18, or run the API locally",
                    "Confirm App Service has ODBC Driver 18 for SQL Server installed",
                ],
            },
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "SQL Agent connection failed for server=%s db=%s",
            config.server,
            config.database,
        )
        raise HTTPException(
            status_code=400,
            detail={
                "message": FRIENDLY_CONNECT_ERROR,
                "suggestions": ERROR_SUGGESTIONS,
            },
        ) from exc

    try:
        profile = build_database_profile(config)
    except ProfileBuildError as exc:
        logger.exception("Profile build failed after connect for db=%s", config.database)
        raise HTTPException(
            status_code=400,
            detail={
                "message": FRIENDLY_PROFILE_ERROR,
                "suggestions": ERROR_SUGGESTIONS,
            },
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected profile failure for db=%s", config.database)
        raise HTTPException(
            status_code=400,
            detail={
                "message": FRIENDLY_PROFILE_ERROR,
                "suggestions": ERROR_SUGGESTIONS,
            },
        ) from exc

    session_id = create_session(config)
    set_profile(session_id, profile)
    preview = profile_schema_preview(profile)
    set_schema(session_id, preview)

    return SqlConnectResponse(
        session_id=session_id,
        database=config.database,
        server=config.server,
        table_count=profile.table_count,
        schema_preview=preview,
    )


@router.get("/session/{session_id}")
def session_status(session_id: str) -> dict:
    """Return non-sensitive session status."""
    config = get_session(session_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    return {
        "session_id": session_id,
        "server": config.server,
        "database": config.database,
        "connected": True,
    }


@router.delete("/session/{session_id}")
def disconnect_session(session_id: str) -> dict[str, str]:
    """Drop in-memory credentials, schema, and profile for a session."""
    delete_session(session_id)
    clear_memory(session_id)
    return {"status": "disconnected"}


@router.post("/chat", response_model=SqlAgentChatResponse)
def sql_agent_chat(payload: SqlAgentChatRequest) -> SqlAgentChatResponse:
    """Planner → profile/metadata/analysis paths. Never returns raw SQL Server errors."""
    settings = get_settings()
    question = payload.question.strip()
    if not question:
        raise HTTPException(
            status_code=400,
            detail={"message": "Question cannot be empty.", "suggestions": ERROR_SUGGESTIONS},
        )

    if get_session(payload.session_id) is None:
        raise HTTPException(
            status_code=400,
            detail={
                "message": FRIENDLY_SESSION_ERROR,
                "suggestions": ["Open Data Sources and connect Azure SQL"],
            },
        )

    try:
        history_payload = [
            {
                "role": m.role if hasattr(m, "role") else m.get("role"),
                "content": m.content if hasattr(m, "content") else m.get("content"),
            }
            for m in (payload.history or [])
        ]
        from ai.orchestrator import run_orchestrator

        orch = run_orchestrator(
            question,
            session_id=payload.session_id,
            history=history_payload,
        )
        result = {
            "answer": orch.answer,
            "sql": orch.sql if orch.sql_executed else None,
            "sql_executed": bool(orch.sql_executed and orch.sql),
            "visualization": orch.visualization,
            "tool": orch.tool,
            "tool_label": orch.tool_label,
            "data_source": orch.data_source,
            "execution_time": orch.execution_time,
            "row_count": orch.row_count,
            "follow_ups": orch.follow_ups,
            "category": orch.category,
            "router_decision": orch.router_decision,
            "validation_result": orch.validation_result,
            "agents_used": orch.agents_used,
            "planner_rationale": orch.planner_rationale,
            "execution_graph": orch.execution_graph,
        }
    except UnsafeSqlError as exc:
        logger.warning("Unsafe SQL rejected: %s", exc)
        raise HTTPException(
            status_code=400,
            detail={
                "message": "That request could not be run safely. Try a different question.",
                "suggestions": ERROR_SUGGESTIONS,
            },
        ) from exc
    except ValueError as exc:
        logger.warning("SQL Agent value error: %s", exc)
        raise HTTPException(
            status_code=400,
            detail={
                "message": sanitize_user_message(str(exc), fallback=FRIENDLY_QUERY_ERROR),
                "suggestions": ERROR_SUGGESTIONS,
            },
        ) from exc
    except ProfileBuildError as exc:
        logger.exception("Profile required but failed during chat")
        raise HTTPException(
            status_code=400,
            detail={"message": FRIENDLY_PROFILE_ERROR, "suggestions": ERROR_SUGGESTIONS},
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("SQL Agent chat failed")
        raise HTTPException(
            status_code=500,
            detail={
                "message": FRIENDLY_QUERY_ERROR,
                "suggestions": ERROR_SUGGESTIONS,
            },
        ) from exc

    answer = sanitize_user_message(
        result.get("answer"),
        fallback=FRIENDLY_QUERY_ERROR,
    )
    # Prefer the agent answer when it is already business-friendly and long.
    raw_answer = (result.get("answer") or "").strip()
    if raw_answer and not _should_replace_answer(raw_answer):
        answer = raw_answer

    return SqlAgentChatResponse(
        answer=answer,
        sql=result.get("sql") if result.get("sql_executed") else None,
        sql_executed=bool(result.get("sql_executed") and result.get("sql")),
        visualization=_parse_visualization(result.get("visualization")),
        tool=result.get("tool", "sql_agent"),
        tool_label=result.get("tool_label", "Generic SQL Agent"),
        data_source=result.get("data_source"),
        execution_time=result.get("execution_time", 0.0),
        model=settings.groq_model,
        row_count=result.get("row_count", 0),
        follow_ups=result.get("follow_ups", ERROR_SUGGESTIONS),
        category=result.get("category"),
        router_decision=result.get("router_decision") or result.get("category"),
        validation_result=_safe_dev_status(result.get("validation_result")),
        agents_used=list(result.get("agents_used") or []),
        planner_rationale=result.get("planner_rationale"),
        execution_graph=list(result.get("execution_graph") or []),
    )


def _parse_visualization(value):
    if not value or not isinstance(value, dict):
        return None
    try:
        from backend.schemas import VisualizationSpec

        return VisualizationSpec.model_validate(value)
    except Exception:  # noqa: BLE001
        return None


def _safe_dev_status(value: str | None) -> str | None:
    if value is None:
        return None
    from ai.sql_agent.errors import looks_like_raw_db_error

    text = str(value).strip()
    if looks_like_raw_db_error(text):
        return "failed (see server logs)"
    return text[:500] if len(text) > 500 else text


def _should_replace_answer(answer: str) -> bool:
    from ai.sql_agent.errors import looks_like_raw_db_error

    return looks_like_raw_db_error(answer)
