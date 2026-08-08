"""Executor — runs planned steps against Azure SQL (templates or validated LLM SQL)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ai.sql_agent.planner import MetadataIntent, Plan, QuestionCategory
from ai.sql_agent.session_store import SqlConnectionConfig, execute_select
from ai.sql_agent.templates import (
    resolve_metadata_sql,
    sql_list_columns,
    sql_list_tables,
    sql_list_views,
    sql_row_count,
    sql_sample_rows,
)
from ai.sql_agent.validator import validate_select_only

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result of one executed SELECT."""

    label: str
    sql: str
    columns: list[str] = field(default_factory=list)
    rows: list[tuple] = field(default_factory=list)
    error: str | None = None

    @property
    def row_count(self) -> int:
        return len(self.rows)

    def as_text(self, *, max_rows: int = 30) -> str:
        if self.error:
            return f"{self.label}: ERROR — {self.error}"
        if not self.columns:
            return f"{self.label}: (no columns)"
        lines = [self.label, " | ".join(self.columns), "-" * 20]
        if not self.rows:
            lines.append("(no rows)")
        else:
            for row in self.rows[:max_rows]:
                lines.append(str(tuple(row)))
            if len(self.rows) > max_rows:
                lines.append(f"... ({len(self.rows) - max_rows} more)")
        return "\n".join(lines)


@dataclass
class ExecutionBundle:
    """All results produced for a plan."""

    results: list[QueryResult] = field(default_factory=list)
    primary_sql: str | None = None

    def combined_text(self, *, max_chars: int = 12_000) -> str:
        text = "\n\n".join(r.as_text() for r in self.results)
        if len(text) > max_chars:
            return text[: max_chars - 40] + "\n...(truncated for model context)"
        return text

    @property
    def total_rows(self) -> int:
        return sum(r.row_count for r in self.results if not r.error)


def _run(config: SqlConnectionConfig, label: str, sql: str, *, max_rows: int = 100) -> QueryResult:
    from ai.sql_agent.errors import FRIENDLY_QUERY_ERROR, sanitize_user_message

    try:
        safe = validate_select_only(sql)
        columns, rows = execute_select(config, safe, max_rows=max_rows)
        return QueryResult(label=label, sql=safe, columns=columns, rows=rows)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Step failed (%s): %s", label, exc)
        return QueryResult(
            label=label,
            sql=sql,
            error=sanitize_user_message(str(exc), fallback=FRIENDLY_QUERY_ERROR),
        )


def _parse_table_rows(result: QueryResult) -> list[tuple[str, str]]:
    """Extract (schema, table) pairs from list-tables style results."""
    pairs: list[tuple[str, str]] = []
    if result.error or not result.rows:
        return pairs
    # Expect schema, table[, type]
    for row in result.rows:
        if len(row) >= 2:
            pairs.append((str(row[0]), str(row[1])))
    return pairs


def execute_metadata(config: SqlConnectionConfig, plan: Plan) -> ExecutionBundle:
    """Run predefined metadata templates — never LLM-generated SQL."""
    intent = plan.metadata_intent or MetadataIntent.DESCRIBE_SCHEMA
    bundle = ExecutionBundle()

    if intent == MetadataIntent.ROW_COUNTS:
        tables = _run(config, "List tables", sql_list_tables(), max_rows=40)
        bundle.results.append(tables)
        pairs = _parse_table_rows(tables)[:15]
        count_rows: list[tuple] = []
        for schema, table in pairs:
            step = _run(
                config,
                f"Row count · {schema}.{table}",
                sql_row_count(schema, table),
                max_rows=1,
            )
            if not step.error and step.rows:
                count_rows.append((schema, table, step.rows[0][0]))
            elif step.error:
                count_rows.append((schema, table, f"error: {step.error}"))
        bundle.results.append(
            QueryResult(
                label="Row counts",
                sql="COUNT_BIG(*) per table (template)",
                columns=["schema", "table", "row_count"],
                rows=count_rows,
            )
        )
        bundle.primary_sql = "COUNT_BIG(*) per table"
        return bundle

    sql = resolve_metadata_sql(intent, target_table=plan.target_table)
    # Cap column listing when no table specified (can be huge).
    max_rows = 80 if intent != MetadataIntent.LIST_COLUMNS else (
        200 if plan.target_table else 60
    )
    result = _run(config, intent.value, sql, max_rows=max_rows)
    bundle.results.append(result)
    bundle.primary_sql = result.sql
    return bundle


def execute_understanding_plan(config: SqlConnectionConfig) -> ExecutionBundle:
    """
    Database Understanding workflow (no LLM SQL generation):
    1) List tables  2) List columns  3) Row counts  4) Sample 3 rows
    """
    bundle = ExecutionBundle()

    tables = _run(config, "1. List tables", sql_list_tables(), max_rows=40)
    views = _run(config, "1b. List views", sql_list_views(), max_rows=40)
    columns = _run(config, "2. List columns", sql_list_columns(), max_rows=80)
    bundle.results.extend([tables, views, columns])

    pairs = _parse_table_rows(tables)[:8]
    count_rows: list[tuple] = []
    for schema, table in pairs:
        step = _run(
            config,
            f"3. Row count · {schema}.{table}",
            sql_row_count(schema, table),
            max_rows=1,
        )
        if not step.error and step.rows:
            count_rows.append((schema, table, int(step.rows[0][0])))
        else:
            count_rows.append((schema, table, 0))

    count_rows.sort(key=lambda r: int(r[2]) if isinstance(r[2], int) else 0, reverse=True)
    bundle.results.append(
        QueryResult(
            label="3. Row counts",
            sql="COUNT_BIG(*) per important table",
            columns=["schema", "table", "row_count"],
            rows=count_rows,
        )
    )

    # Sample from top tables by row count (or first tables).
    sample_targets = [(str(s), str(t)) for s, t, _ in count_rows[:4]] or pairs[:4]
    for schema, table in sample_targets:
        sample = _run(
            config,
            f"4. Sample · {schema}.{table}",
            sql_sample_rows(schema, table, 3),
            max_rows=3,
        )
        bundle.results.append(sample)

    bundle.primary_sql = "understanding workflow (templates)"
    return bundle


def execute_validated_sql(
    config: SqlConnectionConfig,
    sql: str,
    *,
    label: str = "Data analysis query",
    max_rows: int = 50,
) -> QueryResult:
    """Validate then execute LLM-generated SQL (Data Analysis path only)."""
    return _run(config, label, sql, max_rows=max_rows)
