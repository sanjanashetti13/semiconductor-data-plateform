"""Schema-aware metadata reasoning from the cached Database Profile."""

from __future__ import annotations

from ai.sql_agent.planner import MetadataIntent
from ai.sql_agent.profiler import DatabaseProfile, TableProfile


def primary_keys_for(profile: DatabaseProfile, schema: str, table: str) -> list[str]:
    """Extract PK column names for a table from the profile."""
    keys: list[str] = []
    for row in profile.primary_keys:
        # Expected: schema, table, column, constraint
        if len(row) >= 3 and str(row[0]).lower() == schema.lower() and str(row[1]).lower() == table.lower():
            keys.append(str(row[2]))
    return keys


def infer_purpose(tp: TableProfile) -> str:
    """Short purpose inferred from table + column names (no LLM)."""
    if tp.purpose:
        return tp.purpose
    name = tp.name.lower()
    cols = {c.lower() for c, _ in tp.columns}
    col_blob = " ".join(sorted(cols))

    if name.startswith("fact_") or "fact" in name:
        return "Fact / measurement table storing analytical events or readings."
    if name.startswith("dim_") or name.startswith("dimension"):
        return "Dimension table describing business entities for analysis."
    if "sensor" in name or "sensor" in col_blob:
        return "Stores sensor measurements or sensor-related attributes."
    if any(k in name for k in ("order", "sale", "revenue", "transaction", "invoice")):
        return "Transactional table capturing business events or sales activity."
    if any(k in name for k in ("customer", "client", "user", "account")):
        return "Master data about customers or user accounts."
    if any(k in name for k in ("product", "item", "sku", "inventory")):
        return "Product or inventory reference data."
    if any(k in name for k in ("time", "date", "calendar", "month")):
        return "Time dimension supporting date-based reporting."
    if any(k in name for k in ("fail", "defect", "quality", "yield", "wafer")):
        return "Manufacturing quality / yield related records."
    if any(k in cols for k in ("created_at", "updated_at", "timestamp", "event_time")):
        return "Operational records with time-stamped activity."
    if tp.object_type == "VIEW":
        return "Database view combining or projecting underlying table data."
    return f"Relational table with {len(tp.columns)} columns supporting stored application data."


def infer_example_use(tp: TableProfile) -> str:
    """Example analytical use grounded in column names."""
    name = f"{tp.schema}.{tp.name}"
    cols = [c.lower() for c, _ in tp.columns]
    if any("yield" in c for c in cols) or "yield" in tp.name.lower():
        return f"Ask: What is the average yield in `{name}`?"
    if any("fail" in c or "pass" in c for c in cols):
        return f"Ask: How many failed vs passed rows are in `{name}`?"
    if any("sensor" in c for c in cols) or "sensor" in tp.name.lower():
        return f"Ask: Compare sensor values in `{name}`."
    if any(c in cols for c in ("amount", "revenue", "sales", "price", "total")):
        return f"Ask: What is the total sales/amount in `{name}`?"
    if any("date" in c or c.endswith("_at") for c in cols):
        return f"Ask: Show monthly counts from `{name}`."
    return f"Ask: Show sample rows from `{name}` or count rows in `{name}`."


def pick_primary_fact_table(profile: DatabaseProfile) -> TableProfile | None:
    """
    Prefer fact_sensor_readings (Semiconductor), then fact_*, else largest table.
    """
    if not profile.tables:
        return None
    for t in profile.tables:
        if t.name.lower() == "fact_sensor_readings":
            return t
    fact_tables = [t for t in profile.tables if t.name.lower().startswith("fact_")]
    if fact_tables:
        return max(fact_tables, key=lambda t: t.row_count or 0)
    ranked = sorted(profile.tables, key=lambda t: t.row_count or -1, reverse=True)
    return ranked[0]


