"""
FastAPI application for Semiconductor Intelligence Hub.

Run from the project root:

    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.routers.copilot import router as copilot_router
from backend.routers.sql_agent import router as sql_agent_router
from ai.odbc_compat import odbc_available

logger = logging.getLogger(__name__)

DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

_API_PREFIXES = ("api", "docs", "redoc", "openapi.json")


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if not origins:
        origins = list(DEFAULT_ORIGINS)
    if "*" in origins:
        return ["*"]
    return origins


def _static_dir() -> Path | None:
    """Prefer Vercel CDN export, then function-local copy, then local Vite build."""
    for candidate in (
        ROOT / "public",
        ROOT / "backend" / "static",
        Path(__file__).resolve().parent / "static",
        ROOT / "frontend" / "dist",
    ):
        if (candidate / "index.html").exists():
            return candidate
    return None


app = FastAPI(
    title="Semiconductor Intelligence Hub API",
    description="Manufacturing Copilot + Generic AI SQL Agent REST API.",
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(copilot_router)
app.include_router(sql_agent_router)


@app.get("/api")
@app.get("/api/")
def api_root() -> dict[str, object]:
    """Service discovery helper."""
    return {
        "service": "Semiconductor Intelligence Hub API",
        "docs": "/docs",
        "health": "/api/health",
        "odbc_available": odbc_available(),
        "ui": "/" if _static_dir() is not None else None,
    }


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
    def root_without_ui() -> dict[str, str]:
        return {
            "service": "Semiconductor Intelligence Hub API",
            "message": "Web UI is not bundled in this deployment. Open /docs or /api/health.",
            "health": "/api/health",
            "docs": "/docs",
        }
