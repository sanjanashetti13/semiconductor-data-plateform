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
    """Runtime settings for Azure SQL and Groq."""

    sql_server: str
    sql_database: str
    sql_username: str
    sql_password: str
    sql_driver: str
    groq_api_key: str
    groq_model: str


def get_settings() -> Settings:
    """Load and validate required settings from the environment."""
    sql_server = os.getenv("SQL_SERVER") or os.getenv("AZURE_SQL_SERVER")
    sql_database = os.getenv("SQL_DATABASE") or os.getenv("AZURE_SQL_DATABASE")
    sql_username = os.getenv("SQL_USERNAME") or os.getenv("AZURE_SQL_USERNAME")
    sql_password = os.getenv("SQL_PASSWORD") or os.getenv("AZURE_SQL_PASSWORD")
    sql_driver = (
        os.getenv("SQL_DRIVER")
        or os.getenv("AZURE_SQL_DRIVER")
        or "ODBC Driver 18 for SQL Server"
    )
    groq_api_key = os.getenv("GROQ_API_KEY")
    groq_model = os.getenv("GROQ_MODEL") or "llama-3.3-70b-versatile"

    missing = [
        name
        for name, value in (
            ("SQL_SERVER / AZURE_SQL_SERVER", sql_server),
            ("SQL_DATABASE / AZURE_SQL_DATABASE", sql_database),
            ("SQL_USERNAME / AZURE_SQL_USERNAME", sql_username),
            ("SQL_PASSWORD / AZURE_SQL_PASSWORD", sql_password),
            ("GROQ_API_KEY", groq_api_key),
        )
        if not value
    ]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return Settings(
        sql_server=sql_server,
        sql_database=sql_database,
        sql_username=sql_username,
        sql_password=sql_password,
        sql_driver=sql_driver,
        groq_api_key=groq_api_key,
        groq_model=groq_model,
    )
