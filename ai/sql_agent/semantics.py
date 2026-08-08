"""Semantic schema understanding, Semiconductor Mode mappings, and object routing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from ai.sql_agent.profiler import DatabaseProfile, TableProfile


class TableRole(str, Enum):
    FACT = "Fact Table"
    DIMENSION = "Dimension Table"
    ANALYTICAL_VIEW = "Analytical View"
    LOOKUP = "Lookup Table"
    BRIDGE = "Bridge Table"
    STAGING = "Staging Table"
    UNKNOWN = "Table"


class SemanticTarget(str, Enum):
    """Which warehouse object family should answer the question."""

    KPI_VIEW = "kpi_view"
    SENSOR_FACT = "sensor_fact"
    TIME_DIM = "time_dim"
    GENERAL = "general"


@dataclass
class SemanticRoute:
    target: SemanticTarget
    preferred: list[TableProfile]
    guidance: str
    semiconductor_mode: bool = False
    locked_object: str | None = None  # schema.name when table choice is fixed
    allow_llm_sql: bool = True


# Canonical Semiconductor warehouse objects (hard mappings)
SEMI_KPI_VIEW = "vw_manufacturing_summary"
SEMI_SENSOR_FACT = "fact_sensor_readings"
SEMI_TIME_DIM = "dim_time"

# Keyword → canonical object (Semiconductor Mode).
# Sensor patterns are checked BEFORE KPI so "avg sensor_000 for passed wafers"
# still routes to fact_sensor_readings (not vw_manufacturing_summary).
_KEYWORD_OBJECT_MAP: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\b(sensor[_\s]?\d+|sensor|reading|sample\s+rows?|machine\s+learning|\bml\b|"
            r"prediction|anomaly|root\s+cause|raw\s+sensor|average\s+values?\s+of\s+sensor)\b",
            re.I,
        ),
        SEMI_SENSOR_FACT,
    ),
    (
        re.compile(
            r"\b(passed|failed|yield|production|manufacturing\s+summary|"
            r"pass\s+rate|fail\s+rate|total\s+wafers?|kpi|quality\s+rate)\b",
            re.I,
        ),
        SEMI_KPI_VIEW,
    ),
    (
        re.compile(
            r"\b(date|month|year|trend|daily|monthly|calendar|quarter|week|"
            r"over\s+time|by\s+month|by\s+day)\b",
            re.I,
        ),
        SEMI_TIME_DIM,
    ),
]

_SENSOR_HINT = re.compile(
    r"\b(sensor[_\s]?\d+|sensor|reading_id|compare\s+sensor|root\s+cause|"
    r"machine\s+learning|\bml\b|anomaly|prediction|average\s+values?\s+of\s+sensor)\b",
    re.I,
)
_TIME_HINT = re.compile(
    r"\b(date|month|year|trend|daily|monthly|calendar|quarter|"
    r"over\s+time|by\s+month|dim_time)\b",
    re.I,
)


def find_object(profile: DatabaseProfile, name: str) -> TableProfile | None:
    needle = name.lower().split(".")[-1]
    for tp in profile.views + profile.tables:
        if tp.name.lower() == needle:
            return tp
    return None


def is_semiconductor_mode(profile: DatabaseProfile) -> bool:
    """
    Semiconductor Mode when curated warehouse objects are present.

    Accuracy path: fixed semantic mappings, no free-form table picking for KPIs.
    """
    names = {tp.name.lower() for tp in profile.tables + profile.views}
    canonical = {SEMI_KPI_VIEW, SEMI_SENSOR_FACT, SEMI_TIME_DIM}
    hits = names & canonical
    if SEMI_SENSOR_FACT in names and (
        SEMI_KPI_VIEW in names or SEMI_TIME_DIM in names or len(hits) >= 1
    ):
        return True
    if len(hits) >= 2:
        return True
    # Database name hint
    if "semiconductor" in (profile.database or "").lower() and SEMI_SENSOR_FACT in names:
        return True
    return False


def classify_table_role(tp: TableProfile) -> TableRole:
    name = tp.name.lower()
    if tp.object_type == "VIEW" or name.startswith("vw_") or name.startswith("v_"):
        return TableRole.ANALYTICAL_VIEW
    if name.startswith("fact_") or name.startswith("fct_"):
        return TableRole.FACT
    if name.startswith("dim_") or name.startswith("dimension"):
        return TableRole.DIMENSION
    if name.startswith("lookup_") or name.startswith("lkp_") or name.startswith("ref_"):
        return TableRole.LOOKUP
    if name.startswith("bridge_") or name.startswith("map_"):
        return TableRole.BRIDGE
    if name.startswith("stg_") or name.startswith("staging_") or name.startswith("tmp_"):
        return TableRole.STAGING
    if any(k in name for k in ("time", "date", "calendar")):
        return TableRole.DIMENSION
    if any(k in name for k in ("sensor", "reading", "measurement", "event")):
        return TableRole.FACT
    return TableRole.UNKNOWN


def infer_key_metrics(tp: TableProfile) -> list[str]:
    metrics: list[str] = []
    for col, _dtype in tp.columns:
        lower = col.lower()
        if any(
            token in lower
            for token in (
                "yield",
                "pass",
                "fail",
                "total",
                "count",
                "avg",
                "sum",
                "rate",
                "pct",
                "percent",
                "revenue",
                "amount",
                "sensor",
            )
        ):
            metrics.append(col)
    return metrics[:12]


def infer_important_columns(tp: TableProfile) -> list[str]:
    preferred_tokens = (
        "id",
        "key",
        "target",
        "timestamp",
        "date",
        "time",
        "yield",
        "pass",
        "fail",
        "sensor",
        "wafer",
        "month",
        "year",
    )
    important: list[str] = []
    for col, _ in tp.columns:
        lower = col.lower()
        if any(tok in lower for tok in preferred_tokens):
            important.append(col)
        if len(important) >= 10:
            break
    if not important:
        important = [c for c, _ in tp.columns[:8]]
    return important


def infer_preferred_for(tp: TableProfile, role: TableRole) -> list[str]:
    name = tp.name.lower()
    if role == TableRole.ANALYTICAL_VIEW or name == SEMI_KPI_VIEW:
        return ["Yield", "Passed", "Failed", "Production Summary", "Manufacturing KPIs"]
    if role == TableRole.FACT or name == SEMI_SENSOR_FACT:
        return ["Sensor Analytics", "Machine Learning", "Sample Rows", "Root Cause Analysis"]
    if role == TableRole.DIMENSION or name == SEMI_TIME_DIM:
        return ["Monthly Reports", "Trend Analysis", "Filtering", "Daily Reports"]
    if role == TableRole.LOOKUP:
        return ["Lookups", "Label enrichment"]
    return ["General querying"]


def infer_semantic_purpose(tp: TableProfile, role: TableRole) -> str:
    name = tp.name.lower()
    cols = " ".join(c.lower() for c, _ in tp.columns)

    if name == SEMI_KPI_VIEW or (
        role == TableRole.ANALYTICAL_VIEW
        and any(k in name or k in cols for k in ("yield", "pass", "fail", "manufactur"))
    ):
        return "Aggregated Manufacturing KPIs"
    if role == TableRole.ANALYTICAL_VIEW:
        return "Curated analytical view optimized for business questions and KPIs."
    if name == SEMI_SENSOR_FACT or (
        role == TableRole.FACT and ("sensor" in name or "sensor" in cols)
    ):
        return "Raw Sensor Measurements"
    if role == TableRole.FACT:
        return "Grain-level factual measurements or events for detailed analysis."
    if name == SEMI_TIME_DIM or (
        role == TableRole.DIMENSION and any(k in name for k in ("time", "date", "calendar"))
    ):
        return "Time Dimension"
    if role == TableRole.DIMENSION:
        return "Descriptive dimension attributes used to slice and filter facts."
    if role == TableRole.LOOKUP:
        return "Lookup / reference values supporting enrichment and validation."
    if role == TableRole.BRIDGE:
        return "Bridge table modeling many-to-many relationships."
    if role == TableRole.STAGING:
        return "Staging / intermediate data used in ETL processing."
    return f"Relational {tp.object_type.lower()} with {len(tp.columns)} columns."


def infer_use_cases(tp: TableProfile, role: TableRole) -> list[str]:
    return infer_preferred_for(tp, role)


def enrich_table_semantics(tp: TableProfile, profile: DatabaseProfile) -> None:
    """Populate semantic fields on a TableProfile in place."""
    from ai.sql_agent.metadata_reasoning import primary_keys_for

    role = classify_table_role(tp)
    tp.business_role = role.value
    tp.purpose = infer_semantic_purpose(tp, role)
    tp.key_metrics = infer_key_metrics(tp)
    tp.important_columns = infer_important_columns(tp)
    tp.use_cases = infer_use_cases(tp, role)
    tp.preferred_for = infer_preferred_for(tp, role)
    tp.primary_key_columns = primary_keys_for(profile, tp.schema, tp.name)
    tp.relationships = _relationships_for(profile, tp.schema, tp.name)


def enrich_profile_semantics(profile: DatabaseProfile) -> None:
    """Classify every table/view and attach semantic metadata."""
    profile.semiconductor_mode = is_semiconductor_mode(profile)
    for tp in profile.tables + profile.views:
        enrich_table_semantics(tp, profile)


def objects_by_role(profile: DatabaseProfile, role: TableRole) -> list[TableProfile]:
    return [
        tp
        for tp in profile.tables + profile.views
        if (tp.business_role or classify_table_role(tp).value) == role.value
    ]


def pick_kpi_analytical_view(profile: DatabaseProfile) -> TableProfile | None:
    """Prefer manufacturing/summary analytical views for KPI questions."""
    # Semiconductor Mode: hard map
    if is_semiconductor_mode(profile):
        locked = find_object(profile, SEMI_KPI_VIEW)
        if locked:
            return locked

    views = objects_by_role(profile, TableRole.ANALYTICAL_VIEW)
    if not views:
        views = list(profile.views)

    def score(tp: TableProfile) -> tuple[int, int]:
        name = tp.name.lower()
        cols = " ".join(c.lower() for c, _ in tp.columns)
        points = 0
        if "manufactur" in name or "summary" in name or "kpi" in name:
            points += 5
        if any(k in name or k in cols for k in ("yield", "pass", "fail", "wafer")):
            points += 4
        if tp.name.lower().startswith("vw_"):
            points += 2
        return (points, len(tp.columns))

    ranked = sorted(views, key=score, reverse=True)
    if ranked and score(ranked[0])[0] > 0:
        return ranked[0]
    return ranked[0] if ranked else None


def pick_sensor_fact(profile: DatabaseProfile) -> TableProfile | None:
    if is_semiconductor_mode(profile):
        locked = find_object(profile, SEMI_SENSOR_FACT)
        if locked:
            return locked

    facts = objects_by_role(profile, TableRole.FACT)
    sensor_facts = [
        t
        for t in facts
        if "sensor" in t.name.lower()
        or any("sensor" in c.lower() for c, _ in t.columns)
    ]
    if sensor_facts:
        return max(sensor_facts, key=lambda t: t.row_count or 0)
    if facts:
        return max(facts, key=lambda t: t.row_count or 0)
    return None


def pick_time_dimension(profile: DatabaseProfile) -> TableProfile | None:
    if is_semiconductor_mode(profile):
        locked = find_object(profile, SEMI_TIME_DIM)
        if locked:
            return locked

    dims = objects_by_role(profile, TableRole.DIMENSION)
    for tp in dims:
        if any(k in tp.name.lower() for k in ("time", "date", "calendar")):
            return tp
    return dims[0] if dims else None


def resolve_keyword_object(profile: DatabaseProfile, question: str) -> TableProfile | None:
    """Map question keywords to a canonical Semiconductor object when present."""
    for pattern, object_name in _KEYWORD_OBJECT_MAP:
        if pattern.search(question):
            found = find_object(profile, object_name)
            if found:
                return found
    return None


def classify_semantic_target(question: str, *, is_kpi: bool = False) -> SemanticTarget:
    if is_kpi:
        return SemanticTarget.KPI_VIEW
    if _SENSOR_HINT.search(question) and not _TIME_HINT.search(question):
        return SemanticTarget.SENSOR_FACT
    if _TIME_HINT.search(question):
        return SemanticTarget.TIME_DIM
    if _SENSOR_HINT.search(question):
        return SemanticTarget.SENSOR_FACT
    return SemanticTarget.GENERAL


def route_question(
    profile: DatabaseProfile,
    question: str,
    *,
    is_kpi: bool = False,
) -> SemanticRoute:
    """
    WHAT was classified upstream → WHICH object answers it.

    Semiconductor Mode: hard-lock to curated objects (no LLM table shopping).
    Generic Mode: infer from roles / naming.
    """
    semi = is_semiconductor_mode(profile)
    target = classify_semantic_target(question, is_kpi=is_kpi)

    # Keyword override in Semiconductor Mode (except pure KPI already set)
    if semi and not is_kpi:
        mapped = resolve_keyword_object(profile, question)
        if mapped:
            name = mapped.name.lower()
            if name == SEMI_KPI_VIEW:
                target = SemanticTarget.KPI_VIEW
            elif name == SEMI_SENSOR_FACT:
                target = SemanticTarget.SENSOR_FACT
            elif name == SEMI_TIME_DIM:
                target = SemanticTarget.TIME_DIM

    preferred: list[TableProfile] = []
    guidance = ""
    locked: str | None = None
    allow_llm = True

    if target == SemanticTarget.KPI_VIEW:
        view = pick_kpi_analytical_view(profile)
        if view:
            preferred = [view]
            locked = f"{view.schema}.{view.name}"
            allow_llm = False if semi else True
            guidance = (
                f"KPI question: MUST query analytical view `{locked}` "
                f"with dataset-level aggregation (SUM) when the view has "
                f"multiple rows. Do NOT use TOP 1. Do NOT return a single "
                f"day/month grain row as the overall total. "
                f"Do NOT aggregate `{SEMI_SENSOR_FACT}` when this view exists."
            )
        else:
            fact = pick_sensor_fact(profile)
            preferred = [fact] if fact else []
            guidance = (
                "KPI question: no analytical view found; carefully aggregate "
                "from the preferred fact table only."
            )
    elif target == SemanticTarget.SENSOR_FACT:
        fact = pick_sensor_fact(profile)
        preferred = [fact] if fact else []
        if fact:
            locked = f"{fact.schema}.{fact.name}"
            if semi:
                allow_llm = True  # may need column selection, but object is locked
            guidance = (
                f"Sensor / ML question: use ONLY fact table `{locked}` "
                f"for raw readings. Do not use KPI views for sensor grain."
            )
        else:
            guidance = "Sensor question: use the most relevant fact table."
    elif target == SemanticTarget.TIME_DIM:
        dim = pick_time_dimension(profile)
        view = pick_kpi_analytical_view(profile)
        preferred = [x for x in (view, dim) if x]
        if dim:
            locked = f"{dim.schema}.{dim.name}"
        guidance = (
            "Time question: prefer analytical view for KPI trends; "
            f"use `{SEMI_TIME_DIM}` (or time dimension) for date breakdowns."
            if semi
            else "Time question: use time dimension + analytical views for KPI trends."
        )
    else:
        view = pick_kpi_analytical_view(profile)
        fact = pick_sensor_fact(profile)
        preferred = [x for x in (view, fact) if x]
        guidance = (
            "General analytics: prefer curated analytical views for KPIs; "
            "use fact tables only for grain-level detail."
        )
        if semi and preferred:
            locked = f"{preferred[0].schema}.{preferred[0].name}"

    return SemanticRoute(
        target=target,
        preferred=preferred,
        guidance=guidance,
        semiconductor_mode=semi,
        locked_object=locked,
        allow_llm_sql=allow_llm,
    )


def _quoted(schema: str, name: str) -> str:
    return f"[{schema}].[{name}]"


def try_deterministic_kpi_sql(
    profile: DatabaseProfile,
    question: str,
    *,
    config=None,
    force_aggregate: bool = False,
) -> str | None:
    """
    Build dataset-level KPI SQL (SUM when the view is periodic).

    Never uses TOP 1. Delegates to the KPI router.
    """
    from ai.sql_agent.kpi import build_kpi_sql

    built = build_kpi_sql(
        profile, question, config=config, force_aggregate=force_aggregate
    )
    if built is None:
        return None
    sql, _source, _grain = built
    return sql


def locked_object_schema_text(tp: TableProfile) -> str:
    """Schema snippet for a single locked object — LLM cannot see other tables."""
    role = tp.business_role or classify_table_role(tp).value
    lines = [
        f"# Locked object (MUST use only this)",
        f"## {tp.schema}.{tp.name} ({tp.object_type})",
        f"- Business Role: {role}",
        f"- Purpose: {tp.purpose or ''}",
    ]
    if getattr(tp, "preferred_for", None):
        lines.append(f"- Preferred For: {', '.join(tp.preferred_for)}")
    if tp.key_metrics:
        lines.append(f"- Key Metrics: {', '.join(tp.key_metrics)}")
    if tp.important_columns:
        lines.append(f"- Important Columns: {', '.join(tp.important_columns)}")
    col_bits = [f"{n}:{t}" for n, t in tp.columns[:40]]
    if len(tp.columns) > 40:
        col_bits.append(f"+{len(tp.columns) - 40} more")
    lines.append(f"- Columns: {', '.join(col_bits)}")
    lines.append("")
    lines.append("Rules: Query ONLY this object. Do not reference other tables/views.")
    return "\n".join(lines)


def semantic_profile_text(profile: DatabaseProfile, *, max_chars: int = 12_000) -> str:
    """Human/LLM readable semantic profile for every object."""
    mode = "Semiconductor Mode" if is_semiconductor_mode(profile) else "Generic SQL Mode"
    lines = [
        f"# Semantic Profile · {profile.database} · {mode}",
        "",
        "Routing rules:",
        f"- KPI (passed/failed/yield/production) → `{SEMI_KPI_VIEW}` / Analytical Views",
        f"- Sensor / ML / sample rows → `{SEMI_SENSOR_FACT}` / Fact Tables",
        f"- Date / month / trend → `{SEMI_TIME_DIM}` / Time Dimension",
        "- Never answer KPIs from TOP 1 of raw fact tables when a view exists",
        "",
    ]
    for tp in profile.views + profile.tables:
        role = tp.business_role or classify_table_role(tp).value
        lines.append(f"## {tp.schema}.{tp.name} ({tp.object_type})")
        lines.append(f"- Business Role: {role}")
        lines.append(
            f"- Purpose: {tp.purpose or infer_semantic_purpose(tp, classify_table_role(tp))}"
        )
        preferred = getattr(tp, "preferred_for", None) or tp.use_cases
        if preferred:
            lines.append(f"- Preferred For: {', '.join(preferred)}")
        if tp.key_metrics:
            lines.append(f"- Key Metrics: {', '.join(tp.key_metrics)}")
        if tp.important_columns:
            lines.append(f"- Important Columns: {', '.join(tp.important_columns)}")
        if tp.primary_key_columns:
            lines.append(f"- Primary Keys: {', '.join(tp.primary_key_columns)}")
        if tp.relationships:
            lines.append(f"- Relationships: {'; '.join(tp.relationships[:5])}")
        col_bits = [f"{n}:{t}" for n, t in tp.columns[:20]]
        if len(tp.columns) > 20:
            col_bits.append(f"+{len(tp.columns) - 20} more")
        lines.append(f"- Columns: {', '.join(col_bits)}")
        if tp.row_count is not None:
            lines.append(f"- Rows: {tp.row_count}")
        lines.append("")

    text = "\n".join(lines)
    if len(text) > max_chars:
        return text[: max_chars - 40] + "\n...(semantic profile truncated)"
    return text


def _relationships_for(profile: DatabaseProfile, schema: str, table: str) -> list[str]:
    rels: list[str] = []
    for row in profile.foreign_keys:
        if len(row) >= 6:
            if str(row[0]).lower() == schema.lower() and str(row[1]).lower() == table.lower():
                rels.append(f"{row[2]} → {row[3]}.{row[4]}.{row[5]}")
            if str(row[3]).lower() == schema.lower() and str(row[4]).lower() == table.lower():
                rels.append(f"{row[0]}.{row[1]}.{row[2]} → {row[5]}")
    return rels
