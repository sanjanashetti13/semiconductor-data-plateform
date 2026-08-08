"""KPI router — dataset-level business metrics (never row-level TOP 1)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ai.sql_agent.profiler import DatabaseProfile, TableProfile
from ai.sql_agent.session_store import SqlConnectionConfig, execute_select

logger = logging.getLogger(__name__)


class KpiMetric(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    YIELD = "yield"
    TOTAL = "total"
    SUMMARY = "summary"


class ViewGrain(str, Enum):
    SUMMARY = "summary"  # single overall row
    PERIODIC = "periodic"  # daily/monthly grain — must SUM


@dataclass
class KpiColumnMap:
    total: str | None = None
    passed: str | None = None
    failed: str | None = None
    yield_col: str | None = None


@dataclass
class KpiTotals:
    total_wafers: float | None = None
    passed: float | None = None
    failed: float | None = None
    yield_percentage: float | None = None
    sql: str = ""
    source: str = ""
    grain: ViewGrain = ViewGrain.PERIODIC
    validated: bool = False


_KPI_ROUTE = re.compile(
    r"\b("
    r"how\s+many\s+(passed|failed|pass|fail|wafers?)|"
    r"number\s+of\s+(passed|failed|pass|fail|wafers?)|"
    r"overall\s+yield|yield\s*(%|percentage|percent|rate)\b|"
    r"^passed(\s+wafers?)?\s*\??$|"
    r"^failed(\s+wafers?)?\s*\??$|"
    r"^yield\s*\??$|"
    r"production\s+summary|overall\s+summary|manufacturing\s+summary|"
    r"total\s+wafers?|total\s+production|overall\s+production|"
    r"pass\s+(rate|percentage|percent)|"
    r"fail(ure)?\s+(rate|percentage|percent)"
    r")\b",
    re.IGNORECASE,
)

_REASONING_BLOCK = re.compile(
    r"\b(influence|affect|factors?|reduce\s+failures?|improve\s+yield|"
    r"recommend|root\s+cause|how\s+would|how\s+can|how\s+to)\b",
    re.I,
)


_SENSOR_COLUMN = re.compile(
    r"\b(sensor[_\s]?\d+|sensor\s*\d+)\b",
    re.I,
)
_SENSOR_ANALYTICS = re.compile(
    r"\b("
    r"average\s+values?\s+of\s+sensor|avg\s*\(\s*sensor|"
    r"sensor[_\s]?\d+|highest\s+average|lowest\s+average|"
    r"which\s+sensor|compare\s+sensors?"
    r")\b",
    re.I,
)


def is_sensor_analytics_question(question: str) -> bool:
    """True when the ask is about sensor columns / averages — not manufacturing KPIs."""
    q = question or ""
    return bool(_SENSOR_COLUMN.search(q) or _SENSOR_ANALYTICS.search(q))


def is_kpi_route(question: str) -> bool:
    """True when the question must use the KPI handler (no free-form LLM SQL)."""
    q = question or ""
    if _REASONING_BLOCK.search(q):
        return False
    # Sensor analytics must never be answered from vw_manufacturing_summary KPIs.
    if is_sensor_analytics_question(q):
        return False
    return bool(_KPI_ROUTE.search(q))


_METRIC_PASSED = re.compile(
    r"\b(how\s+many\s+)?pass(ed|es)?(\s+wafers?)?\b", re.I
)
_METRIC_FAILED = re.compile(
    r"\b(how\s+many\s+)?fail(ed|ures?)?(\s+wafers?)?\b", re.I
)
_METRIC_YIELD = re.compile(
    r"\b(overall\s+)?yield\b|pass\s+(rate|percentage|percent)|fail(ure)?\s+(rate|percentage)",
    re.I,
)
_METRIC_TOTAL = re.compile(
    r"\b(total\s+(wafers?|production)|overall\s+production|how\s+many\s+wafers?)\b",
    re.I,
)
_METRIC_SUMMARY = re.compile(
    r"\b(production|manufacturing|overall)\s+summary\b|\bkpi\b",
    re.I,
)


def classify_kpi_metric(question: str) -> KpiMetric:
    q = question.lower()
    if _METRIC_SUMMARY.search(q):
        return KpiMetric.SUMMARY
    if _METRIC_FAILED.search(q) and not _METRIC_PASSED.search(q):
        return KpiMetric.FAILED
    if _METRIC_PASSED.search(q) and not _METRIC_FAILED.search(q):
        return KpiMetric.PASSED
    if _METRIC_YIELD.search(q):
        return KpiMetric.YIELD
    if _METRIC_TOTAL.search(q):
        return KpiMetric.TOTAL
    if _METRIC_PASSED.search(q):
        return KpiMetric.PASSED
    if _METRIC_FAILED.search(q):
        return KpiMetric.FAILED
    return KpiMetric.SUMMARY


def _pick_col(col_map: dict[str, str], *candidates: str) -> str | None:
    for cand in candidates:
        if cand in col_map:
            return col_map[cand]
    for lower, original in col_map.items():
        if any(cand in lower for cand in candidates):
            return original
    return None


def map_kpi_columns(tp: TableProfile) -> KpiColumnMap:
    col_map = {c.lower(): c for c, _ in tp.columns}
    return KpiColumnMap(
        total=_pick_col(
            col_map, "total_wafers", "wafer_count", "total", "total_count", "n_wafers"
        ),
        passed=_pick_col(
            col_map, "passed", "pass_count", "total_passed", "pass", "num_passed"
        ),
        failed=_pick_col(
            col_map, "failed", "fail_count", "total_failed", "fail", "num_failed"
        ),
        yield_col=_pick_col(
            col_map,
            "yield_percentage",
            "yield_pct",
            "yield_percent",
            "overall_yield",
            "yield",
            "pass_rate",
        ),
    )


def quoted(schema: str, name: str) -> str:
    return f"[{schema}].[{name}]"


def detect_view_grain(
    config: SqlConnectionConfig | None,
    tp: TableProfile,
) -> ViewGrain:
    """
    COUNT(*) == 1 → summary view (use row as-is).
    Otherwise → periodic grain (must SUM for overall KPIs).
    """
    cached = getattr(tp, "kpi_grain", None)
    if cached in (ViewGrain.SUMMARY.value, ViewGrain.PERIODIC.value, ViewGrain.SUMMARY, ViewGrain.PERIODIC):
        if isinstance(cached, ViewGrain):
            return cached
        return ViewGrain(cached)

    if tp.row_count == 1:
        tp.kpi_grain = ViewGrain.SUMMARY.value  # type: ignore[attr-defined]
        return ViewGrain.SUMMARY
    if tp.row_count is not None and tp.row_count > 1:
        tp.kpi_grain = ViewGrain.PERIODIC.value  # type: ignore[attr-defined]
        return ViewGrain.PERIODIC

    if config is None:
        # Unknown — prefer aggregation (safer for overall totals)
        return ViewGrain.PERIODIC

    try:
        sql = f"SELECT COUNT_BIG(*) AS cnt FROM {quoted(tp.schema, tp.name)}"
        cols, rows = execute_select(config, sql, max_rows=1)
        del cols
        count = int(rows[0][0]) if rows and rows[0] and rows[0][0] is not None else 0
        tp.row_count = count
        grain = ViewGrain.SUMMARY if count == 1 else ViewGrain.PERIODIC
        tp.kpi_grain = grain.value  # type: ignore[attr-defined]
        logger.info(
            "KPI view grain %s.%s → %s (rows=%s)",
            tp.schema,
            tp.name,
            grain.value,
            count,
        )
        return grain
    except Exception as exc:  # noqa: BLE001
        logger.warning("KPI grain detect failed for %s.%s: %s", tp.schema, tp.name, exc)
        return ViewGrain.PERIODIC


def build_aggregated_kpi_sql(tp: TableProfile, cols: KpiColumnMap) -> str:
    """Dataset-level SUM over a periodic KPI view."""
    full = quoted(tp.schema, tp.name)
    parts: list[str] = []
    if cols.total:
        parts.append(f"SUM([{cols.total}]) AS total_wafers")
    if cols.passed:
        parts.append(f"SUM([{cols.passed}]) AS passed")
    if cols.failed:
        parts.append(f"SUM([{cols.failed}]) AS failed")

    if cols.passed and cols.total:
        parts.append(
            "ROUND(100.0 * SUM([{p}]) / NULLIF(SUM([{t}]), 0), 2) AS yield_percentage".format(
                p=cols.passed, t=cols.total
            )
        )
    elif cols.passed and cols.failed:
        parts.append(
            "ROUND(100.0 * SUM([{p}]) / NULLIF(SUM([{p}]) + SUM([{f}]), 0), 2) "
            "AS yield_percentage".format(p=cols.passed, f=cols.failed)
        )
    elif cols.yield_col:
        # Last resort: weighted average is unavailable; AVG is wrong for yields.
        # Prefer recomputing from passed/total when possible; else omit.
        pass

    if not parts:
        # No recognizable KPI columns — still force a single aggregated probe row
        return f"SELECT COUNT(*) AS row_count FROM {full}"

    return f"SELECT\n    " + ",\n    ".join(parts) + f"\nFROM {full}"


def build_summary_row_sql(tp: TableProfile, cols: KpiColumnMap) -> str:
    """Single-row summary view — select KPI columns directly (no TOP 1)."""
    full = quoted(tp.schema, tp.name)
    selected: list[str] = []
    aliases = [
        (cols.total, "total_wafers"),
        (cols.passed, "passed"),
        (cols.failed, "failed"),
        (cols.yield_col, "yield_percentage"),
    ]
    for original, alias in aliases:
        if original:
            if original.lower() == alias.lower():
                selected.append(f"[{original}]")
            else:
                selected.append(f"[{original}] AS {alias}")
    if not selected:
        return f"SELECT * FROM {full}"
    return f"SELECT {', '.join(selected)} FROM {full}"


def build_fact_kpi_sql(tp: TableProfile) -> str | None:
    """Fallback: aggregate pass/fail from a fact table with a target column."""
    col_map = {c.lower(): c for c, _ in tp.columns}
    target = _pick_col(col_map, "target", "label", "class", "outcome", "result")
    if not target:
        return None
    full = quoted(tp.schema, tp.name)
    # Common conventions: -1/0 = pass, 1 = fail (SECOM and similar)
    return f"""
