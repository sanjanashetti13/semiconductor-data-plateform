"""Optional ODBC / pyodbc loading for environments without native drivers."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

REQUIRED_DRIVER = "ODBC Driver 18 for SQL Server"

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
            "(ODBC driver / pyodbc missing). On Azure App Service, ensure "
            "ODBC Driver 18 for SQL Server is installed, or run the backend locally."
        )
        raise OdbcUnavailableError(_PYODBC_ERROR) from exc


def odbc_available() -> bool:
    try:
        get_pyodbc()
        return True
    except OdbcUnavailableError:
        return False


def list_odbc_drivers() -> list[str]:
    """Return installed ODBC driver names, or empty list if pyodbc is unavailable."""
    try:
        pyodbc = get_pyodbc()
    except OdbcUnavailableError:
        return []
    try:
        return [str(name) for name in pyodbc.drivers()]
    except Exception:  # noqa: BLE001
        logger.exception("Failed to enumerate ODBC drivers")
        return []


def driver_18_available() -> bool:
    """True when Microsoft ODBC Driver 18 for SQL Server is installed."""
    drivers = list_odbc_drivers()
    return any(REQUIRED_DRIVER.lower() in d.lower() for d in drivers)


def log_odbc_startup_diagnostics() -> None:
    """
    Log ODBC / Driver 18 status at process start.

    Intended for operators and Developer Mode troubleshooting.
    Never expose driver lists on public HTTP responses.
    """
    if not odbc_available():
        logger.warning(
            "ODBC diagnostics: pyodbc is not importable. "
            "Azure SQL features will return 503 until the native driver stack is installed."
        )
        return

    drivers = list_odbc_drivers()
    if driver_18_available():
        logger.info(
            "ODBC diagnostics: %s is available (%d driver(s) total).",
            REQUIRED_DRIVER,
            len(drivers),
        )
    else:
        logger.warning(
            "ODBC diagnostics: %s was NOT found. Installed drivers: %s",
            REQUIRED_DRIVER,
            drivers or "(none)",
        )
