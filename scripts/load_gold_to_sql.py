"""Load gold sensor CSV into Azure SQL (env-based credentials only)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SERVER = os.getenv("AZURE_SQL_SERVER") or os.getenv("SQL_SERVER")
DATABASE = os.getenv("AZURE_SQL_DATABASE") or os.getenv("SQL_DATABASE")
USERNAME = os.getenv("AZURE_SQL_USERNAME") or os.getenv("SQL_USERNAME")
PASSWORD = os.getenv("AZURE_SQL_PASSWORD") or os.getenv("SQL_PASSWORD")
DRIVER = (
    os.getenv("AZURE_SQL_DRIVER")
    or os.getenv("SQL_DRIVER")
    or "ODBC Driver 18 for SQL Server"
)

DATA_FILE = PROJECT_ROOT / "data" / "gold_sensor_data.csv"


def main() -> None:
    missing = [
        name
        for name, value in (
            ("AZURE_SQL_SERVER / SQL_SERVER", SERVER),
            ("AZURE_SQL_DATABASE / SQL_DATABASE", DATABASE),
            ("AZURE_SQL_USERNAME / SQL_USERNAME", USERNAME),
            ("AZURE_SQL_PASSWORD / SQL_PASSWORD", PASSWORD),
        )
        if not value
    ]
    if missing:
        print(
            "Missing required environment variables:\n  - "
            + "\n  - ".join(missing)
            + "\n\nCopy .env.example to .env and set Azure SQL credentials.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not DATA_FILE.exists():
        print(f"Data file not found: {DATA_FILE}", file=sys.stderr)
        sys.exit(1)

    connection_string = (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER=tcp:{SERVER},1433;"
        f"DATABASE={DATABASE};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
    )

    engine = create_engine(
        f"mssql+pyodbc:///?odbc_connect={quote_plus(connection_string)}",
        fast_executemany=True,
    )

    with engine.connect() as conn:
        version = conn.execute(text("SELECT @@VERSION")).scalar()
        print("Connected successfully.")
        print(str(version)[:120], "...")

    print("\nReading gold dataset...")
    df = pd.read_csv(DATA_FILE)
    print(f"Rows    : {len(df)}")
    print(f"Columns : {len(df.columns)}")

    print("\nCleaning data...")
    df["timestamp"] = (
        pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(None)
    )
    df["target"] = pd.to_numeric(df["target"], errors="coerce").astype("Int64")
    for col in [c for c in df.columns if c.startswith("sensor_")]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    print("Cleaning completed.")

    print("\nUploading to Azure SQL (fact_sensor_readings)...")
    df.to_sql(
        name="fact_sensor_readings",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=100,
    )
    print("Upload successful.")

    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM fact_sensor_readings")
        ).scalar()
    print(f"\nRows in SQL table: {count}")


if __name__ == "__main__":
    main()
