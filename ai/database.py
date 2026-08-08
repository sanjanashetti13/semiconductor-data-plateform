"""Azure SQL database access — connection and query execution only."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator, Iterable, Sequence

import pyodbc

from ai.config import Settings, get_settings, require_mode1_sql


def build_connection_string(settings: Settings | None = None) -> str:
    """Build an ODBC connection string for Azure SQL (Mode 1 curated warehouse)."""
    cfg = require_mode1_sql(settings)
    return (
        f"DRIVER={{{cfg.sql_driver}}};"
        f"SERVER={cfg.sql_server};"
        f"DATABASE={cfg.sql_database};"
        f"UID={cfg.sql_username};"
        f"PWD={cfg.sql_password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
    )


@contextmanager
def get_connection(
    settings: Settings | None = None,
) -> Generator[pyodbc.Connection, None, None]:
    """Open a short-lived Azure SQL connection."""
    connection = pyodbc.connect(build_connection_string(settings))
    try:
        yield connection
    finally:
        connection.close()


def execute_query(
    sql: str,
    params: Sequence[Any] | None = None,
    settings: Settings | None = None,
) -> list[tuple]:
    """Execute a SQL query and return all rows as tuples."""
    with get_connection(settings) as connection:
        cursor = connection.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor.fetchall()


def format_rows(rows: Iterable[Any], columns: Sequence[str] | None = None) -> str:
    """Format query rows into a plain-text table for LLM prompts."""
    row_list = list(rows)
    if not row_list:
        return "No rows returned."

    lines: list[str] = []
    if columns:
        lines.append(" | ".join(columns))
        lines.append("-" * max(len(lines[0]), 20))

    for row in row_list:
        lines.append(str(tuple(row)))
    return "\n".join(lines)
