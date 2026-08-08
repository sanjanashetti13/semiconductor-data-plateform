"""Complete schema knowledge model — business meaning of every object."""

from __future__ import annotations

from dataclasses import dataclass, field

from ai.sql_agent.profiler import DatabaseProfile, TableProfile
from ai.sql_agent.semantics import (
    classify_table_role,
    infer_preferred_for,
    infer_semantic_purpose,
    is_semiconductor_mode,
)


@dataclass
class ObjectKnowledge:
    """Semantic knowledge card for one table or view."""

    name: str
    full_name: str
    object_type: str
    business_role: str
    purpose: str
    main_columns: list[str] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)
    typical_usage: list[str] = field(default_factory=list)
    key_metrics: list[str] = field(default_factory=list)
    row_count: int | None = None


@dataclass
class SchemaKnowledgeModel:
    """Whole-database semantic model used before answering."""

    database: str
    semiconductor_mode: bool = False
    domain: str = ""
    purpose: str = ""
    objects: list[ObjectKnowledge] = field(default_factory=list)
    analytics_use_cases: list[str] = field(default_factory=list)
    ai_opportunities: list[str] = field(default_factory=list)

    @property
    def object_count(self) -> int:
        return len(self.objects)


def _card_for(tp: TableProfile) -> ObjectKnowledge:
    role = tp.business_role or classify_table_role(tp).value
    purpose = tp.purpose or infer_semantic_purpose(tp, classify_table_role(tp))
    usage = list(tp.preferred_for or tp.use_cases or infer_preferred_for(tp, classify_table_role(tp)))
    main = list(tp.important_columns or [c for c, _ in tp.columns[:10]])
    return ObjectKnowledge(
        name=tp.name,
        full_name=f"{tp.schema}.{tp.name}",
        object_type=tp.object_type,
        business_role=role,
        purpose=purpose,
        main_columns=main[:12],
        relationships=list(tp.relationships or [])[:8],
        typical_usage=usage[:6],
        key_metrics=list(tp.key_metrics or [])[:8],
        row_count=tp.row_count,
    )


def _infer_domain(profile: DatabaseProfile, objects: list[ObjectKnowledge]) -> str:
    blob = " ".join(
        f"{o.name} {o.purpose} {' '.join(o.main_columns)} {' '.join(o.typical_usage)}"
        for o in objects
    ).lower()
    if is_semiconductor_mode(profile) or any(
        k in blob for k in ("wafer", "sensor", "yield", "secom", "manufactur")
    ):
        return (
            "Semiconductor manufacturing intelligence — wafer process sensors, "
            "pass/fail quality outcomes, and production KPIs."
        )
    if any(k in blob for k in ("order", "customer", "revenue", "sales")):
        return "Commercial / transactional analytics."
    if any(k in blob for k in ("patient", "claim", "clinical")):
        return "Healthcare / clinical operations analytics."
    return (
        f"Enterprise analytics database with {profile.table_count} tables "
        f"and {profile.view_count} views."
    )


def _infer_purpose(profile: DatabaseProfile, objects: list[ObjectKnowledge]) -> str:
    roles = {o.business_role for o in objects}
    has_view = any(o.object_type == "VIEW" or "Analytical" in o.business_role for o in objects)
    has_fact = any("Fact" in o.business_role for o in objects)
    if is_semiconductor_mode(profile):
        return (
            "Support manufacturing quality and yield analysis: monitor sensor signals, "
            "track pass/fail outcomes, and publish curated KPIs for operations and leadership."
        )
    parts = ["Store and analyze operational data"]
    if has_fact:
        parts.append("at grain-level fact detail")
    if has_view:
        parts.append("with curated analytical views for business KPIs")
    if "Dimension Table" in roles:
        parts.append("and descriptive dimensions for slicing/trends")
    return "; ".join(parts) + "."


def _use_cases(profile: DatabaseProfile, objects: list[ObjectKnowledge]) -> list[str]:
    cases: list[str] = []
    names = {o.name.lower() for o in objects}
    if any("manufactur" in n or "summary" in n or n.startswith("vw_") for n in names):
        cases.extend(
            [
                "Report overall passed / failed / yield KPIs",
                "Track production summary trends over time",
            ]
        )
    if any("sensor" in n or "fact_" in n for n in names):
        cases.extend(
            [
                "Compare sensor readings for pass vs fail populations",
                "Investigate root-cause signals linked to failures",
            ]
        )
    if any("time" in n or "date" in n or n.startswith("dim_") for n in names):
        cases.append("Slice KPIs by day / month / year using the time dimension")
    if not cases:
        cases = [
            "Explore table purposes and row volumes",
            "Ask for sample rows from primary fact tables",
            "Compute counts, averages, and top-N rankings",
        ]
    # Deduplicate
    seen: set[str] = set()
    out: list[str] = []
    for c in cases:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out[:8]


