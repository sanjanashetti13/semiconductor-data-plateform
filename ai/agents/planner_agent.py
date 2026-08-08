"""Planner Agent — intent → ordered specialized-agent plan (never runs SQL)."""

from __future__ import annotations

import logging
import re

from ai.agents.base import AgentTask, ExecutionPlan, OrchestratorRequest
from ai.context import is_follow_up
from ai.memory import get_memory

logger = logging.getLogger(__name__)

_KNOWLEDGE = re.compile(
    r"\b(what is|what's|explain|define|meaning of|how does|tell me about|"
    r"wafer|secom|etl|databricks|architecture|medallion|bronze|silver|gold|"
    r"azure sql|power bi|semiconductor)\b",
    re.I,
)
_SCHEMA = re.compile(
    r"\b(schema|tables?|views?|columns?|objects?|fact_|dim_|information_schema|"
    r"primary key|foreign key|relationships?|explain every)\b",
    re.I,
)
_POWERBI = re.compile(r"\b(power\s*bi|dashboard|visualize|report url)\b", re.I)
_ML = re.compile(
    r"\b(predict|prediction|ml|machine learning|random forest|feature importance|"
    r"anomaly|failure model|classify wafer)\b",
    re.I,
)
_RECOMMEND = re.compile(
    r"\b(recommend|recommendation|improve|how can we|what should|action|"
    r"next steps?|mitigate)\b",
    re.I,
)
_ANALYTICS = re.compile(
    r"\b(why|interpret|insight|trend|compare|analysis|meaning of (these|the) numbers|"
    r"what does .+ mean)\b",
    re.I,
)
_DATA = re.compile(
    r"\b(yield|passed|failed|fail|pass|month|sensor|kpi|count|total|average|"
    r"how many|show me|list|top|worst|best|summary)\b",
    re.I,
)
_SMALLTALK = re.compile(
    r"^(hi|hello|hey|thanks|thank you|good (morning|afternoon|evening))\b",
    re.I,
)


