"""Sanitize exceptions so users never see SQL Server / ODBC raw errors."""

from __future__ import annotations

import re

FRIENDLY_PROFILE_ERROR = (
    "I couldn't analyze the database structure. "
    "Please reconnect the database or refresh the schema."
)

FRIENDLY_QUERY_ERROR = (
    "I couldn't complete that request. "
    "Please try a simpler question, or reconnect the database if the issue continues."
)

FRIENDLY_CONNECT_ERROR = (
    "Unable to connect to the database. "
    "Check the server, database name, username, and password, then try again."
)

FRIENDLY_SESSION_ERROR = (
    "Your database session is no longer active. "
    "Please reconnect on Data Sources."
)

_RAW_ERROR_MARKERS = (
    "pyodbc",
    "odbc",
    "sql server",
    "microsoft sql",
    "login failed",
    "tcp provider",
    "named pipes",
    "cannot open database",
    "invalid object name",
    "incorrect syntax",
    "arithmetic overflow",
    "conversion failed",
    "timeout expired",
    "communication link failure",
    "[sql server]",
    "sqlstate",
    "nativeerror",
    "hyperlink",
    "driver=",
)


def looks_like_raw_db_error(message: str) -> bool:
    lower = (message or "").lower()
    if any(marker in lower for marker in _RAW_ERROR_MARKERS):
        return True
    if re.search(r"\[\w+\]\[?\w*\]?", message or ""):
        # ODBC-style [Microsoft][ODBC Driver...] brackets
        if "odbc" in lower or "sql" in lower or "driver" in lower:
            return True
    return False


def sanitize_user_message(message: str | None, *, fallback: str = FRIENDLY_QUERY_ERROR) -> str:
    """Return a business-friendly message; never forward raw DB exceptions."""
    text = (message or "").strip()
    if not text:
        return fallback
    if looks_like_raw_db_error(text):
        return fallback
    # Truncate overly long technical dumps
    if len(text) > 400:
        return fallback
    return text
