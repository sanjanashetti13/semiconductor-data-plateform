from pathlib import Path
import pandas as pd

# -----------------------------------------------------
# Load Dataset
# -----------------------------------------------------

DATA_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "processed"
    / "secom_clean.csv"
)

df = pd.read_csv(DATA_PATH)

# -----------------------------------------------------
# SECOM Convention
# -1 = Pass
#  1 = Fail
# -----------------------------------------------------

pass_df = df[df["target"] == -1]
fail_df = df[df["target"] == 1]

# -----------------------------------------------------
# Find Sensor Columns
# -----------------------------------------------------

sensor_columns = [
    col for col in df.columns
    if col.startswith("sensor_")
]

results = []

# -----------------------------------------------------
# Compare Every Sensor
# -----------------------------------------------------

for sensor in sensor_columns:

    pass_avg = pass_df[sensor].mean()
    fail_avg = fail_df[sensor].mean()

    difference = abs(pass_avg - fail_avg)

    results.append({
        "Sensor": sensor,
        "Pass Average": pass_avg,
        "Fail Average": fail_avg,
        "Difference": difference
    })

# -----------------------------------------------------
# Rank Sensors
# -----------------------------------------------------

results_df = pd.DataFrame(results)

results_df = results_df.sort_values(
    by="Difference",
    ascending=False
)

print("\nTop 10 Most Important Sensors\n")

print(results_df.head(10))

# -----------------------------------------------------
# Save Results
# -----------------------------------------------------

OUTPUT_PATH = (
    Path(__file__).resolve().parent
    / "top_sensor_difference.csv"
)

results_df.to_csv(OUTPUT_PATH, index=False)

print(f"\nSaved to:\n{OUTPUT_PATH}")