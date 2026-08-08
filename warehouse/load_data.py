from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv
import os


load_dotenv()


DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "secom_clean.csv"


def connect_db():
    return psycopg.connect(**DB_CONFIG)


def load_dataset():
    return pd.read_csv(DATA_PATH)


def load_dim_time(conn, df):
    cursor = conn.cursor()

    timestamps = (
        pd.to_datetime(df["timestamp"])
        .drop_duplicates()
        .sort_values()
    )

    for ts in timestamps:
        cursor.execute(
            """
            INSERT INTO dim_time (
                timestamp,
                year,
                month,
                day,
                hour,
                minute,
                weekday
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp) DO NOTHING;
            """,
            (
                ts,
                ts.year,
                ts.month,
                ts.day,
                ts.hour,
                ts.minute,
                ts.day_name(),
            ),
        )

    conn.commit()

    print(f"Inserted {len(timestamps)} records into dim_time.")

def get_time_mapping(conn):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT time_id, timestamp
        FROM dim_time;
    """)

    rows = cursor.fetchall()

    return {
        timestamp: time_id
        for time_id, timestamp in rows
    }

def get_quality_mapping(conn):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT quality_id, target
        FROM dim_quality;
    """)

    rows = cursor.fetchall()

    return {
        target: quality_id
        for quality_id, target in rows
    }

def load_fact_table(conn, df, time_map, quality_map):
    cursor = conn.cursor()

    # Convert timestamps to datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    sensor_columns = [
        col for col in df.columns
        if col.startswith("sensor_")
    ]

    for _, row in df.iterrows():

        # Lookup foreign keys
        time_id = time_map[row["timestamp"]]
        quality_id = quality_map[row["target"]]

        # Sensor values
        sensor_values = [row[col] for col in sensor_columns]

        # Complete row
        values = [time_id, quality_id] + sensor_values

        placeholders = ", ".join(["%s"] * len(values))

        query = f"""
        INSERT INTO fact_sensor_data (
            time_id,
            quality_id,
            {", ".join(sensor_columns)}
        )
        VALUES ({placeholders});
        """

        cursor.execute(query, values)

    conn.commit()

    print(f"Inserted {len(df)} rows into fact_sensor_data.")
def main():
    df = load_dataset()

    print("=" * 60)
    print("Dataset Loaded Successfully")
    print("=" * 60)
    print(f"Rows    : {len(df)}")
    print(f"Columns : {len(df.columns)}")

    conn = connect_db()

    print("\nConnected to PostgreSQL successfully!")

    load_dim_time(conn, df)

    time_map = get_time_mapping(conn)

    quality_map = get_quality_mapping(conn)

    print(f"\nTotal qualities in dim_quality : {len(quality_map)}")

    first_key = next(iter(quality_map))

    print("\nExample Mapping:")
    print(first_key, "->", quality_map[first_key])

    print(f"\nQuality Mapping : {quality_map}")

    print(f"\nTotal timestamps in dim_time : {len(time_map)}")

    first_key = next(iter(time_map))

    print("\nExample Mapping:")
    print(first_key, "->", time_map[first_key])

    load_fact_table(conn, df, time_map, quality_map)

    conn.close()


if __name__ == "__main__":
    main()