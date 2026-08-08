import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# --------------------------
# Load Gold Dataset
# --------------------------

DATA_FILE = "../data/gold_sensor_data.csv"

print("Reading dataset...")

df = pd.read_csv(DATA_FILE)

print(df.shape)

# --------------------------
# Prepare Data
# --------------------------

X = df.drop(columns=["timestamp", "target"])

y = df["target"]

print("\nFeatures :", X.shape[1])
print("Rows     :", X.shape[0])

# --------------------------
# Train Test Split
# --------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

# --------------------------
# Train Model
# --------------------------

print("\nTraining Random Forest...")

model = RandomForestClassifier(
    n_estimators=300,
    random_state=42,
    n_jobs=-1,
    class_weight="balanced"
)

model.fit(X_train, y_train)

print("Training Complete!")

# --------------------------
# Evaluate
# --------------------------

predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

print("\nAccuracy :", round(accuracy * 100, 2), "%")

print("\nClassification Report\n")

print(classification_report(y_test, predictions))

# --------------------------
# Save Model
# --------------------------

joblib.dump(
    model,
    "../ml_outputs/failure_prediction_model.pkl"
)

print("\nModel Saved!")