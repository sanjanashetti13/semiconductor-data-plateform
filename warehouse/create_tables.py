from pathlib import Path
import psycopg
from dotenv import load_dotenv
import os


# ------------------------------------
# Load Environment Variables
# ------------------------------------

load_dotenv()


# ------------------------------------
# Database Configuration
# ------------------------------------

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


# ------------------------------------
# Project Paths
# ------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SCHEMA_PATH = PROJECT_ROOT / "warehouse" / "schema.sql"


# ------------------------------------
# Create Warehouse Tables
# ------------------------------------

def create_tables():

    with psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    ) as conn:

        with conn.cursor() as cursor:

            with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
                sql_script = file.read()

            cursor.execute(sql_script)

            conn.commit()

            print("=" * 60)
            print("Warehouse created successfully!")
            print("=" * 60)


# ------------------------------------
# Main
# ------------------------------------

def main():

    create_tables()


if __name__ == "__main__":
    main()