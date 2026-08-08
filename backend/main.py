"""
FastAPI application for Semiconductor Intelligence Hub.

Production (Azure App Service — one URL for UI + API):

    python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT

Local API only:

    uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.routers.copilot import router as copilot_router
from backend.routers.sql_agent import router as sql_agent_router
from ai.odbc_compat import log_odbc_startup_diagnostics

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

_API_PREFIXES = ("api", "docs", "redoc", "openapi.json")


def _app_env() -> str:
    return (os.getenv("APP_ENV") or "development").strip().lower()


def _is_production() -> bool:
    return _app_env() in {"production", "prod"}


def _cors_origins() -> list[str]:
    """
    Same-origin production does not need wildcard CORS.

    - If CORS_ORIGINS is set, use that list (never prefer bare '*' in production).
    - If unset in production: empty list (same-origin browser calls only).
    - If unset in development: localhost Vite/preview origins.
    """
    raw = os.getenv("CORS_ORIGINS", "")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if origins:
        if _is_production() and origins == ["*"]:
            logger.warning(
                "CORS_ORIGINS=* is discouraged in production; "
                "prefer omitting CORS_ORIGINS for same-origin App Service."
            )
        return origins
    if _is_production():
        return []
    return list(DEFAULT_DEV_ORIGINS)


def _static_dir() -> Path | None:
    """Prefer CDN/export copies, then local Vite production build."""
    for candidate in (
        ROOT / "public",
        ROOT / "backend" / "static",
        Path(__file__).resolve().parent / "static",
        ROOT / "frontend" / "dist",
    ):
        if (candidate / "index.html").exists():
            return candidate
    return None


def _missing_ui_payload() -> dict[str, str]:
    return {
        "service": "Semiconductor Intelligence Hub API",
        "message": (
            "React production build not found. "
            "From the repo root run: cd frontend && npm ci && npm run build "
            "so that frontend/dist/index.html exists, then restart the API."
        ),
        "health": "/api/health",
        "docs": "/docs",
    }


app = FastAPI(
    title="Semiconductor Intelligence Hub API",
    description="Manufacturing Copilot + Generic AI SQL Agent REST API.",
    version="1.3.0",
    docs_url=None if _is_production() and os.getenv("ENABLE_API_DOCS", "").lower() not in {
        "1",
        "true",
        "yes",
    } else "/docs",
    redoc_url=None if _is_production() and os.getenv("ENABLE_API_DOCS", "").lower() not in {
        "1",
        "true",
        "yes",
    } else "/redoc",
)

_cors = _cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors,
    allow_credentials=bool(_cors),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(copilot_router)
app.include_router(sql_agent_router)


@app.on_event("startup")
def _on_startup() -> None:
    logger.info("Starting Semiconductor Intelligence Hub (APP_ENV=%s)", _app_env())
    log_odbc_startup_diagnostics()
    static = _static_dir()
    if static is None:
        logger.warning(
            "UI bundle missing — API-only mode. Build frontend/dist for one-server hosting."
        )
    else:
        logger.info("Serving React UI from %s", static)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    logger.info("Request validation failed: %s", exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": {"message": "Invalid request.", "suggestions": []}},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    _request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled server error: %s", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "message": "An unexpected error occurred. Please try again.",
                "suggestions": [],
            }
        },
    )


@app.get("/api")
@app.get("/api/")
def api_root() -> dict[str, object]:
    """Service discovery helper (no secrets, no ODBC internals)."""
    return {
        "service": "Semiconductor Intelligence Hub API",
        "docs": "/docs" if app.docs_url else None,
        "health": "/api/health",
        "ui": "/" if _static_dir() is not None else None,
    }


@app.get("/api/diagnostics/odbc")
def odbc_diagnostics() -> JSONResponse:
    """
    ODBC Driver 18 check for operators / Developer Mode.

    Disabled unless ENABLE_DIAGNOSTICS=true (never enable publicly in production
    without access control).
    """
    if os.getenv("ENABLE_DIAGNOSTICS", "").lower() not in {"1", "true", "yes"}:
        raise HTTPException(status_code=404, detail="Not Found")

    from ai.odbc_compat import REQUIRED_DRIVER, driver_18_available, list_odbc_drivers, odbc_available

    return JSONResponse(
        {
            "pyodbc_importable": odbc_available(),
            "required_driver": REQUIRED_DRIVER,
            "driver_18_available": driver_18_available(),
            "drivers": list_odbc_drivers(),
        }
    )


_STATIC = _static_dir()
if _STATIC is not None:
    assets_dir = _STATIC / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    async def spa_index():
        return FileResponse(_STATIC / "index.html")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        head = full_path.split("/", 1)[0]
        if head in _API_PREFIXES:
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = _STATIC / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_STATIC / "index.html")
else:

    @app.get("/")
    def root_without_ui() -> JSONResponse:
        status = 503 if _is_production() else 200
        return JSONResponse(status_code=status, content=_missing_ui_payload())