def _ai_opportunities(profile: DatabaseProfile, objects: list[ObjectKnowledge]) -> list[str]:
    blob = " ".join(o.name.lower() + " " + " ".join(o.main_columns).lower() for o in objects)
    ops: list[str] = []
    if "sensor" in blob or "fact_sensor" in blob:
        ops.extend(
            [
                "Train failure-prediction models on high-dimensional sensor features",
                "Rank sensors that most differentiate pass vs fail wafers",
                "Detect process drift / anomalies before yield drops",
            ]
        )
    if "yield" in blob or "pass" in blob or "fail" in blob:
        ops.append("Recommend process interventions when yield declines")
    if not ops:
        ops = [
            "Automate catalog Q&A over the semantic profile",
            "Generate governed KPI SQL from natural language",
            "Surface unusual trends for analyst review",
        ]
    return ops[:6]


def build_schema_knowledge(profile: DatabaseProfile) -> SchemaKnowledgeModel:
    """Build a complete knowledge model covering every table and view."""
    objects = [_card_for(tp) for tp in list(profile.tables) + list(profile.views)]
    model = SchemaKnowledgeModel(
        database=profile.database,
        semiconductor_mode=is_semiconductor_mode(profile),
        objects=objects,
    )
    model.domain = _infer_domain(profile, objects)
    model.purpose = _infer_purpose(profile, objects)
    model.analytics_use_cases = _use_cases(profile, objects)
    model.ai_opportunities = _ai_opportunities(profile, objects)
    return model


def knowledge_model_to_text(model: SchemaKnowledgeModel, *, max_chars: int = 14_000) -> str:
    """Serialize the full knowledge model for LLM reasoning (all objects)."""
    lines = [
        f"# Schema Knowledge Model · {model.database}",
        f"Mode: {'Semiconductor' if model.semiconductor_mode else 'Generic'}",
        f"Objects: {model.object_count}",
        "",
        "## Database Purpose",
        model.purpose,
        "",
        "## Business Domain",
        model.domain,
        "",
        "## Analytics Use Cases",
    ]
    for u in model.analytics_use_cases:
        lines.append(f"- {u}")
    lines.extend(["", "## AI Opportunities"])
    for a in model.ai_opportunities:
        lines.append(f"- {a}")
    lines.extend(["", "## Objects (complete catalog — do not omit any)"])

    for obj in model.objects:
        rows = f"{obj.row_count:,}" if isinstance(obj.row_count, int) else "Unknown"
        lines.append("")
        lines.append(f"### {obj.full_name}")
        lines.append(f"- Name: {obj.full_name}")
        lines.append(f"- Type: {obj.object_type}")
        lines.append(f"- Business Role: {obj.business_role}")
        lines.append(f"- Purpose: {obj.purpose}")
        lines.append(f"- Main columns: {', '.join(obj.main_columns) or '—'}")
        lines.append(
            f"- Relationships: {'; '.join(obj.relationships) if obj.relationships else '—'}"
        )
        lines.append(
            f"- Typical business usage: {', '.join(obj.typical_usage) if obj.typical_usage else '—'}"
        )
        if obj.key_metrics:
            lines.append(f"- Key metrics: {', '.join(obj.key_metrics)}")
        lines.append(f"- Rows: {rows}")

    text = "\n".join(lines)
    if len(text) > max_chars:
        return text[: max_chars - 60] + "\n\n...(knowledge model truncated — earlier objects retained)"
    return text


def format_full_object_catalog(model: SchemaKnowledgeModel) -> str:
    """User-facing structured explanation for EVERY table and view."""
    parts = [
        f"**Objects in `{model.database}`** ({model.object_count} discovered)",
        "",
        f"**Database purpose:** {model.purpose}",
        "",
    ]
    for obj in model.objects:
        rows = f"{obj.row_count:,}" if isinstance(obj.row_count, int) else "Unknown"
        parts.extend(
            [
                f"### `{obj.full_name}`",
                f"- **Name:** `{obj.full_name}`",
                f"- **Type:** {obj.object_type} · {obj.business_role}",
                f"- **Purpose:** {obj.purpose}",
                f"- **Main columns:** {', '.join(f'`{c}`' for c in obj.main_columns) or '—'}",
                f"- **Relationships:** {'; '.join(obj.relationships) if obj.relationships else '—'}",
                f"- **Typical business usage:** {', '.join(obj.typical_usage) if obj.typical_usage else '—'}",
                f"- **Rows:** {rows}",
                "",
            ]
        )
    if not model.objects:
        return "No tables or views were discovered in the schema profile."
    return "\n".join(parts).strip()
