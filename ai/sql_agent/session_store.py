"""Dynamic Azure SQL helpers for the generic SQL Agent (any database)."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Generator
from uuid import uuid4

import pyodbc

# Keep schema text small enough for Groq context windows (wide tables like SECOM).
DEFAULT_MAX_TABLES = 40
DEFAULT_MAX_COLUMNS_PER_TABLE = 28
DEFAULT_MAX_SCHEMA_CHARS = 18_000


@dataclass
class SqlConnectionConfig:
    """User-provided Azure SQL connection (held in-memory only)."""

    server: str
    database: str
    username: str
    password: str
    driver: str = "ODBC Driver 18 for SQL Server"


# In-memory session store — credentials never written to disk or logs.
_SESSIONS: dict[str, SqlConnectionConfig] = {}
_SCHEMAS: dict[str, str] = {}


def create_session(config: SqlConnectionConfig) -> str:
    """Store connection config in memory and return an opaque session id."""
    session_id = str(uuid4())
    _SESSIONS[session_id] = config
    return session_id


def get_session(session_id: str) -> SqlConnectionConfig | None:
    """Fetch an in-memory session config."""
    return _SESSIONS.get(session_id)


def delete_session(session_id: str) -> None:
    """Remove session credentials, schema, and profile."""
    _SESSIONS.pop(session_id, None)
    _SCHEMAS.pop(session_id, None)
    try:
        from ai.sql_agent.profiler import clear_profile

        clear_profile(session_id)
    except Exception:  # noqa: BLE001
        pass


def set_schema(session_id: str, schema_text: str) -> None:
    """Cache inspected schema text for a session."""
    _SCHEMAS[session_id] = schema_text


def get_schema(session_id: str) -> str | None:
    """Return cached schema text for a session."""
    return _SCHEMAS.get(session_id)


def build_odbc_string(config: SqlConnectionConfig) -> str:
    """Build an ODBC connection string (never log this)."""
    return (
        f"DRIVER={{{config.driver}}};"
        f"SERVER={config.server};"
        f"DATABASE={config.database};"
        f"UID={config.username};"
        f"PWD={config.password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
    )


@contextmanager
def open_connection(config: SqlConnectionConfig) -> Generator[pyodbc.Connection, None, None]:
    """Open a short-lived connection for the given config."""
    connection = pyodbc.connect(build_odbc_string(config), timeout=15)
    try:
        yield connection
    finally:
        connection.close()


def test_connection(config: SqlConnectionConfig) -> None:
    """Raise if the connection cannot be established."""
    with open_connection(config) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT 1;")
        cursor.fetchone()


def execute_select(
    config: SqlConnectionConfig,
    sql: str,
    *,
    max_rows: int = 100,
) -> tuple[list[str], list[tuple]]:
    """Execute a validated SELECT and return (columns, rows)."""
    with open_connection(config) as connection:
        cursor = connection.cursor()
        cursor.execute(sql)
        columns = [col[0] for col in (cursor.description or [])]
        rows = cursor.fetchmany(max_rows)
        return columns, [tuple(row) for row in rows]


def truncate_schema_for_llm(
    schema_text: str,
    *,
    max_chars: int = DEFAULT_MAX_SCHEMA_CHARS,
) -> str:
    """Hard-cap schema text so Groq requests stay within context limits."""
    text = schema_text.strip()
    if len(text) <= max_chars:
        return text
    cut = text[: max_chars - 80].rsplit("\n", 1)[0]
    return (
        f"{cut}\n\n"
        f"...(schema truncated for model context; "
        f"{len(text) - len(cut)} chars omitted)"
    )


def inspect_schema(
    config: SqlConnectionConfig,
    *,
    max_tables: int = DEFAULT_MAX_TABLES,
    max_columns_per_table: int = DEFAULT_MAX_COLUMNS_PER_TABLE,
    max_chars: int = DEFAULT_MAX_SCHEMA_CHARS,
) -> str:
    """
    Inspect INFORMATION_SCHEMA and return a compact schema summary for the LLM.

    Wide tables (hundreds of columns) are summarized so prompts fit model context.
    """
    limit = max(1, min(int(max_tables), 80))
    col_limit = max(5, min(int(max_columns_per_table), 60))

    tables_sql = f"""
    SELECT TOP ({limit})
        TABLE_SCHEMA,
        TABLE_NAME,
        TABLE_TYPE
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE IN ('BASE TABLE', 'VIEW')
      AND TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest')
    ORDER BY
        CASE WHEN TABLE_TYPE = 'BASE TABLE' THEN 0 ELSE 1 END,
        TABLE_SCHEMA,
        TABLE_NAME;
    """
    columns_sql = """
    SELECT
        COLUMN_NAME,
        DATA_TYPE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
    ORDER BY ORDINAL_POSITION;
    """
    column_count_sql = """
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?;
    """

    lines: list[str] = [
        f"# Schema · {config.database}",
        f"(up to {limit} objects, {col_limit} columns each)",
        "",
    ]

    with open_connection(config) as connection:
        cursor = connection.cursor()
        cursor.execute(tables_sql)
        tables = cursor.fetchall()

        if not tables:
            return "No tables or views found in INFORMATION_SCHEMA."

        for schema_name, table_name, table_type in tables:
            cursor.execute(column_count_sql, schema_name, table_name)
            total_cols = int(cursor.fetchone()[0] or 0)
            cursor.execute(columns_sql, schema_name, table_name)
            cols = cursor.fetchmany(col_limit)
            col_bits = [f"{name}:{dtype}" for name, dtype in cols]
            extra = total_cols - len(col_bits)
            if extra > 0:
                col_bits.append(f"+{extra} more")
            kind = "VIEW" if "VIEW" in str(table_type).upper() else "TABLE"
            lines.append(
                f"{schema_name}.{table_name} ({kind}): {', '.join(col_bits)}"
            )

    return truncate_schema_for_llm("\n".join(lines), max_chars=max_chars)
