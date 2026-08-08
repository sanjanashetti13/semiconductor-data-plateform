import pandas as pd

# Read Gold Dataset
df = pd.read_csv("C:\KLE\KLE_Projects\Semiconductor\semiconductor-data-platform\data\gold_sensor_data.csv.csv")

columns = df.columns

sql = []
sql.append("CREATE TABLE fact_sensor_readings (")
sql.append("    reading_id INT IDENTITY(1,1) PRIMARY KEY,")

for col in columns:

    if col.lower() == "timestamp":
        sql.append(f"    [{col}] DATETIME2,")

    elif col.lower() in ["target", "pass/fail"]:
        sql.append(f"    [{col}] INT,")

    else:
        sql.append(f"    [{col}] FLOAT,")

sql[-1] = sql[-1].rstrip(",")

sql.append(");")

with open("../sql/create_fact_table.sql", "w") as f:
    f.write("\n".join(sql))

print("SQL file generated successfully.")
print("Columns:", len(columns))