def format_table_catalog(profile: DatabaseProfile, *, include_views: bool = False) -> str:
    """
    Rich catalog for 'what tables exist' / 'what does each table contain'.

    Sections per table: Table Name, Purpose, Columns, Rows, Example Use
    """
    objects: list[TableProfile] = list(profile.tables)
    if include_views:
        objects.extend(profile.views)
    if not objects:
        return "No tables were found in the cached schema profile."

    parts: list[str] = [f"**Tables in `{profile.database}`** ({len(profile.tables)} found)", ""]
    for tp in objects:
        pks = primary_keys_for(profile, tp.schema, tp.name)
        pk_text = ", ".join(f"`{k}`" for k in pks) if pks else "Not detected"
        col_preview = ", ".join(f"`{n}` ({t})" for n, t in tp.columns[:12])
        if len(tp.columns) > 12:
            col_preview += f", … (+{len(tp.columns) - 12} more)"
        rows_text = f"{tp.row_count:,}" if isinstance(tp.row_count, int) else "Unknown"
        parts.extend(
            [
                f"### `{tp.schema}.{tp.name}`",
                f"- **Table Name:** `{tp.schema}.{tp.name}`",
                f"- **Business Role:** {tp.business_role or 'Table'}",
                f"- **Purpose:** {tp.purpose or infer_purpose(tp)}",
                f"- **Columns:** {len(tp.columns)} — {col_preview or '_none_'}",
                f"- **Primary Key:** {pk_text}",
                f"- **Rows:** {rows_text}",
                f"- **Key Metrics:** {', '.join(f'`{m}`' for m in (tp.key_metrics or [])[:8]) or '—'}",
                f"- **Example Use:** {', '.join((tp.use_cases or [infer_example_use(tp)])[:3])}",
                "",
            ]
        )
    return "\n".join(parts).strip()


def format_views_catalog(profile: DatabaseProfile) -> str:
    if not profile.views:
        return "No views were found in the cached schema profile."
    parts = [f"**Views in `{profile.database}`** ({len(profile.views)} found)", ""]
    for vp in profile.views:
        col_preview = ", ".join(f"`{n}`" for n, _ in vp.columns[:10])
        parts.append(f"- `{vp.schema}.{vp.name}` — {len(vp.columns)} columns ({col_preview})")
    return "\n".join(parts)


def format_row_counts(profile: DatabaseProfile) -> str:
    if not profile.tables:
        return "No tables available for row counts."
    ranked = sorted(profile.tables, key=lambda t: t.row_count or -1, reverse=True)
    lines = ["**Row counts**", ""]
    for tp in ranked:
        rc = f"{tp.row_count:,}" if isinstance(tp.row_count, int) else "Unknown"
        lines.append(f"- `{tp.schema}.{tp.name}` — **{rc}** rows · {len(tp.columns)} columns")
    return "\n".join(lines)


def resolve_table(profile: DatabaseProfile, target: str | None) -> TableProfile | None:
    if not target:
        return None
    cleaned = target.replace("[", "").replace("]", "").strip()
    if "." in cleaned:
        schema, name = cleaned.split(".", 1)
        for tp in profile.tables + profile.views:
            if tp.schema.lower() == schema.lower() and tp.name.lower() == name.lower():
                return tp
    for tp in profile.tables + profile.views:
        if tp.name.lower() == cleaned.lower():
            return tp
    return None


def format_columns_for_table(profile: DatabaseProfile, target: str | None) -> str:
    tp = resolve_table(profile, target)
    if tp is None:
        # All tables summary
        lines = ["**Columns by table**", ""]
        for table in profile.tables[:20]:
            cols = ", ".join(f"`{n}`" for n, _ in table.columns[:15])
            lines.append(f"- `{table.schema}.{table.name}` ({len(table.columns)}): {cols}")
        return "\n".join(lines)
    pks = primary_keys_for(profile, tp.schema, tp.name)
    lines = [
        f"**Columns · `{tp.schema}.{tp.name}`**",
        "",
        f"- **Purpose:** {infer_purpose(tp)}",
        f"- **Primary Key:** {', '.join(f'`{k}`' for k in pks) or 'Not detected'}",
        f"- **Rows:** {tp.row_count if tp.row_count is not None else 'Unknown'}",
        "",
    ]
    for name, dtype in tp.columns:
        marker = " (PK)" if name in pks else ""
        lines.append(f"- `{name}` — {dtype}{marker}")
    return "\n".join(lines)


