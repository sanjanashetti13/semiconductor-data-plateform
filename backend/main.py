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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    # Always allow common local + Vercel preview hosts when not explicitly set.
    if not origins:
        origins = list(DEFAULT_ORIGINS)
    # Permit Vercel deployments of this project when CORS_ORIGINS includes *
    if "*" in origins:
        return ["*"]
    return origins


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
    """Service discovery helper (avoid conflicting with static site `/`)."""
    return {
        "service": "Semiconductor Intelligence Hub API",
        "docs": "/docs",
        "health": "/api/health",
        "odbc_available": odbc_available(),
    }
