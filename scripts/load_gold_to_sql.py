from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# ======================================================
# Azure SQL Details
# ======================================================

SERVER = "semiconductor-server-sanjana.database.windows.net"
DATABASE = "semiconductor-db"
USERNAME = "sqladmin"
PASSWORD = "FlynnRapunzel@123"

# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "gold_sensor_data.csv"

connection_string = (
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER=tcp:{SERVER},1433;"
    f"DATABASE={DATABASE};"
    f"UID={USERNAME};"
    f"PWD={PASSWORD};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
)

engine = create_engine(
    f"mssql+pyodbc:///?odbc_connect={quote_plus(connection_string)}",
    fast_executemany=True
)

# ------------------------------------------------------
# Test Connection
# ------------------------------------------------------

with engine.connect() as conn:
    version = conn.execute(text("SELECT @@VERSION")).scalar()
    print("Connected Successfully!")
    print(version)

# ------------------------------------------------------
# Read CSV
# ------------------------------------------------------

print("\nReading Gold Dataset...")

df = pd.read_csv(DATA_FILE)

print(f"Rows    : {len(df)}")
print(f"Columns : {len(df.columns)}")

# ------------------------------------------------------
# Data Cleaning
# ------------------------------------------------------

print("\nCleaning Data...")

# Timestamp
df["timestamp"] = (
    pd.to_datetime(df["timestamp"], utc=True)
      .dt.tz_convert(None)
)

# Target
df["target"] = pd.to_numeric(df["target"], errors="coerce").astype("Int64")

# Convert every sensor column to numeric
sensor_columns = [
    col for col in df.columns
    if col.startswith("sensor_")
]

for col in sensor_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

print("Cleaning Completed!")

# ------------------------------------------------------
# Check Missing Values
# ------------------------------------------------------

nulls = df.isnull().sum()

problem_cols = nulls[nulls > 0]

if len(problem_cols) > 0:
    print("\nColumns containing NULL values:")
    print(problem_cols)
else:
    print("\nNo NULL values found.")

print("\nData Types:\n")
print(df.dtypes)

print("\nFirst Record:\n")
print(df.head(1).T)

# ------------------------------------------------------
# Upload
# ------------------------------------------------------

print("\nUploading to Azure SQL...")

df.to_sql(
    name="fact_sensor_readings",
    con=engine,
    if_exists="append",
    index=False,
    chunksize=100
)

print("\nUpload Successful!")

# ------------------------------------------------------
# Verify Upload
# ------------------------------------------------------

with engine.connect() as conn:
    count = conn.execute(
        text("SELECT COUNT(*) FROM fact_sensor_readings")
    ).scalar()

print(f"\nRows in SQL Table : {count}")