def plan(question: str, request: OrchestratorRequest) -> ExecutionPlan:
    """
    Build an execution plan of specialized agents.

    The Planner never executes SQL — it only decides who runs and in what order.
    """
    q = (question or "").strip()
    intent = q.split("(Conversation context")[0].strip() or q
    lower = intent.lower()
    mem = get_memory(request.session_id)
    has_session = bool(request.session_id)
    follow_up = is_follow_up(intent)

    tasks: list[AgentTask] = []
    rationale_parts: list[str] = []
    style = "standard"

    if _SMALLTALK.match(intent):
        tasks.append(AgentTask("knowledge", "Acknowledge and offer analytics help", "knowledge"))
        rationale_parts.append("smalltalk → knowledge")
        style = "direct"
        return _done(tasks, rationale_parts, style)

    if _POWERBI.search(lower) and not _DATA.search(lower):
        tasks.append(AgentTask("powerbi", "Explain / validate Power BI dashboard integration"))
        rationale_parts.append("powerbi intent")
        style = "direct"
        return _done(tasks, rationale_parts, style)

    if _ML.search(lower):
        if has_session or _DATA.search(lower):
            tasks.append(AgentTask("database", "Gather wafer/sensor context for ML", tool_hint=_tool_hint(lower)))
            rationale_parts.append("ml needs data context")
        tasks.append(AgentTask("ml", "Run or explain failure prediction model"))
        if _ANALYTICS.search(lower) or _RECOMMEND.search(lower):
            tasks.append(AgentTask("analytics", "Interpret ML / manufacturing findings"))
        if _RECOMMEND.search(lower):
            tasks.append(AgentTask("recommendation", "Suggest process improvements from ML findings"))
        rationale_parts.append("ml pipeline")
        style = "detailed"
        return _done(tasks, rationale_parts, style)

    knowledge_only = bool(_KNOWLEDGE.search(lower)) and not (
        _DATA.search(lower) or _SCHEMA.search(lower) or _RECOMMEND.search(lower)
    )
    # Conceptual Qs without live metrics
    if knowledge_only and not follow_up:
        tasks.append(AgentTask("knowledge", "Answer from curated knowledge base", "knowledge"))
        rationale_parts.append("conceptual → knowledge")
        style = "direct"
        return _done(tasks, rationale_parts, style)

    if _SCHEMA.search(lower) and not _DATA.search(lower):
        if has_session:
            tasks.append(AgentTask("schema", "Inspect schema / semantic profile"))
            rationale_parts.append("schema inspection")
            # Catalog questions are answered by Schema Agent alone
            if any(k in lower for k in ("every table", "all table", "objects exist", "list table")):
                style = "detailed"
                return _done(tasks, rationale_parts, style)
            tasks.append(AgentTask("knowledge", "Explain schema concepts in business language", "knowledge"))
            rationale_parts.append("schema + knowledge")
        else:
            tasks.append(AgentTask("knowledge", "Explain schema concepts from knowledge base", "knowledge"))
            rationale_parts.append("schema concepts without live DB")
        style = "detailed" if "every" in lower else "standard"
        return _done(tasks, rationale_parts, style)

    # Follow-up "Why?" with prior topic → analytics (+ optional recommendation)
    if follow_up and mem and (mem.last_sql_result or mem.last_topic):
        if not any(t.agent == "database" for t in tasks):
            # Prefer analytics over re-query when memory has results
            if mem.last_sql_result and _ANALYTICS.search(lower):
                tasks.append(AgentTask("analytics", f"Explain prior finding: {mem.last_topic or 'previous result'}"))
                if _RECOMMEND.search(lower) or "why" in lower:
                    tasks.append(AgentTask("recommendation", "Recommend improvements based on prior analysis"))
                rationale_parts.append("follow-up using session memory")
                style = "detailed"
                return _done(tasks, rationale_parts, style)
            tasks.append(
                AgentTask(
                    "database",
                    "Resolve follow-up with live data",
                    tool_hint=_tool_hint(lower) or _tool_hint(mem.last_topic or ""),
                )
            )
            rationale_parts.append("follow-up → database")

    needs_data = bool(_DATA.search(lower)) or has_session and not knowledge_only
    needs_analytics = bool(_ANALYTICS.search(lower)) or ("why" in lower)
    needs_recommend = bool(_RECOMMEND.search(lower))

    # Complex: why lowest yield + improve
    if needs_data or has_session:
        hint = _tool_hint(lower)
        if "worst" in lower or ("lowest" in lower and "yield" in lower):
            hint = hint or "worst_month"
        elif "best" in lower or ("highest" in lower and "yield" in lower):
            hint = hint or "best_month"
        elif "monthly" in lower and "yield" in lower:
            hint = hint or "monthly_yield"
        elif "sensor" in lower:
            hint = hint or "sensor_comparison"
        elif "summary" in lower or "overall" in lower:
            hint = hint or "overall_summary"
        elif needs_recommend and not needs_analytics:
            hint = hint or "recommendations"

        tasks.append(
            AgentTask(
                "database",
                "Retrieve manufacturing / SQL evidence",
                tool_hint=hint,
            )
        )
        rationale_parts.append(f"database (hint={hint})")

    if needs_analytics and tasks:
        tasks.append(AgentTask("analytics", "Interpret quantitative findings"))
        rationale_parts.append("analytics interpretation")
        style = "detailed"

    if needs_recommend:
        tasks.append(AgentTask("recommendation", "Generate actionable recommendations"))
        rationale_parts.append("recommendations")
        style = "detailed"

    if not tasks:
        if has_session:
            tasks.append(AgentTask("database", "Answer via SQL agent path"))
            rationale_parts.append("default → database")
        else:
            tasks.append(AgentTask("knowledge", "Fallback conceptual answer", "knowledge"))
            rationale_parts.append("default → knowledge")

    return _done(tasks, rationale_parts, style)


def _tool_hint(text: str) -> str | None:
    lower = (text or "").lower()
    if "recommend" in lower:
        return "recommendations"
    if "worst" in lower or "lowest" in lower:
        return "worst_month"
    if "best" in lower or "highest" in lower:
        return "best_month"
    if "monthly" in lower and "yield" in lower:
        return "monthly_yield"
    if "sensor" in lower:
        return "sensor_comparison"
    if "summary" in lower or "overall" in lower:
        return "overall_summary"
    if any(k in lower for k in ("wafer", "secom", "etl", "architecture", "what is")):
        return "knowledge"
    return None


def _done(tasks: list[AgentTask], parts: list[str], style: str) -> ExecutionPlan:
    # Deduplicate consecutive same agent
    deduped: list[AgentTask] = []
    for task in tasks:
        if deduped and deduped[-1].agent == task.agent and deduped[-1].goal == task.goal:
            continue
        deduped.append(task)
    rationale = " -> ".join(parts) if parts else "default plan"
    logger.info("Planner plan: %s | agents=%s", rationale, [t.agent for t in deduped])
    return ExecutionPlan(tasks=deduped, rationale=rationale, response_style=style)
