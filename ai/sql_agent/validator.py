"""SQL safety validation — SELECT-only for the generic SQL Agent."""

from __future__ import annotations

import re

FORBIDDEN_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "EXEC",
    "EXECUTE",
    "MERGE",
    "GRANT",
    "REVOKE",
    "CREATE",
    "REPLACE",
    "CALL",
    "INTO",
    "OPENROWSET",
    "OPENDATASOURCE",
    "BULK",
)


class UnsafeSqlError(ValueError):
    """Raised when SQL fails safety validation."""


def _strip_comments(sql: str) -> str:
    """Remove line and block comments."""
    without_block = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    without_line = re.sub(r"--.*?$", " ", without_block, flags=re.MULTILINE)
    return without_line


def validate_select_only(sql: str) -> str:
    """
    Validate that SQL is a single read-only SELECT/CTE statement.

    Returns cleaned SQL or raises UnsafeSqlError.
    """
    if not sql or not sql.strip():
        raise UnsafeSqlError("SQL query cannot be empty.")

    cleaned = _strip_comments(sql).strip().rstrip(";").strip()
    if not cleaned:
        raise UnsafeSqlError("SQL query cannot be empty after removing comments.")

    if ";" in cleaned:
        raise UnsafeSqlError("Multiple SQL statements are not allowed.")

    upper = cleaned.upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        raise UnsafeSqlError("Only SELECT queries are allowed.")

    for keyword in FORBIDDEN_KEYWORDS:
        pattern = rf"(?<![A-Z0-9_]){re.escape(keyword)}(?![A-Z0-9_])"
        if re.search(pattern, upper):
            raise UnsafeSqlError(f"Forbidden SQL keyword detected: {keyword}")

    if "XP_" in upper or "SP_" in upper:
        raise UnsafeSqlError("Stored procedure execution is not allowed.")

    return cleaned
