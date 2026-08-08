"""
Generic SQL Agent orchestrator.

Pipeline: Intent → Semantic Route → (SQL | Knowledge | Profile) → Formatter
"""

from __future__ import annotations

import json
import logging
import re
import time

from ai.llm import chat
from ai.sql_agent.errors import (
    FRIENDLY_PROFILE_ERROR,
    FRIENDLY_QUERY_ERROR,
    sanitize_user_message,
)
from ai.sql_agent.executor import (
    execute_metadata,
    execute_validated_sql,
)
from ai.sql_agent.formatter import (
    compact_result_for_prompt,
    follow_ups_for,
    format_analysis_answer,
    format_analysis_failure,
    format_metadata_answer,
    format_smalltalk,
)
from ai.sql_agent.planner import MetadataIntent, Plan, QuestionCategory, classify_question
from ai.sql_agent.profiler import (
    ProfileBuildError,
    ensure_profile,
)
from ai.sql_agent.metadata_reasoning import (
    follow_ups_for_metadata,
    follow_ups_for_understanding,
    format_columns_for_table,
    format_explain_tables,
    format_keys,
    format_row_counts,
    format_sample_answer,
    format_table_catalog,
    format_views_catalog,
    pick_primary_fact_table,
    resolve_table,
)
from ai.sql_agent.context import resolve_contextual_question
from ai.sql_agent.followups import dynamic_follow_ups
from ai.sql_agent.prompts import (
    BUSINESS_REASONING_SYSTEM,
    DB_UNDERSTANDING_SYSTEM,
    KNOWLEDGE_ANSWER_SYSTEM,
    SQL_GENERATION_SYSTEM,
    SQL_RETRY_SYSTEM,
    build_knowledge_user_prompt,
    build_reasoning_user_prompt,
    build_sql_explain_user_prompt,
    build_sql_generation_user_prompt,
    build_sql_retry_user_prompt,
    build_understanding_user_prompt,
    explain_system_for_mode,
)
from ai.sql_agent.response_mode import ResponseMode
from ai.sql_agent.semantics import (
    locked_object_schema_text,
    route_question,
    semantic_profile_text,
)
from ai.sql_agent.kpi import (
    execute_kpi_query,
    format_kpi_answer,
    is_kpi_route,
)
from ai.sql_agent.session_store import (
    get_schema,
    get_session,
    inspect_schema,
    set_schema,
    truncate_schema_for_llm,
)
from ai.sql_agent.templates import sql_sample_rows
from ai.sql_agent.validator import UnsafeSqlError, validate_select_only

logger = logging.getLogger(__name__)


def _safe_validation(text: str) -> str:
    """Developer-facing status — never raw ODBC dumps."""
    from ai.sql_agent.errors import looks_like_raw_db_error

    cleaned = (text or "").strip()
    if not cleaned:
        return "n/a"
    if looks_like_raw_db_error(cleaned):
        return "failed (see server logs)"
    if len(cleaned) > 220:
        return cleaned[:217] + "..."
    return cleaned


