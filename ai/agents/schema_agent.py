"""Schema Agent — INFORMATION_SCHEMA profile & semantic roles (in-memory)."""

from __future__ import annotations

import logging
from typing import Any

from ai.agents.base import AgentResult, OrchestratorRequest
from ai.memory import ensure_memory
from ai.registry import register

logger = logging.getLogger(__name__)


@register("schema")
def run(goal: str, request: OrchestratorRequest, bag: dict[str, Any]) -> AgentResult:
    """Inspect schema, build semantic profile, store summary in session memory."""
    if not request.session_id:
        return AgentResult(
            agent="schema",
            success=False,
            summary="Connect Azure SQL to inspect schema.",
            error="no_session",
        )

    try:
        from ai.sql_agent.profiler import ensure_profile
        from ai.sql_agent.schema_knowledge import (
            build_schema_knowledge,
            format_full_object_catalog,
            knowledge_model_to_text,
        )
        from ai.sql_agent.session_store import get_session, inspect_schema

        config = get_session(request.session_id)
        if config is None:
            return AgentResult(
                agent="schema",
                success=False,
                summary="Session expired. Reconnect Azure SQL.",
                error="expired",
            )

        schema_text = inspect_schema(config)
        profile = ensure_profile(request.session_id, config)
        model = build_schema_knowledge(profile)
        catalog = format_full_object_catalog(model)
        semantic = knowledge_model_to_text(model)

        roles = {
            "facts": [o.name for o in model.objects if "Fact" in o.business_role],
            "dimensions": [o.name for o in model.objects if "Dimension" in o.business_role],
            "views": [o.name for o in model.objects if o.object_type == "VIEW"],
            "lookups": [o.name for o in model.objects if "Lookup" in o.business_role],
        }

        mem = ensure_memory(request.session_id, database=config.database)
        mem.schema_summary = catalog[:6_000]
        mem.extra["schema_roles"] = roles

        q = (bag.get("resolved_question") or request.question).lower()
        summary = catalog if "every" in q or "all table" in q else semantic
        return AgentResult(
            agent="schema",
            success=True,
            summary=summary,
            data={
                "roles": roles,
                "catalog": catalog,
                "semantic": semantic,
                "raw_schema": schema_text,
            },
            meta={
                "goal": goal,
                "database": config.database,
                "table_count": model.object_count,
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Schema agent failed")
        return AgentResult(
            agent="schema",
            success=False,
            summary="Could not inspect schema.",
            error=str(exc),
        )