def format_keys(profile: DatabaseProfile, *, kind: str) -> str:
    rows = profile.primary_keys if kind == "pk" else profile.foreign_keys
    title = "Primary keys" if kind == "pk" else "Foreign keys / relationships"
    if not rows:
        return f"No {title.lower()} were detected in the schema profile."
    lines = [f"**{title}**", ""]
    for row in rows[:60]:
        lines.append("- " + " · ".join(str(v) for v in row if v is not None))
    return "\n".join(lines)


def format_sample_answer(
    *,
    table: TableProfile,
    columns: list[str],
    rows: list[tuple],
) -> str:
    """Business-facing sample rows answer (never just table names)."""
    from ai.sql_agent.formatter import format_rows_markdown
    from ai.sql_agent.executor import QueryResult

    result = QueryResult(
        label=f"Sample · {table.schema}.{table.name}",
        sql=f"SELECT TOP (10) * FROM [{table.schema}].[{table.name}]",
        columns=columns,
        rows=rows,
    )
    purpose = infer_purpose(table)
    return (
        f"**Sample rows from `{table.schema}.{table.name}`**\n\n"
        f"{purpose}\n\n"
        f"Showing up to {len(rows)} of {table.row_count if table.row_count is not None else 'unknown'} rows.\n\n"
        f"{format_rows_markdown(result, max_rows=10)}"
    )


def follow_ups_for_metadata(
    intent: MetadataIntent | None,
    profile: DatabaseProfile,
    *,
    sample_table: TableProfile | None = None,
) -> list[str]:
    """Context-aware suggestions based on the last metadata response."""
    fact = pick_primary_fact_table(profile)
    fact_name = f"{fact.schema}.{fact.name}" if fact else None

    if intent == MetadataIntent.SAMPLE_ROWS and sample_table:
        full = f"{sample_table.schema}.{sample_table.name}"
        return [
            f"Explain these columns in {full}",
            f"Find missing values in {full}",
            f"Show statistics for {full}",
            f"Generate a summary of {full}",
        ]

    if intent in (MetadataIntent.LIST_TABLES, MetadataIntent.DESCRIBE_SCHEMA, None):
        suggestions = []
        if fact_name:
            suggestions.append(f"Describe {fact_name}")
        suggestions.extend(
            [
                "Show columns for the main tables",
                "Show row counts",
                "Explain relationships",
            ]
        )
        if fact_name:
            suggestions.append(f"Show sample rows from {fact_name}")
        return suggestions[:4]

    if intent == MetadataIntent.LIST_COLUMNS:
        return [
            "Show sample rows",
            "Show row counts",
            "Show primary keys",
            "What is this database about?",
        ]

    if intent == MetadataIntent.ROW_COUNTS:
        return [
            "Show sample rows",
            "List the tables with purpose and columns",
            "Show primary keys",
            "What is this database about?",
        ]

    if intent in (MetadataIntent.RELATIONSHIPS, MetadataIntent.FOREIGN_KEYS, MetadataIntent.PRIMARY_KEYS):
        return [
            "List the tables with purpose and columns",
            "Show sample rows",
            "Show row counts",
            "What is this database about?",
        ]

    if intent == MetadataIntent.LIST_VIEWS:
        return [
            "List the tables with purpose and columns",
            "Show sample rows",
            "What is this database about?",
        ]

    return [
        "List the tables with purpose and columns",
        "Show sample rows",
        "Show row counts",
        "What is this database about?",
    ]


def follow_ups_for_understanding(profile: DatabaseProfile) -> list[str]:
    fact = pick_primary_fact_table(profile)
    suggestions = ["List the tables with purpose and columns", "Show row counts"]
    if fact:
        suggestions.append(f"Show sample rows from {fact.schema}.{fact.name}")
        suggestions.append(f"Describe {fact.schema}.{fact.name}")
    else:
        suggestions.extend(["Show sample rows", "Show primary keys"])
    return suggestions[:4]