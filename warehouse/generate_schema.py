from pathlib import Path
import pandas as pd


# ------------------------------------
# Project Paths
# ------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "secom_clean.csv"
)


# ------------------------------------
# Generate SQL Sensor Columns
# ------------------------------------

def generate_sensor_columns(df: pd.DataFrame) -> None:
    """
    Generate SQL column definitions for all sensor columns.
    """

    sensor_columns = [
        column
        for column in df.columns
        if column.startswith("sensor_")
    ]

    print("\nGenerated SQL Columns\n")
    print("-" * 60)

    for column in sensor_columns:
        print(f"{column} DOUBLE PRECISION,")

    print("-" * 60)
    print(f"Total Sensor Columns: {len(sensor_columns)}")


# ------------------------------------
# Main
# ------------------------------------

def main():

    df = pd.read_csv(DATA_PATH)

    generate_sensor_columns(df)


if __name__ == "__main__":
    main()