"""Database Profiling Tool — build once per session, cache in memory."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ai.sql_agent.session_store import SqlConnectionConfig, open_connection
from ai.sql_agent.templates import (
    sql_foreign_keys,
    sql_list_tables,
    sql_list_views,
    sql_primary_keys,
    sql_row_count,
    sql_sample_rows,
)

logger = logging.getLogger(__name__)

_PROFILES: dict[str, "DatabaseProfile"] = {}

FRIENDLY_PROFILE_ERROR = (
    "I couldn't analyze the database structure. "
    "Please reconnect the database or refresh the schema."
)


@dataclass
class TableProfile:
    schema: str
    name: str
    object_type: str  # TABLE | VIEW
    columns: list[tuple[str, str]] = field(default_factory=list)  # (name, type)
    row_count: int | None = None
    sample_rows: list[tuple] = field(default_factory=list)
    sample_columns: list[str] = field(default_factory=list)
    # Semantic enrichment (filled by semantics.enrich_profile_semantics)
    business_role: str | None = None
    purpose: str | None = None
    key_metrics: list[str] = field(default_factory=list)
    important_columns: list[str] = field(default_factory=list)
    use_cases: list[str] = field(default_factory=list)
    preferred_for: list[str] = field(default_factory=list)
    primary_key_columns: list[str] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)
    kpi_grain: str | None = None  # "summary" | "periodic" for KPI views


@dataclass
class DatabaseProfile:
    """Cached structural snapshot of a connected database."""

    database: str
    schemas: list[str] = field(default_factory=list)
    tables: list[TableProfile] = field(default_factory=list)
    views: list[TableProfile] = field(default_factory=list)
    primary_keys: list[tuple] = field(default_factory=list)
    foreign_keys: list[tuple] = field(default_factory=list)
    built: bool = False
    semiconductor_mode: bool = False

    @property
    def table_count(self) -> int:
        return len(self.tables)

    @property
    def view_count(self) -> int:
        return len(self.views)


class ProfileBuildError(RuntimeError):
    """Raised when profiling fails; message is always user-safe."""


def get_profile(session_id: str) -> DatabaseProfile | None:
    return _PROFILES.get(session_id)


def set_profile(session_id: str, profile: DatabaseProfile) -> None:
    _PROFILES[session_id] = profile


def clear_profile(session_id: str) -> None:
    _PROFILES.pop(session_id, None)


def clear_all_profiles() -> None:
    _PROFILES.clear()


def _fetchall(cursor, sql: str, params: tuple | None = None) -> list[tuple]:
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    return [tuple(row) for row in cursor.fetchall()]


def _fetchmany(cursor, sql: str, params: tuple | None = None, n: int = 50) -> list[tuple]:
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    return [tuple(row) for row in cursor.fetchmany(n)]


def build_database_profile(
    config: SqlConnectionConfig,
    *,
    max_tables: int = 30,
    max_columns: int = 40,
    sample_tables: int = 5,
) -> DatabaseProfile:
    """
    Inspect the connected database once and return a structured profile.

    Never raises pyodbc errors to callers — wraps failures as ProfileBuildError.
    """
    try:
        profile = DatabaseProfile(database=config.database)
        schema_set: set[str] = set()

        with open_connection(config) as connection:
            cursor = connection.cursor()

            table_rows = _fetchmany(cursor, sql_list_tables(), n=max_tables)
            view_rows = _fetchmany(cursor, sql_list_views(), n=max_tables)

            columns_sql = """
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
            """

            def load_object(schema: str, name: str, kind: str) -> TableProfile:
                schema_set.add(schema)
                cols = _fetchmany(cursor, columns_sql, (schema, name), n=max_columns)
                tp = TableProfile(
                    schema=schema,
                    name=name,
                    object_type=kind,
                    columns=[(str(c[0]), str(c[1])) for c in cols],
                )
                if kind in ("TABLE", "VIEW"):
                    try:
                        cursor.execute(sql_row_count(schema, name))
                        row = cursor.fetchone()
                        tp.row_count = int(row[0]) if row else None
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "Row count failed for %s.%s: %s", schema, name, exc
                        )
                        tp.row_count = None
                return tp

            for row in table_rows:
                schema, name = str(row[0]), str(row[1])
                profile.tables.append(load_object(schema, name, "TABLE"))

            for row in view_rows:
                schema, name = str(row[0]), str(row[1])
                profile.views.append(load_object(schema, name, "VIEW"))

            try:
                profile.primary_keys = _fetchmany(cursor, sql_primary_keys(), n=200)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Primary key inspect failed: %s", exc)

            try:
                profile.foreign_keys = _fetchmany(cursor, sql_foreign_keys(), n=200)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Foreign key inspect failed: %s", exc)

            # Sample 3 rows from important tables (highest row count first).
            ranked = sorted(
                [t for t in profile.tables if t.row_count is not None],
                key=lambda t: t.row_count or 0,
                reverse=True,
            )
            targets = ranked[:sample_tables] or profile.tables[:sample_tables]
            # Prefer sampling KPI views as well for semantic evidence.
            view_targets = [
                v
                for v in profile.views
                if any(
                    k in v.name.lower()
                    or any(k in c.lower() for c, _ in v.columns)
                    for k in ("summary", "yield", "kpi", "manufactur")
                )
            ][:2]
            for tp in list(targets) + view_targets:
                try:
                    cursor.execute(sql_sample_rows(tp.schema, tp.name, 3))
                    cols = [col[0] for col in (cursor.description or [])]
                    rows = [tuple(r) for r in cursor.fetchmany(3)]
                    if len(cols) > 12:
                        cols = cols[:12]
                        rows = [tuple(r[:12]) for r in rows]
                    tp.sample_columns = cols
                    tp.sample_rows = rows
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Sample failed for %s.%s: %s", tp.schema, tp.name, exc
                    )

        profile.schemas = sorted(schema_set)
        profile.built = True

        from ai.sql_agent.semantics import enrich_profile_semantics

        enrich_profile_semantics(profile)
        return profile
    except ProfileBuildError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Database profile build failed for db=%s", config.database)
        raise ProfileBuildError(FRIENDLY_PROFILE_ERROR) from exc


def ensure_profile(session_id: str, config: SqlConnectionConfig) -> DatabaseProfile:
    """Return cached profile or build and cache it."""
    existing = get_profile(session_id)
    if existing and existing.built:
        # Re-enrich older sessions that lack semantic roles / Semiconductor flags.
        sample = (existing.tables or existing.views or [None])[0]
        needs_enrich = sample is not None and (
            not getattr(sample, "business_role", None)
            or not hasattr(sample, "preferred_for")
            or not hasattr(existing, "semiconductor_mode")
        )
        if needs_enrich:
            from ai.sql_agent.semantics import enrich_profile_semantics

            enrich_profile_semantics(existing)
        return existing
    profile = build_database_profile(config)
    set_profile(session_id, profile)
    return profile


def profile_to_text(profile: DatabaseProfile, *, max_chars: int = 14_000) -> str:
    """Serialize semantic profile for LLM understanding / SQL generation."""
    from ai.sql_agent.semantics import semantic_profile_text

    return semantic_profile_text(profile, max_chars=max_chars)


def profile_schema_preview(profile: DatabaseProfile, *, max_lines: int = 80) -> str:
    """Short preview for the Data Sources UI (includes semantic roles + purpose)."""
    mode = "Semiconductor Mode" if getattr(profile, "semiconductor_mode", False) else "Generic SQL Mode"
    lines = [
        f"# Semantic Profile · {profile.database} · {mode}",
        f"Schemas: {', '.join(profile.schemas) or '(none)'}",
        f"Tables: {profile.table_count} · Views: {profile.view_count}",
        "",
        "On connect the assistant inferred business roles (Fact / Dimension / View).",
        "",
    ]
    for tp in profile.tables[:40]:
        role = tp.business_role or "Table"
        purpose = (tp.purpose or "")[:80]
        col_bits = [f"{n}:{t}" for n, t in tp.columns[:8]]
        extra = len(tp.columns) - len(col_bits)
        if extra > 0:
            col_bits.append(f"+{extra} more")
        lines.append(f"{tp.schema}.{tp.name} ({role})")
        if purpose:
            lines.append(f"  Purpose: {purpose}")
        lines.append(f"  Columns: {', '.join(col_bits)}")
    for vp in profile.views[:20]:
        role = vp.business_role or "Analytical View"
        purpose = (vp.purpose or "")[:80]
        lines.append(f"{vp.schema}.{vp.name} ({role})")
        if purpose:
            lines.append(f"  Purpose: {purpose}")
    return "\n".join(lines[:max_lines])


def _safe_cell(value: Any) -> Any:
    text = str(value)
    return text if len(text) <= 80 else text[:77] + "..."