SELECT
    COUNT(*) AS total_wafers,
    SUM(CASE WHEN [{target}] IN (-1, 0) THEN 1 ELSE 0 END) AS passed,
    SUM(CASE WHEN [{target}] IN (1) THEN 1 ELSE 0 END) AS failed,
    ROUND(
        100.0 * SUM(CASE WHEN [{target}] IN (-1, 0) THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        2
    ) AS yield_percentage
FROM {full}
""".strip()


def pick_kpi_source(profile: DatabaseProfile) -> TableProfile | None:
    """Prefer analytical KPI view; else infer from semantic profile."""
    from ai.sql_agent.semantics import pick_kpi_analytical_view, pick_sensor_fact

    view = pick_kpi_analytical_view(profile)
    if view:
        return view
    return pick_sensor_fact(profile)


def build_kpi_sql(
    profile: DatabaseProfile,
    question: str,
    *,
    config: SqlConnectionConfig | None = None,
    force_aggregate: bool = False,
) -> tuple[str, TableProfile, ViewGrain] | None:
    """
    Build deterministic dataset-level KPI SQL.

    Never emits TOP 1 / LIMIT 1.
    """
    source = pick_kpi_source(profile)
    if source is None:
        return None

    cols = map_kpi_columns(source)
    has_kpi_cols = bool(cols.passed or cols.failed or cols.total or cols.yield_col)

    if source.object_type == "VIEW" or has_kpi_cols:
        grain = (
            ViewGrain.PERIODIC
            if force_aggregate
            else detect_view_grain(config, source)
        )
        if grain == ViewGrain.SUMMARY and not force_aggregate:
            sql = build_summary_row_sql(source, cols)
        else:
            sql = build_aggregated_kpi_sql(source, cols)
        if "TOP" in sql.upper().split() or "TOP(" in sql.upper().replace(" ", ""):
            raise RuntimeError("KPI SQL must never use TOP 1")
        return sql, source, grain

    # Fact-table fallback
    fact_sql = build_fact_kpi_sql(source)
    if fact_sql:
        return fact_sql, source, ViewGrain.SUMMARY
    return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_kpi_result(columns: list[str], rows: list[tuple]) -> KpiTotals:
    """Parse a single aggregated KPI result row (or SUM multiple rows in Python)."""
    if not columns:
        return KpiTotals()

    lower = [c.lower() for c in columns]

    def col_index(*names: str) -> int | None:
        for name in names:
            if name in lower:
                return lower.index(name)
        for i, c in enumerate(lower):
            if any(name in c for name in names):
                return i
        return None

    idx_total = col_index("total_wafers", "total", "wafer_count")
    idx_passed = col_index("passed", "pass_count", "pass")
    idx_failed = col_index("failed", "fail_count", "fail")
    idx_yield = col_index("yield_percentage", "yield_pct", "yield", "overall_yield")

    if len(rows) > 1:
        # Safety net: aggregate in Python if SQL returned grain rows
        logger.warning(
            "KPI query returned %s rows — aggregating in Python (expected 1)",
            len(rows),
        )
        totals = KpiTotals(grain=ViewGrain.PERIODIC)
        if idx_total is not None:
            totals.total_wafers = sum(
                _to_float(r[idx_total]) or 0 for r in rows if len(r) > idx_total
            )
        if idx_passed is not None:
            totals.passed = sum(
                _to_float(r[idx_passed]) or 0 for r in rows if len(r) > idx_passed
            )
        if idx_failed is not None:
            totals.failed = sum(
                _to_float(r[idx_failed]) or 0 for r in rows if len(r) > idx_failed
            )
        if totals.passed is not None and totals.total_wafers:
            totals.yield_percentage = round(
                100.0 * totals.passed / totals.total_wafers, 2
            )
        elif totals.passed is not None and totals.failed is not None:
            denom = totals.passed + totals.failed
            if denom:
                totals.yield_percentage = round(100.0 * totals.passed / denom, 2)
        return totals

    if not rows:
        return KpiTotals()

    row = rows[0]
    totals = KpiTotals(grain=ViewGrain.SUMMARY)
    if idx_total is not None and idx_total < len(row):
        totals.total_wafers = _to_float(row[idx_total])
    if idx_passed is not None and idx_passed < len(row):
        totals.passed = _to_float(row[idx_passed])
    if idx_failed is not None and idx_failed < len(row):
        totals.failed = _to_float(row[idx_failed])
    if idx_yield is not None and idx_yield < len(row):
        totals.yield_percentage = _to_float(row[idx_yield])

    # Recompute yield when components exist
    if totals.passed is not None and totals.total_wafers:
        totals.yield_percentage = round(100.0 * totals.passed / totals.total_wafers, 2)
    elif (
        totals.yield_percentage is None
        and totals.passed is not None
        and totals.failed is not None
    ):
        denom = totals.passed + totals.failed
        if denom:
            totals.yield_percentage = round(100.0 * totals.passed / denom, 2)
            if totals.total_wafers is None:
                totals.total_wafers = denom

    return totals


def validate_kpi_totals(
    totals: KpiTotals,
    *,
    fact_row_count: int | None = None,
) -> tuple[bool, str]:
    """
    Return (ok, reason). Failures should trigger SUM() retry.
    """
    if totals.passed is None and totals.failed is None and totals.total_wafers is None:
        return False, "empty KPI result"

    if (
        totals.passed is not None
        and totals.failed is not None
        and totals.total_wafers is not None
    ):
        expected = totals.passed + totals.failed
        if abs(expected - totals.total_wafers) > 0.5:
            return (
                False,
                f"passed+failed ({expected}) != total_wafers ({totals.total_wafers})",
            )

    if (
        fact_row_count
        and fact_row_count > 1000
        and totals.passed is not None
        and totals.passed < 100
        and (totals.total_wafers is None or totals.total_wafers < 200)
    ):
        return (
            False,
            f"suspiciously low passed={totals.passed} vs fact rows={fact_row_count}",
        )

    return True, "ok"


def format_kpi_answer(question: str, totals: KpiTotals) -> str:
    """Concise Copilot-style KPI answer — no paragraphs."""
    metric = classify_kpi_metric(question)

    def fmt_int(value: float | None) -> str:
        if value is None:
            return "n/a"
        return f"{int(round(value)):,}"

    def fmt_pct(value: float | None) -> str:
        if value is None:
            return "n/a"
        return f"{value:.2f}%"

    if metric == KpiMetric.PASSED:
        return f"Passed Wafers: {fmt_int(totals.passed)}"
    if metric == KpiMetric.FAILED:
        return f"Failed Wafers: {fmt_int(totals.failed)}"
    if metric == KpiMetric.YIELD:
        return f"Overall Yield: {fmt_pct(totals.yield_percentage)}"
    if metric == KpiMetric.TOTAL:
        return f"Total Production: {fmt_int(totals.total_wafers)}"

    # Summary
    lines = [
        f"Total Wafers: {fmt_int(totals.total_wafers)}",
        f"Passed: {fmt_int(totals.passed)}",
        f"Failed: {fmt_int(totals.failed)}",
        f"Yield: {fmt_pct(totals.yield_percentage)}",
    ]
    return "\n".join(lines)


def execute_kpi_query(
    config: SqlConnectionConfig,
    profile: DatabaseProfile,
    question: str,
) -> KpiTotals:
    """
    Run KPI SQL with validation + automatic SUM() retry.

    Never returns a random grain row as an overall total.
    """
    from ai.sql_agent.semantics import pick_sensor_fact

    built = build_kpi_sql(profile, question, config=config, force_aggregate=False)
    if built is None:
        raise RuntimeError("No KPI source table/view found in the semantic profile.")

    sql, source, grain = built
    cols, rows = execute_select(config, sql, max_rows=500)
    totals = parse_kpi_result(cols, rows)
    totals.sql = sql
    totals.source = f"{source.schema}.{source.name}"
    totals.grain = grain

    fact = pick_sensor_fact(profile)
    fact_rows = fact.row_count if fact else None
    ok, reason = validate_kpi_totals(totals, fact_row_count=fact_rows)

    if not ok or len(rows) > 1:
        logger.warning(
            "KPI validation failed (%s); retrying with SUM() aggregation",
            reason if not ok else f"multi-row result ({len(rows)})",
        )
        rebuilt = build_kpi_sql(
            profile, question, config=config, force_aggregate=True
        )
        if rebuilt is None:
            raise RuntimeError("KPI aggregation retry could not build SQL.")
        sql2, source2, grain2 = rebuilt
        cols2, rows2 = execute_select(config, sql2, max_rows=5)
        totals = parse_kpi_result(cols2, rows2)
        totals.sql = sql2
        totals.source = f"{source2.schema}.{source2.name}"
        totals.grain = grain2
        ok2, reason2 = validate_kpi_totals(totals, fact_row_count=fact_rows)
        totals.validated = ok2
        if not ok2:
            logger.warning("KPI still invalid after SUM retry: %s", reason2)
        return totals

    totals.validated = True
    return totals