def _json_safe(value):
    """Convert SQL cell values to JSON-friendly primitives."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def _kpi_visualization(question: str, totals) -> dict | None:
    """Optional chart for multi-metric KPI asks (e.g. compare passed vs failed)."""
    from ai.sql_agent.visualization import build_visualization, wants_visualization

    if not wants_visualization(question, row_count=3, column_count=2):
        # Still allow compare-style questions
        q = (question or "").lower()
        if not any(k in q for k in ("compare", "passed vs", "failed vs", "show", "chart")):
            return None
    data = []
    if totals.passed is not None:
        data.append({"label": "passed", "value": float(totals.passed)})
    if totals.failed is not None:
        data.append({"label": "failed", "value": float(totals.failed)})
    if totals.total_wafers is not None and len(data) < 2:
        data.append({"label": "total", "value": float(totals.total_wafers)})
    if len(data) < 2:
        return None
    return {
        "type": "bar",
        "title": "Production totals",
        "xAxis": "Metric",
        "yAxis": "Count",
        "data": data,
    }
    return cleaned


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError("Model did not return JSON.") from None
        return json.loads(match.group(0))


def _ensure_schema(session_id: str, config) -> str:
    schema = get_schema(session_id)
    if not schema or len(schema) > 24_000:
        schema = inspect_schema(config)
        set_schema(session_id, schema)
    return truncate_schema_for_llm(schema)


def _base_response(
    *,
    answer: str,
    config_database: str,
    category: QuestionCategory,
    sql: str | None = None,
    sql_executed: bool = False,
    row_count: int = 0,
    columns: list[str] | None = None,
    rows: list | None = None,
    visualization: dict | None = None,
    execution_time: float = 0.0,
    validation_result: str = "n/a",
    follow_ups: list[str] | None = None,
) -> dict:
    # Only expose SQL when it actually ran successfully.
    safe_sql = sql if sql_executed and sql else None
    return {
        "answer": answer,
        "sql": safe_sql,
        "sql_executed": bool(sql_executed and safe_sql),
        "columns": list(columns or []),
        "rows": list(rows or []),
        "visualization": visualization,
        "row_count": row_count,
        "data_source": f"Azure SQL · {config_database}",
        "tool": "sql_agent",
        "tool_label": "Azure Data Copilot",
        "category": category.value,
        "router_decision": category.value,
        "validation_result": _safe_validation(validation_result),
        "execution_time": execution_time,
        "follow_ups": follow_ups if follow_ups is not None else follow_ups_for(category),
    }


def _handle_smalltalk(config, schema: str, started: float) -> dict:
    names: list[str] = []
    for line in schema.splitlines():
        match = re.match(r"^([\w\[\]\.]+)\s+\((TABLE|VIEW)\)", line.strip())
        if match:
            names.append(match.group(1))
    return _base_response(
        answer=format_smalltalk(config.database, names),
        config_database=config.database,
        category=QuestionCategory.SMALLTALK,
        validation_result="skipped (greeting)",
        execution_time=round(time.perf_counter() - started, 2),
    )


def _handle_knowledge(session_id: str, config, plan: Plan, started: float) -> dict:
    """Knowledge questions — NEVER execute SQL."""
    from ai.tools.knowledge import run as knowledge_run

    evidence_parts: list[str] = []
    try:
        kb = knowledge_run(plan.question)
        evidence_parts.append(str(kb.get("data") or ""))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Knowledge tool failed: %s", exc)

    try:
        profile = ensure_profile(session_id, config)
        evidence_parts.append(
            "\n\n## Connected database semantic snapshot\n"
            + semantic_profile_text(profile, max_chars=3_000)
        )
    except Exception:  # noqa: BLE001
        pass

    evidence = "\n".join(p for p in evidence_parts if p).strip()
    if not evidence:
        evidence = "No knowledge base available."

    try:
        answer = chat(
            [
                {"role": "system", "content": KNOWLEDGE_ANSWER_SYSTEM},
                {
                    "role": "user",
                    "content": build_knowledge_user_prompt(plan.question, evidence),
                },
            ],
            temperature=0.2,
        )
        return _base_response(
            answer=answer.strip(),
            config_database=config.database,
            category=QuestionCategory.KNOWLEDGE,
            sql=None,
            validation_result="knowledge tool / profile (no SQL)",
            execution_time=round(time.perf_counter() - started, 2),
            follow_ups=follow_ups_for(QuestionCategory.KNOWLEDGE),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Knowledge answer failed")
        return _base_response(
            answer=sanitize_user_message(str(exc), fallback=FRIENDLY_QUERY_ERROR),
            config_database=config.database,
            category=QuestionCategory.KNOWLEDGE,
            validation_result="knowledge failed",
            execution_time=round(time.perf_counter() - started, 2),
        )


def _handle_metadata(session_id: str, config, plan: Plan, started: float) -> dict:
    """
    Answer metadata from the cached schema profile whenever possible.

    SAMPLE_ROWS executes a safe TOP 10 against the primary fact / largest table.
    """
    intent = plan.metadata_intent or MetadataIntent.LIST_TABLES
    sample_table = None
    sql_used = None
    row_count = 0

    try:
        profile = ensure_profile(session_id, config)
    except ProfileBuildError:
        return _base_response(
            answer=FRIENDLY_PROFILE_ERROR,
            config_database=config.database,
            category=QuestionCategory.METADATA,
            validation_result="profile unavailable",
            execution_time=round(time.perf_counter() - started, 2),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Metadata profile load failed: %s", exc)
        return _base_response(
            answer=FRIENDLY_PROFILE_ERROR,
            config_database=config.database,
            category=QuestionCategory.METADATA,
            validation_result="profile unavailable",
            execution_time=round(time.perf_counter() - started, 2),
        )

    try:
        if intent == MetadataIntent.SAMPLE_ROWS:
            sample_table = pick_primary_fact_table(profile)
            if plan.target_table:
                resolved = resolve_table(profile, plan.target_table)
                if resolved:
                    sample_table = resolved
            if sample_table is None:
                answer = "No tables are available to sample from the schema profile."
            else:
                sql = sql_sample_rows(sample_table.schema, sample_table.name, 10)
                result = execute_validated_sql(
                    config,
                    sql,
                    label=f"Sample · {sample_table.schema}.{sample_table.name}",
                    max_rows=10,
                )
                if result.error:
                    answer = FRIENDLY_QUERY_ERROR
                else:
                    columns = result.columns
                    rows = result.rows
                    if len(columns) > 12:
                        columns = columns[:12]
                        rows = [tuple(r[:12]) for r in rows]
                    answer = format_sample_answer(
                        table=sample_table, columns=columns, rows=rows
                    )
                    sql_used = result.sql
                    row_count = len(rows)
        elif intent in (MetadataIntent.LIST_TABLES, MetadataIntent.EXPLAIN_ALL):
            if intent == MetadataIntent.EXPLAIN_ALL:
                from ai.sql_agent.schema_knowledge import (
                    build_schema_knowledge,
                    format_full_object_catalog,
                )

                model = build_schema_knowledge(profile)
                answer = format_full_object_catalog(model)
                row_count = model.object_count
            else:
                answer = format_explain_tables(profile, include_views=False)
                row_count = profile.table_count
        elif intent == MetadataIntent.DESCRIBE_SCHEMA:
            from ai.sql_agent.schema_knowledge import (
                build_schema_knowledge,
                format_full_object_catalog,
            )

            model = build_schema_knowledge(profile)
            answer = format_full_object_catalog(model)
            row_count = model.object_count
        elif intent == MetadataIntent.LIST_VIEWS:
            answer = format_views_catalog(profile)
            row_count = profile.view_count
        elif intent == MetadataIntent.LIST_COLUMNS:
            answer = format_columns_for_table(profile, plan.target_table)
            row_count = profile.table_count
        elif intent == MetadataIntent.ROW_COUNTS:
            answer = format_row_counts(profile)
            row_count = profile.table_count
        elif intent == MetadataIntent.PRIMARY_KEYS:
            answer = format_keys(profile, kind="pk")
        elif intent in (MetadataIntent.FOREIGN_KEYS, MetadataIntent.RELATIONSHIPS):
            answer = format_keys(profile, kind="fk")
        elif intent == MetadataIntent.INDEXES:
            bundle = execute_metadata(config, plan)
            answer = format_metadata_answer(intent, bundle)
            sql_used = bundle.primary_sql
            primary = bundle.results[-1] if bundle.results else None
            row_count = primary.row_count if primary else 0
        else:
            answer = format_explain_tables(profile, include_views=False)

        suggestions = dynamic_follow_ups(
            category=QuestionCategory.METADATA,
            question=plan.question,
            profile=profile,
            answer=answer,
        )
        if not suggestions:
            suggestions = follow_ups_for_metadata(
                intent, profile, sample_table=sample_table
            )
        return _base_response(
            answer=answer,
            config_database=config.database,
            category=QuestionCategory.METADATA,
            sql=sql_used,
            sql_executed=bool(sql_used),
            row_count=row_count,
            validation_result=f"schema profile · {intent.value}",
            execution_time=round(time.perf_counter() - started, 2),
            follow_ups=suggestions,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Metadata reasoning failed")
        return _base_response(
            answer=sanitize_user_message(str(exc), fallback=FRIENDLY_QUERY_ERROR),
            config_database=config.database,
            category=QuestionCategory.METADATA,
            validation_result="failed (metadata)",
            execution_time=round(time.perf_counter() - started, 2),
        )


def _handle_understanding(session_id: str, config, started: float) -> dict:
    """Whole-database business understanding — full knowledge model, no SQL."""
    try:
        from ai.sql_agent.schema_knowledge import (
            build_schema_knowledge,
            knowledge_model_to_text,
        )

        profile = ensure_profile(session_id, config)
        model = build_schema_knowledge(profile)
        evidence = knowledge_model_to_text(model)
        summary = chat(
            [
                {"role": "system", "content": DB_UNDERSTANDING_SYSTEM},
                {"role": "user", "content": build_understanding_user_prompt(evidence)},
            ],
            temperature=0.2,
        )
        answer = summary.strip()
        return _base_response(
            answer=answer,
            config_database=config.database,
            category=QuestionCategory.BUSINESS_UNDERSTANDING,
            sql=None,
            row_count=model.object_count,
            validation_result=(
                f"schema knowledge model · {model.object_count} objects · no SQL"
            ),
            execution_time=round(time.perf_counter() - started, 2),
            follow_ups=dynamic_follow_ups(
                category=QuestionCategory.BUSINESS_UNDERSTANDING,
                question="What is this database used for?",
                profile=profile,
                answer=answer,
            )
            or follow_ups_for_understanding(profile),
        )
    except ProfileBuildError:
        return _base_response(
            answer=FRIENDLY_PROFILE_ERROR,
            config_database=config.database,
            category=QuestionCategory.BUSINESS_UNDERSTANDING,
            validation_result="profile build failed",
            execution_time=round(time.perf_counter() - started, 2),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Business understanding failed: %s", exc)
        return _base_response(
            answer=FRIENDLY_PROFILE_ERROR,
            config_database=config.database,
            category=QuestionCategory.BUSINESS_UNDERSTANDING,
            validation_result="understanding failed",
            execution_time=round(time.perf_counter() - started, 2),
        )


def _handle_reasoning(session_id: str, config, plan: Plan, started: float) -> dict:
    """Business reasoning from schema knowledge — never KPI-only, never SQL."""
    try:
        from ai.sql_agent.schema_knowledge import (
            build_schema_knowledge,
            knowledge_model_to_text,
        )

        profile = ensure_profile(session_id, config)
        model = build_schema_knowledge(profile)
        evidence = knowledge_model_to_text(model)
        narrative = chat(
            [
                {"role": "system", "content": BUSINESS_REASONING_SYSTEM},
                {
                    "role": "user",
                    "content": build_reasoning_user_prompt(plan.question, evidence),
                },
            ],
            temperature=0.25,
        )
        answer = narrative.strip()
        return _base_response(
            answer=answer,
            config_database=config.database,
            category=QuestionCategory.BUSINESS_REASONING,
            sql=None,
            row_count=model.object_count,
            validation_result=(
                f"business reasoning · knowledge model ({model.object_count} objects) · no SQL"
            ),
            execution_time=round(time.perf_counter() - started, 2),
            follow_ups=dynamic_follow_ups(
                category=QuestionCategory.BUSINESS_REASONING,
                question=plan.question,
                profile=profile,
                answer=answer,
            )
            or [
                "How many failed wafers?",
                "What is the overall yield?",
                "Explain every table",
                "Show sample rows",
            ],
        )
    except ProfileBuildError:
        return _base_response(
            answer=FRIENDLY_PROFILE_ERROR,
            config_database=config.database,
            category=QuestionCategory.BUSINESS_REASONING,
            validation_result="profile unavailable",
            execution_time=round(time.perf_counter() - started, 2),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Business reasoning failed")
        return _base_response(
            answer=sanitize_user_message(str(exc), fallback=FRIENDLY_QUERY_ERROR),
            config_database=config.database,
            category=QuestionCategory.BUSINESS_REASONING,
            validation_result="failed (reasoning)",
            execution_time=round(time.perf_counter() - started, 2),
        )


def _handle_schema(session_id: str, config, plan: Plan, started: float) -> dict:
    """Explain EVERY table and view from the schema knowledge model."""
    try:
        from ai.sql_agent.schema_knowledge import (
            build_schema_knowledge,
            format_full_object_catalog,
        )

        profile = ensure_profile(session_id, config)
        model = build_schema_knowledge(profile)
        answer = format_full_object_catalog(model)
        return _base_response(
            answer=answer,
            config_database=config.database,
            category=QuestionCategory.SCHEMA,
            sql=None,
            row_count=model.object_count,
            validation_result=(
                f"full object catalog · {model.object_count} tables/views · no SQL"
            ),
            execution_time=round(time.perf_counter() - started, 2),
            follow_ups=dynamic_follow_ups(
                category=QuestionCategory.SCHEMA,
                question=plan.question,
                profile=profile,
                answer=answer,
            ),
        )
    except ProfileBuildError:
        return _base_response(
            answer=FRIENDLY_PROFILE_ERROR,
            config_database=config.database,
            category=QuestionCategory.SCHEMA,
            validation_result="profile unavailable",
            execution_time=round(time.perf_counter() - started, 2),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Schema explanation failed")
        return _base_response(
            answer=sanitize_user_message(str(exc), fallback=FRIENDLY_QUERY_ERROR),
            config_database=config.database,
            category=QuestionCategory.SCHEMA,
            validation_result="failed (schema)",
            execution_time=round(time.perf_counter() - started, 2),
        )


def _generate_sql(
    question: str,
    schema: str,
    *,
    routing_guidance: str = "",
    preferred_objects: str = "",
    locked_object: str = "",
) -> str:
    raw = chat(
        [
            {"role": "system", "content": SQL_GENERATION_SYSTEM},
            {
                "role": "user",
                "content": build_sql_generation_user_prompt(
                    question,
                    schema,
                    routing_guidance=routing_guidance,
                    preferred_objects=preferred_objects,
                    locked_object=locked_object,
                ),
            },
        ],
        temperature=0.0,
        json_mode=True,
    )
    payload = _extract_json(raw)
    sql = str(payload.get("sql", "")).strip()
    if not sql:
        raise ValueError("Empty SQL returned by the model.")
    return sql


def _retry_sql(
    question: str,
    schema: str,
    previous_sql: str,
    error: str,
    *,
    routing_guidance: str = "",
) -> str:
    raw = chat(
        [
            {"role": "system", "content": SQL_RETRY_SYSTEM},
            {
                "role": "user",
                "content": build_sql_retry_user_prompt(
                    question,
                    schema,
                    previous_sql,
                    error,
                    routing_guidance=routing_guidance,
                ),
            },
        ],
        temperature=0.0,
        json_mode=True,
    )
    payload = _extract_json(raw)
    sql = str(payload.get("sql", "")).strip()
    if not sql:
        raise ValueError("Empty SQL returned on retry.")
    return sql


def _preferred_objects_text(route) -> str:
    lines: list[str] = []
    for tp in route.preferred:
        metrics = ", ".join(tp.key_metrics[:8]) if tp.key_metrics else "(see columns)"
        preferred = ", ".join(getattr(tp, "preferred_for", None) or tp.use_cases or [])
        lines.append(
            f"- {tp.schema}.{tp.name} [{tp.business_role or tp.object_type}] "
            f"— {tp.purpose or ''} | metrics: {metrics}"
            + (f" | preferred for: {preferred}" if preferred else "")
        )
    return "\n".join(lines) if lines else "(none — choose best object from profile)"


def _run_sql_and_explain(
    *,
    config,
    plan: Plan,
    candidate_sql: str,
    category: QuestionCategory,
    started: float,
    schema_for_retry: str,
    routing_guidance: str,
    mode: ResponseMode,
) -> dict:
    """Validate → execute → explain with one retry."""
    last_error = ""
    sql_attempt = candidate_sql

    for attempt in range(2):
        try:
            if not sql_attempt:
                raise ValueError(last_error or "No SQL generated.")

            safe_sql = validate_select_only(sql_attempt)
            result = execute_validated_sql(config, safe_sql)
            if result.error:
                raise RuntimeError(
                    sanitize_user_message(result.error, fallback=FRIENDLY_QUERY_ERROR)
                )

            result_text = compact_result_for_prompt(result, mode)
            if len(result_text) > 4_000:
                result_text = result_text[:4_000] + "\n...(truncated)"

            temperature = 0.1 if mode == ResponseMode.DIRECT else 0.2
            narrative = chat(
                [
                    {"role": "system", "content": explain_system_for_mode(mode)},
                    {
                        "role": "user",
                        "content": build_sql_explain_user_prompt(
                            plan.question, safe_sql, result_text, mode
                        ),
                    },
                ],
                temperature=temperature,
            )
            answer = format_analysis_answer(
                narrative=narrative,
                sql=safe_sql,
                result=result,
                mode=mode,
            )
            from ai.sql_agent.visualization import build_visualization

            viz = build_visualization(
                plan.question,
                list(result.columns),
                list(result.rows),
            )
            route_note = f" · route={routing_guidance[:80]}" if routing_guidance else ""
            return _base_response(
                answer=answer,
                config_database=config.database,
                category=category,
                sql=safe_sql,
                sql_executed=True,
                row_count=result.row_count,
                columns=list(result.columns),
                rows=[[_json_safe(c) for c in row] for row in result.rows[:50]],
                visualization=viz,
                validation_result=(
                    f"passed (SELECT-only) · response_mode={mode.value}{route_note}"
                ),
                execution_time=round(time.perf_counter() - started, 2),
            )
        except (UnsafeSqlError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            logger.warning("SQL attempt %s failed: %s", attempt + 1, last_error)
            if attempt == 0:
                try:
                    sql_attempt = _retry_sql(
                        plan.question,
                        truncate_schema_for_llm(schema_for_retry, max_chars=8_000),
                        sql_attempt or "(none)",
                        last_error,
                        routing_guidance=routing_guidance,
                    )
                except Exception as retry_exc:  # noqa: BLE001
                    last_error = f"{last_error}; retry generation failed: {retry_exc}"
                    break
            else:
                break
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            logger.exception("Unexpected SQL analysis failure")
            if attempt == 0:
                try:
                    sql_attempt = _retry_sql(
                        plan.question,
                        truncate_schema_for_llm(schema_for_retry, max_chars=8_000),
                        sql_attempt or "(none)",
                        last_error,
                        routing_guidance=routing_guidance,
                    )
                    continue
                except Exception as retry_exc:  # noqa: BLE001
                    last_error = f"{last_error}; retry failed: {retry_exc}"
            break

    return _base_response(
        answer=format_analysis_failure(last_error or "Unknown failure"),
        config_database=config.database,
        category=category,
        sql=None,
        sql_executed=False,
        row_count=0,
        validation_result=f"failed: {last_error or 'unknown'}",
        execution_time=round(time.perf_counter() - started, 2),
    )


def _handle_kpi(session_id: str, config, plan: Plan, schema: str, started: float) -> dict:
    """
    KPI path: dataset-level totals only.

    - Never TOP 1 / first grain row
    - Detect summary vs periodic views; SUM when multi-row
    - Validate passed+failed == total; retry with SUM on failure
    - Concise answers (no LLM paragraphs)
    """
    del schema  # semantic profile drives KPI routing
    try:
        profile = ensure_profile(session_id, config)
        route = route_question(profile, plan.question, is_kpi=True)
        totals = execute_kpi_query(config, profile, plan.question)
        answer = format_kpi_answer(plan.question, totals)
        mode_note = "Semiconductor" if route.semiconductor_mode else "Generic"
        grain_note = totals.grain.value if totals.grain else "unknown"
        profile_for_fu = profile
        return _base_response(
            answer=answer,
            config_database=config.database,
            category=QuestionCategory.KPI,
            sql=totals.sql,
            sql_executed=bool(totals.sql),
            row_count=1,
            visualization=_kpi_visualization(plan.question, totals),
            validation_result=(
                f"kpi · {mode_note} · grain={grain_note} · "
                f"source={totals.source} · validated={totals.validated}"
            ),
            execution_time=round(time.perf_counter() - started, 2),
            follow_ups=dynamic_follow_ups(
                category=QuestionCategory.KPI,
                question=plan.question,
                profile=profile_for_fu,
                answer=answer,
            )
            or follow_ups_for(QuestionCategory.KPI),
        )
    except ProfileBuildError:
        return _base_response(
            answer=FRIENDLY_PROFILE_ERROR,
            config_database=config.database,
            category=QuestionCategory.KPI,
            validation_result="profile unavailable",
            execution_time=round(time.perf_counter() - started, 2),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("KPI handler failed")
        return _base_response(
            answer=format_analysis_failure(str(exc)),
            config_database=config.database,
            category=QuestionCategory.KPI,
            validation_result=f"failed: {exc}",
            execution_time=round(time.perf_counter() - started, 2),
        )


def _handle_analytical(
    session_id: str,
    config,
    plan: Plan,
    schema: str,
    started: float,
) -> dict:
    """Analytical path: semantic route → locked object → SQL → explain."""
    mode = plan.response_mode or ResponseMode.DIRECT
    routing_guidance = ""
    preferred_text = ""
    semantic_schema = schema
    candidate_sql = ""
    locked_name = ""

    try:
        profile = ensure_profile(session_id, config)
        route = route_question(profile, plan.question, is_kpi=False)
        routing_guidance = route.guidance
        preferred_text = _preferred_objects_text(route)
        locked_name = route.locked_object or ""

        # Semiconductor / locked: only expose the preferred object to the LLM
        if route.preferred and (route.semiconductor_mode or route.locked_object):
            semantic_schema = locked_object_schema_text(route.preferred[0])
        else:
            semantic_schema = semantic_profile_text(profile)

        candidate_sql = _generate_sql(
            plan.question,
            semantic_schema,
            routing_guidance=routing_guidance,
            preferred_objects=preferred_text,
            locked_object=locked_name,
        )
    except ProfileBuildError:
        try:
            candidate_sql = _generate_sql(plan.question, schema)
        except Exception as exc:  # noqa: BLE001
            return _base_response(
                answer=format_analysis_failure(str(exc)),
                config_database=config.database,
                category=QuestionCategory.ANALYTICAL,
                validation_result=f"failed: {exc}",
                execution_time=round(time.perf_counter() - started, 2),
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Analytical routing failed")
        return _base_response(
            answer=format_analysis_failure(str(exc)),
            config_database=config.database,
            category=QuestionCategory.ANALYTICAL,
            validation_result=f"failed: {exc}",
            execution_time=round(time.perf_counter() - started, 2),
        )

    return _run_sql_and_explain(
        config=config,
        plan=plan,
        candidate_sql=candidate_sql,
        category=QuestionCategory.ANALYTICAL,
        started=started,
        schema_for_retry=semantic_schema,
        routing_guidance=routing_guidance,
        mode=mode,
    )


def ask_sql_agent(
    session_id: str,
    question: str,
    *,
    history: list | None = None,
) -> dict:
    """
    Intent → Route → Execute (enterprise analytics assistant).

    1. Resolve conversation context for follow-ups
    2. Classify WHAT (KPI | Schema | Business understanding | Metadata |
       Analytical | Knowledge | Smalltalk)
    3. Determine WHICH table/view (semantic routing / Semiconductor locks)
    4. Generate or skip SQL accordingly
    """
    cleaned = question.strip()
    if not cleaned:
        raise ValueError("Question cannot be empty.")

    config = get_session(session_id)
    if config is None:
        raise ValueError("No active database session. Connect a data source first.")

    started = time.perf_counter()
    resolved = resolve_contextual_question(cleaned, history)
    plan = classify_question(resolved)

    # Safety net: force KPI handler when business-metric language is present
    intent_probe = resolved.split("(Conversation context")[0].strip() or resolved
    if (
        is_kpi_route(intent_probe)
        and plan.category
        not in (
            QuestionCategory.METADATA,
            QuestionCategory.SCHEMA,
            QuestionCategory.BUSINESS_UNDERSTANDING,
            QuestionCategory.BUSINESS_REASONING,
            QuestionCategory.KNOWLEDGE,
            QuestionCategory.SMALLTALK,
        )
        and plan.category != QuestionCategory.KPI
    ):
        from ai.sql_agent.intent import QuestionIntent
        from ai.sql_agent.planner import Plan as PlanCls
        from ai.sql_agent.response_mode import classify_response_mode

        plan = PlanCls(
            category=QuestionCategory.KPI,
            question=intent_probe,
            intent=QuestionIntent.KPI,
            response_mode=classify_response_mode(intent_probe),
        )

    schema = _ensure_schema(session_id, config)

    if plan.category == QuestionCategory.SMALLTALK:
        return _handle_smalltalk(config, schema, started)

    if plan.category == QuestionCategory.KNOWLEDGE:
        result = _handle_knowledge(session_id, config, plan, started)
        try:
            profile = ensure_profile(session_id, config)
            result["follow_ups"] = dynamic_follow_ups(
                category=QuestionCategory.KNOWLEDGE,
                question=plan.question,
                profile=profile,
                answer=result.get("answer"),
            )
        except Exception:  # noqa: BLE001
            pass
        return result

    if plan.category == QuestionCategory.SCHEMA:
        return _handle_schema(session_id, config, plan, started)

    if plan.category == QuestionCategory.METADATA:
        return _handle_metadata(session_id, config, plan, started)

    if plan.category == QuestionCategory.BUSINESS_REASONING:
        return _handle_reasoning(session_id, config, plan, started)

    if plan.category in (
        QuestionCategory.BUSINESS_UNDERSTANDING,
        QuestionCategory.DATABASE_UNDERSTANDING,
    ):
        return _handle_understanding(session_id, config, started)

    if plan.category == QuestionCategory.KPI:
        return _handle_kpi(session_id, config, plan, schema, started)

    result = _handle_analytical(session_id, config, plan, schema, started)
    try:
        profile = ensure_profile(session_id, config)
        result["follow_ups"] = dynamic_follow_ups(
            category=QuestionCategory.ANALYTICAL,
            question=plan.question,
            profile=profile,
            answer=result.get("answer"),
        )
    except Exception:  # noqa: BLE001
        pass
    return result
