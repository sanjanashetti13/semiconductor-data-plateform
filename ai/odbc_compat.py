"""Optional ODBC / pyodbc loading for environments without native drivers (e.g. Vercel)."""

from __future__ import annotations

from typing import Any

_PYODBC: Any | None = None
_PYODBC_ERROR: str | None = None


class OdbcUnavailableError(RuntimeError):
    """Raised when Azure SQL connectivity is not available in this runtime."""


def get_pyodbc():
    """
    Lazy-import pyodbc.

    Returns the module or raises OdbcUnavailableError with a user-safe message.
    """
    global _PYODBC, _PYODBC_ERROR
    if _PYODBC is not None:
        return _PYODBC
    if _PYODBC_ERROR is not None:
        raise OdbcUnavailableError(_PYODBC_ERROR)
    try:
        import pyodbc as _mod  # type: ignore

        _PYODBC = _mod
        return _PYODBC
    except Exception as exc:  # noqa: BLE001
        _PYODBC_ERROR = (
            "Azure SQL connectivity is not available in this hosting environment "
            "(ODBC driver / pyodbc missing). Deploy the API on Azure App Service, "
            "Render, or Railway for full database features, or run the backend locally."
        )
        raise OdbcUnavailableError(_PYODBC_ERROR) from exc


def odbc_available() -> bool:
    try:
        get_pyodbc()
        return True
    except OdbcUnavailableError:
        return False
