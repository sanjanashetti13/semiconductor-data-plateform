"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """Runtime settings for Azure SQL (Mode 1) and Groq."""

    sql_server: str
    sql_database: str
    sql_username: str
    sql_password: str
    sql_driver: str
    groq_api_key: str
    groq_model: str
    cors_origins: tuple[str, ...]
    app_env: str


def get_settings() -> Settings:
    """
    Load settings from the environment.

    GROQ_API_KEY is required for the AI Copilot.
    Azure SQL env vars are required for Semiconductor Mode (Mode 1) tools.
    Generic SQL Mode uses credentials supplied at connect time (never from .env
    to the browser).
    """
    sql_server = (os.getenv("SQL_SERVER") or os.getenv("AZURE_SQL_SERVER") or "").strip()
    sql_database = (
        os.getenv("SQL_DATABASE") or os.getenv("AZURE_SQL_DATABASE") or ""
    ).strip()
    sql_username = (
        os.getenv("SQL_USERNAME") or os.getenv("AZURE_SQL_USERNAME") or ""
    ).strip()
    sql_password = (
        os.getenv("SQL_PASSWORD") or os.getenv("AZURE_SQL_PASSWORD") or ""
    ).strip()
    sql_driver = (
        os.getenv("SQL_DRIVER")
        or os.getenv("AZURE_SQL_DRIVER")
        or "ODBC Driver 18 for SQL Server"
    ).strip()
    groq_api_key = (os.getenv("GROQ_API_KEY") or "").strip()
    groq_model = (os.getenv("GROQ_MODEL") or "llama-3.3-70b-versatile").strip()
    app_env = (os.getenv("APP_ENV") or "development").strip()
    cors_raw = os.getenv("CORS_ORIGINS") or (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"
    )
    cors_origins = tuple(o.strip() for o in cors_raw.split(",") if o.strip())

    if not groq_api_key:
        raise ValueError(
            "Missing required environment variable: GROQ_API_KEY. "
            "Copy .env.example to .env and set your Groq API key."
        )

    return Settings(
        sql_server=sql_server,
        sql_database=sql_database,
        sql_username=sql_username,
        sql_password=sql_password,
        sql_driver=sql_driver,
        groq_api_key=groq_api_key,
        groq_model=groq_model,
        cors_origins=cors_origins,
        app_env=app_env,
    )


def require_mode1_sql(settings: Settings | None = None) -> Settings:
    """Ensure Mode 1 curated warehouse credentials are present."""
    cfg = settings or get_settings()
    missing = [
        name
        for name, value in (
            ("AZURE_SQL_SERVER / SQL_SERVER", cfg.sql_server),
            ("AZURE_SQL_DATABASE / SQL_DATABASE", cfg.sql_database),
            ("AZURE_SQL_USERNAME / SQL_USERNAME", cfg.sql_username),
            ("AZURE_SQL_PASSWORD / SQL_PASSWORD", cfg.sql_password),
        )
        if not value
    ]
    if missing:
        raise ValueError(
            "Semiconductor Mode requires Azure SQL environment variables: "
            + ", ".join(missing)
        )
    return cfg
