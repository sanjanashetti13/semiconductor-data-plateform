
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SECOM_PATH = PROJECT_ROOT / "data" / "raw" / "secom" / "uci_secom.csv"

WAFER_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "wafer_defect"
    / "semiconductor_wafer_defect_dataset.csv"
)


def load_dataset(path: Path) -> pd.DataFrame:
    """
    Load a CSV dataset into a pandas DataFrame.

    Parameters
    ----------
    path : Path
        Path to the CSV file.

    Returns
    -------
    pd.DataFrame
        Loaded DataFrame.
    """
    try:
        df = pd.read_csv(path)
        print(f"Successfully loaded: {path.name}")
        return df

    except FileNotFoundError:
        print(f"ERROR: File not found -> {path}")
        raise

    except Exception as e:
        print(f"ERROR while reading {path.name}: {e}")
        raise
def print_separator(title: str) -> None:
    """
    Print a formatted section header.
    """
    print("\n" + "=" * 60)
    print(title.center(60))
    print("=" * 60)


def basic_profile(df: pd.DataFrame, dataset_name: str) -> None:
    """
    Display basic profiling information for a dataset.

    Parameters
    ----------
    df : pd.DataFrame
        The dataset to profile.

    dataset_name : str
        Name of the dataset.
    """

    print_separator(f"{dataset_name} PROFILE")

    # Dataset Shape
    print("\nDataset Shape")
    print("-" * 60)
    print(f"Rows    : {df.shape[0]}")
    print(f"Columns : {df.shape[1]}")

    # Memory Usage
    memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)

    print("\nMemory Usage")
    print("-" * 60)
    print(f"{memory_mb:.2f} MB")

    # Data Types
    print("\nData Types")
    print("-" * 60)
    print(df.dtypes.value_counts())

    # Column Names
    print("\nColumn Names")
    print("-" * 60)

    for index, column in enumerate(df.columns, start=1):
        print(f"{index}. {column}")

    # First Five Rows
    print("\nFirst 5 Rows")
    print("-" * 60)
    print(df.head())

    # Last Five Rows
    print("\nLast 5 Rows")
    print("-" * 60)
    print(df.tail())

def data_quality_profile(df: pd.DataFrame, dataset_name: str) -> None:
    """
    Display data quality metrics for a dataset.

    Parameters
    ----------
    df : pd.DataFrame
        Dataset to analyze.

    dataset_name : str
        Name of the dataset.
    """

    print_separator(f"{dataset_name} DATA QUALITY REPORT")

    # Missing Values
    print("\nMissing Values")
    print("-" * 60)

    missing_count = df.isnull().sum()
    missing_percent = (missing_count / len(df)) * 100

    missing_df = pd.DataFrame({
        "Missing Count": missing_count,
        "Missing %": missing_percent.round(2)
    })

    missing_df = missing_df[missing_df["Missing Count"] > 0]

    if missing_df.empty:
        print("No missing values found.")
    else:
        print(missing_df.sort_values(by="Missing Count", ascending=False))

    # Duplicate Rows
    print("\nDuplicate Rows")
    print("-" * 60)

    duplicate_rows = df.duplicated().sum()
    print(f"Duplicate Rows : {duplicate_rows}")

    # Unique Values
    print("\nUnique Values Per Column")
    print("-" * 60)

    unique_values = df.nunique()

    unique_df = pd.DataFrame({
        "Unique Values": unique_values
    })

    print(unique_df)

    # Constant Columns
    print("\nConstant Columns")
    print("-" * 60)

    constant_columns = unique_values[unique_values == 1].index.tolist()

    if constant_columns:
        for column in constant_columns:
            print(column)
    else:
        print("No constant columns found.")

    # Summary
    print("\nSummary")
    print("-" * 60)

    print(f"Total Rows              : {len(df)}")
    print(f"Total Columns           : {df.shape[1]}")
    print(f"Columns With Nulls      : {len(missing_df)}")
    print(f"Duplicate Rows          : {duplicate_rows}")
    print(f"Constant Columns        : {len(constant_columns)}")

def statistical_profile(df: pd.DataFrame, dataset_name: str) -> None:
    """
    Display statistical summary of numerical columns.

    Parameters
    ----------
    df : pd.DataFrame
        Dataset to analyze.

    dataset_name : str
        Name of the dataset.
    """

    print_separator(f"{dataset_name} STATISTICAL PROFILE")

    # Select only numerical columns
    numerical_df = df.select_dtypes(include=["number"])

    if numerical_df.empty:
        print("No numerical columns found.")
        return

    statistics = numerical_df.describe().T

    print("\nStatistical Summary")
    print("-" * 60)
    print(statistics.round(2))

    print("\nOverall Statistics")
    print("-" * 60)
    print(f"Numerical Columns : {numerical_df.shape[1]}")
    print(f"Total Observations : {len(df)}")

def main():

    print("SEMICONDUCTOR DATA PROFILING - PHASE 2")

    # Load datasets
    secom_df = load_dataset(SECOM_PATH)
    wafer_df = load_dataset(WAFER_PATH)

    print("\nDatasets loaded successfully.")

    basic_profile(secom_df, "SECOM DATASET")
    basic_profile(wafer_df, "WAFER DEFECT DATASET")
    data_quality_profile(secom_df, "SECOM DATASET")
    data_quality_profile(wafer_df, "WAFER DEFECT DATASET")
    statistical_profile(secom_df, "SECOM DATASET")
    statistical_profile(wafer_df, "WAFER DEFECT DATASET")

   
    


if __name__ == "__main__":
    main()