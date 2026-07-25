from pathlib import Path
import pandas as pd


# -----------------------------
# Dataset Path
# -----------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

SECOM_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "secom"
    / "uci_secom.csv"
)
PROCESSED_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "secom_clean.csv"
)


# -----------------------------
# Load Dataset
# -----------------------------
def load_dataset(path: Path) -> pd.DataFrame:
    """
    Load a CSV dataset.

    Parameters
    ----------
    path : Path
        Path to the CSV file.

    Returns
    -------
    pd.DataFrame
        Loaded dataset.
    """

    try:
        df = pd.read_csv(path)
        print(f"Successfully loaded: {path.name}")
        return df

    except FileNotFoundError:
        print(f"File not found: {path}")
        raise

    except Exception as e:
        print(f"Error loading dataset: {e}")
        raise


# -----------------------------
# Rename Sensor Columns
# -----------------------------
def rename_sensor_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename SECOM sensor columns to a consistent naming convention.

    Parameters
    ----------
    df : pd.DataFrame
        Original SECOM dataset.

    Returns
    -------
    pd.DataFrame
        Dataset with renamed columns.
    """

    renamed_df = df.copy()

    new_columns = []

    for column in renamed_df.columns:

        if column == "Time":
            new_columns.append("timestamp")

        elif column == "Pass/Fail":
            new_columns.append("target")

        else:
            sensor_number = int(column) + 1
            new_columns.append(f"sensor_{sensor_number:03}")

    renamed_df.columns = new_columns

    return renamed_df

def convert_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert the timestamp column to datetime format.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataset.

    Returns
    -------
    pd.DataFrame
        Dataset with converted timestamp column.
    """

    converted_df = df.copy()

    converted_df["timestamp"] = pd.to_datetime(
        converted_df["timestamp"],
        errors="coerce"
    )

    return converted_df

def remove_constant_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove columns that contain only one unique value.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataset.

    Returns
    -------
    pd.DataFrame
        Dataset after removing constant columns.
    """

    cleaned_df = df.copy()

    constant_columns = [
        column
        for column in cleaned_df.columns
        if cleaned_df[column].nunique(dropna=True) == 1
    ]

    cleaned_df.drop(columns=constant_columns, inplace=True)

    print(f"\nRemoved {len(constant_columns)} constant columns.")

    if constant_columns:
        print("\nFirst 10 Constant Columns:")
        print(constant_columns[:10])

        if len(constant_columns) > 10:
            print(f"... and {len(constant_columns) - 10} more.")

    return cleaned_df

def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fill missing values in numerical columns using the median.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataset.

    Returns
    -------
    pd.DataFrame
        Dataset with missing values handled.
    """

    cleaned_df = df.copy()

    numerical_columns = cleaned_df.select_dtypes(include=["number"]).columns

    for column in numerical_columns:
        median_value = cleaned_df[column].median()
        cleaned_df[column] = cleaned_df[column].fillna(median_value)

    print("\nMissing values handled using median imputation.")

    remaining_missing = cleaned_df.isnull().sum().sum()

    print(f"Remaining Missing Values: {remaining_missing}")

    return cleaned_df

def validate_schema(df: pd.DataFrame) -> None:
    """
    Validate the schema of the preprocessed dataset.

    Parameters
    ----------
    df : pd.DataFrame
        Preprocessed dataset.
    """

    print("\nSchema Validation")
    print("-" * 60)

    # Check timestamp column
    if "timestamp" in df.columns:
        print("✓ Timestamp column exists.")
    else:
        print("✗ Timestamp column is missing.")

    # Check target column
    if "target" in df.columns:
        print("✓ Target column exists.")
    else:
        print("✗ Target column is missing.")

    # Check for missing values
    total_missing = df.isnull().sum().sum()

    if total_missing == 0:
        print("✓ No missing values found.")
    else:
        print(f"✗ {total_missing} missing values remain.")

    # Check duplicate rows
    duplicate_rows = df.duplicated().sum()

    if duplicate_rows == 0:
        print("✓ No duplicate rows found.")
    else:
        print(f"✗ {duplicate_rows} duplicate rows found.")

    print(f"✓ Final Dataset Shape: {df.shape}")

def save_clean_dataset(df: pd.DataFrame, output_path: Path) -> None:
    """
    Save the cleaned dataset as a CSV file.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned dataset.

    output_path : Path
        Destination path for the cleaned CSV.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False)

    print(f"\nClean dataset saved to:")
    print(output_path)
# -----------------------------
# Main Function
# -----------------------------
def main():

    secom_df = load_dataset(SECOM_PATH)

    clean_df = rename_sensor_columns(secom_df)
    clean_df = rename_sensor_columns(secom_df)

    clean_df = convert_timestamp(clean_df)
    clean_df = rename_sensor_columns(secom_df)

    clean_df = convert_timestamp(clean_df)

    clean_df = remove_constant_columns(clean_df)
    clean_df = handle_missing_values(clean_df)

    validate_schema(clean_df)
    save_clean_dataset(clean_df, PROCESSED_PATH)

    

    print(f"\nFinal Shape: {clean_df.shape}")

    print(clean_df.dtypes.head())

    print("\nFirst 10 Column Names:")
    print(clean_df.columns.tolist()[:10])

    print("\nLast 5 Column Names:")
    print(clean_df.columns.tolist()[-5:])


# -----------------------------
# Program Entry Point
# -----------------------------
if __name__ == "__main__":
    main()