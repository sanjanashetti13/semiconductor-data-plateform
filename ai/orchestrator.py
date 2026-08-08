"""Multi-agent orchestrator — Planner → agents → merge → final answer."""

from __future__ import annotations

import logging
import time
from typing import Any

from ai.agents.base import (
    AgentResult,
    ExecutionPlan,
    OrchestratorRequest,
    OrchestratorResponse,
)
from ai.agents.planner_agent import plan as build_plan
from ai.context import format_history, resolve_question
from ai.memory import ensure_memory, remember_turn
from ai.registry import ensure_registered, get_agent

logger = logging.getLogger(__name__)


def run_orchestrator(
    question: str,
    *,
    session_id: str | None = None,
    history: list[dict[str, str]] | None = None,
    power_bi_url: str | None = None,
) -> OrchestratorResponse:
    """
    Receive a user request, invoke the Planner, execute agents, merge results.

    Preserves existing SQL Agent / manufacturing tool behavior while adding
    an orchestration layer for multi-agent workflows.
    """
    ensure_registered()
    started = time.perf_counter()
    cleaned = (question or "").strip()
    if not cleaned:
        raise ValueError("Question cannot be empty.")

    history = history or []
    request = OrchestratorRequest(
        question=cleaned,
        session_id=session_id,
        history=history,
        power_bi_url=power_bi_url,
    )

    if session_id:
        from ai.sql_agent.session_store import get_session

        cfg = get_session(session_id)
        if cfg:
            ensure_memory(session_id, database=cfg.database)

    resolved = resolve_question(cleaned, history)
    execution_plan = build_plan(resolved, request)

    # Session path: SQL Agent already interprets — avoid redundant analytics agent
    execution_plan = _optimize_plan(execution_plan, request)

    bag: dict[str, Any] = {
        "resolved_question": resolved,
        "history_text": format_history(history),
        "prior_summaries": [],
        "tool_hint": None,
    }

    results: list[AgentResult] = []
    graph: list[str] = []
    agents_used: list[str] = []

    logger.info(
        "Orchestrator start session=%s plan=%s agents=%s",
        session_id,
        execution_plan.rationale,
        [t.agent for t in execution_plan.tasks],
    )

    for task in execution_plan.tasks:
        bag["tool_hint"] = task.tool_hint
        agent_fn = get_agent(task.agent)
        step_started = time.perf_counter()
        logger.info("Invoking agent=%s goal=%s", task.agent, task.goal)
        try:
            result = agent_fn(task.goal, request, bag)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent %s crashed", task.agent)
            result = AgentResult(
                agent=task.agent,
                success=False,
                summary=f"Agent {task.agent} failed.",
                error=str(exc),
            )

        elapsed = time.perf_counter() - step_started
        result.meta["execution_time"] = round(elapsed, 3)
        results.append(result)
        agents_used.append(task.agent)
        graph.append(f"{task.agent} ({'ok' if result.success else 'fail'} · {elapsed:.2f}s)")

        if result.success and result.summary and not result.meta.get("skipped"):
            bag["prior_summaries"].append(f"[{result.agent}] {result.summary}")

        logger.info(
            "Agent done agent=%s success=%s time=%.3fs error=%s",
            task.agent,
            result.success,
            elapsed,
            result.error,
        )

    answer, sql, sql_executed, visualization, follow_ups, category, row_count, data_source, validation, router = (
        _merge(execution_plan, results, request, resolved)
    )

    total = time.perf_counter() - started
    remember_turn(
        session_id,
        question=cleaned,
        answer=answer,
        sql=sql if sql_executed else None,
        sql_result=next(
            (r.summary for r in results if r.agent == "database" and r.success),
            None,
        ),
        topic=_topic(resolved),
    )

    router_decision = (
        f"planner -> {' -> '.join(agents_used)} | {execution_plan.rationale}"
    )
    if router:
        router_decision = f"{router_decision} | sql_route={router}"

    validation_result = validation
    if validation_result:
        validation_result = f"{validation_result} | graph: {' → '.join(graph)}"
    else:
        validation_result = f"agents ok | graph: {' → '.join(graph)}"

    logger.info(
        "Orchestrator complete time=%.3fs agents=%s",
        total,
        agents_used,
    )

    return OrchestratorResponse(
        answer=answer,
        sql=sql if sql_executed else None,
        sql_executed=bool(sql_executed and sql),
        visualization=visualization,
        follow_ups=follow_ups,
        category=category,
        row_count=row_count,
        data_source=data_source,
        tool="multi_agent",
        tool_label="Multi-Agent Orchestrator",
        validation_result=validation_result,
        router_decision=router_decision,
        agents_used=agents_used,
        planner_rationale=execution_plan.rationale,
        execution_graph=graph,
        execution_time=round(total, 3),
        intermediate=results,
    )


def _optimize_plan(plan: ExecutionPlan, request: OrchestratorRequest) -> ExecutionPlan:
    """Drop redundant analytics when Database Agent will call ask_sql_agent."""
    if not request.session_id:
        return plan
    agents = [t.agent for t in plan.tasks]
    if "database" in agents and "analytics" in agents:
        plan.tasks = [t for t in plan.tasks if t.agent != "analytics"]
        plan.rationale = (plan.rationale or "") + " | skip analytics (sql agent interprets)"
    return plan


def _merge(
    plan: ExecutionPlan,
    results: list[AgentResult],
    request: OrchestratorRequest,
    resolved: str,
) -> tuple:
    ok = [r for r in results if r.success and not r.meta.get("skipped")]
    empty = (None, False, None)  # sql, sql_executed, visualization
    if not ok:
        failed = results[-1].summary if results else "No agents produced an answer."
        return (failed, *empty, _default_follow_ups(), "error", 0, None, "failed", None)

    by_agent = {r.agent: r for r in ok}
    sql = next((r.sql for r in ok if r.sql), None)
    sql_executed = False
    visualization = None
    follow_ups: list[str] = []
    category = None
    row_count = 0
    data_source = None
    validation = None
    router = None

    db = by_agent.get("database")
    if db and isinstance(db.data, dict):
        follow_ups = list(db.meta.get("follow_ups") or db.data.get("follow_ups") or [])
        category = db.meta.get("category") or db.data.get("category")
        row_count = int(db.meta.get("row_count") or db.data.get("row_count") or 0)
        data_source = db.meta.get("data_source") or db.data.get("data_source")
        validation = db.meta.get("validation_result") or db.data.get("validation_result")
        router = db.meta.get("router_decision") or db.data.get("router_decision")
        sql = sql or db.data.get("sql") or db.sql
        sql_executed = bool(
            db.meta.get("sql_executed")
            if "sql_executed" in db.meta
            else db.data.get("sql_executed")
        )
        if not sql_executed and sql and db.data.get("sql_executed") is not False:
            # Legacy success path: SQL present from ask_sql_agent success
            sql_executed = bool(db.data.get("sql_executed", bool(sql)))
        visualization = db.meta.get("visualization") or db.data.get("visualization")

    for r in ok:
        data_source = data_source or r.meta.get("data_source")

    def _pack(answer: str, sql_val: str | None = sql):
        executed = bool(sql_executed and sql_val)
        return (
            answer,
            sql_val if executed else None,
            executed,
            visualization if executed else visualization,
            follow_ups or _default_follow_ups(),
            category,
            row_count,
            data_source,
            validation,
            router,
        )

    if len(ok) == 1:
        only = ok[0]
        if only.agent == "database" and request.session_id and only.summary:
            return _pack(only.summary)
        if only.agent == "database" and not request.session_id:
            return _pack(_mode1_explain(resolved, only), None)
        return (
            only.summary,
            None,
            False,
            None,
            follow_ups or _default_follow_ups(),
            category or only.agent,
            row_count,
            data_source,
            validation,
            router,
        )

    parts: list[str] = []
    if db and db.summary:
        if request.session_id:
            parts.append(db.summary)
        else:
            parts.append(_mode1_explain(resolved, db))

    for name in ("schema", "knowledge", "ml", "powerbi", "analytics", "recommendation"):
        agent = by_agent.get(name)
        if not agent or agent is db:
            continue
        if name == "knowledge" and "schema" in by_agent:
            continue
        if name in ("analytics", "recommendation") and request.session_id and db:
            header = "## Analysis" if name == "analytics" else "## Recommendations"
            body = agent.summary.strip()
            if body.startswith("#"):
                parts.append(body)
            else:
                parts.append(f"{header}\n\n{body}")
            continue
        if name not in ("analytics", "recommendation") or not db:
            parts.append(agent.summary)

    answer = "\n\n".join(p for p in parts if p).strip() or ok[-1].summary
    out = list(_pack(answer))
    out[5] = category or "multi_agent"
    return tuple(out)


def _mode1_explain(question: str, db: AgentResult) -> str:
    """Reuse existing adaptive response prompting for manufacturing tools."""
    from ai.llm import chat
    from ai.prompt import (
        ADAPTIVE_RESPONSE_SYSTEM_PROMPT,
        build_adaptive_user_prompt,
        infer_response_mode,
    )

    tool_name = db.meta.get("tool") or "overall_summary"
    data = db.summary
    source = db.meta.get("data_source") or "Azure SQL"
    mode = infer_response_mode(question, tool_name)
    return chat(
        [
            {"role": "system", "content": ADAPTIVE_RESPONSE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_adaptive_user_prompt(
                    question,
                    data,
                    source=source,
                    response_mode=mode,
                ),
            },
        ],
        temperature=0.1,
    )


def _default_follow_ups() -> list[str]:
    return [
        "Give overall production summary",
        "Which month had the lowest yield?",
        "What is the SECOM dataset?",
    ]


def _topic(question: str) -> str:
    text = question.split("(Conversation context")[0].strip()
    return text[:120]


# Public alias used by routers
run = run_orchestrator
