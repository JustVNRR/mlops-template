from pathlib import Path

import pandas as pd
from google.cloud import bigquery
from loguru import logger

from package_folder.ml_logic.demo_data import generate_demo_data
from package_folder.params import (
    ALL_FEATURES,
    BQ_DATASET,
    DATA_SOURCE,
    DTYPES_RAW,
    GCP_PROJECT,
    LOCAL_DATA_PATH,
    TARGET_COLUMN,
)

# Clean dataset produced by `preprocess()` and consumed by `train()`.
# This is what makes the pipeline steps independent: `make run_train` works
# even if `make run_preprocess` ran in another shell.
PROCESSED_DATA_PATH = LOCAL_DATA_PATH / "processed" / "processed.csv"


# ==============================================================================
# 🔌 LOADING RAW DATA
# ==============================================================================
def get_raw_data(min_date: str | None = None, max_date: str | None = None) -> pd.DataFrame:
    """
    Load raw data from the source configured by DATA_SOURCE.

    - "demo"     : synthetic dataset, no network access (default)
    - "bigquery" : query against the project's raw table
    """
    if DATA_SOURCE == "demo":
        logger.info("Generating the demonstration dataset...")
        return generate_demo_data()

    # --- DATA_SOURCE == "bigquery" ---
    if not GCP_PROJECT or not BQ_DATASET:
        raise ValueError(
            "❌ DATA_SOURCE='bigquery' requires GCP_PROJECT and BQ_DATASET in your .env.\n"
            "   → Fill them in, or set DATA_SOURCE=demo to work offline."
        )

    # TODO: adapt this query to the columns of YOUR raw table, then return the
    #       result of get_data_with_cache():
    #
    #   query = f\"\"\"
    #       SELECT {', '.join(COLUMN_NAMES_RAW)}
    #       FROM `{GCP_PROJECT}.{BQ_DATASET}.raw_data`
    #       WHERE date BETWEEN '{min_date}' AND '{max_date}'
    #   \"\"\"
    #   cache_path = LOCAL_DATA_PATH / "raw" / f"raw_{min_date}_{max_date}.csv"
    #   return get_data_with_cache(GCP_PROJECT, query, cache_path)
    raise NotImplementedError(
        "❌ DATA_SOURCE='bigquery': the query against your raw table still has to be written.\n"
        "   → Complete the TODO above in ml_logic/data.py,\n"
        "     or set DATA_SOURCE=demo in your .env to use the demonstration dataset."
    )


def get_data_with_cache(
    gcp_project: str,
    query: str,
    cache_path: Path,
    data_has_header: bool = True,
) -> pd.DataFrame:
    """
    Retrieve `query` data from BigQuery, or from `cache_path` if the file exists.
    Store at `cache_path` if retrieved from BigQuery for future use.
    """
    if cache_path.is_file():
        logger.info("Load data from local CSV...")
        df = pd.read_csv(cache_path, header="infer" if data_has_header else None)
    else:
        logger.info("Load data from BigQuery server...")
        client = bigquery.Client(project=gcp_project)
        query_job = client.query(query)
        result = query_job.result()
        df = result.to_dataframe()

        # Store as CSV if the BQ query returned at least one valid line
        if df.shape[0] > 1:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(cache_path, header=data_has_header, index=False)

    logger.info(f"Data loaded, with shape {df.shape}")

    return df


# ==============================================================================
# 🧹 CLEANING
# ==============================================================================
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean raw data by:
    - assigning correct dtypes to each column
    - removing buggy or irrelevant rows
    """
    initial_rows = len(df)

    # 1. Explicit types: float32 instead of float64 halves the memory footprint
    #    on large volumes, with no useful precision lost here.
    #    Only PRESENT columns are cast: a user dataset may not follow this schema
    #    exactly.
    dtypes = {column: dtype for column, dtype in DTYPES_RAW.items() if column in df.columns}
    df = df.astype(dtypes)

    # 2. Strict duplicates
    df = df.drop_duplicates()

    # 3. Incomplete rows — only the schema columns are checked
    required_columns = [c for c in ALL_FEATURES + [TARGET_COLUMN] if c in df.columns]
    df = df.dropna(subset=required_columns)

    # 4. Outliers.
    #    One placeholder rule, and the only line of `clean_data` that assumes
    #    anything about the data: a non-positive target is treated as a
    #    data-entry artefact.
    #    ⚠️ Replace it with rules that match YOUR data. As written, a
    #    legitimately negative target would be dropped without warning.
    if TARGET_COLUMN in df.columns:
        df = df[df[TARGET_COLUMN] > 0]

    removed = initial_rows - len(df)
    logger.info(f"Data cleaned: {len(df)} rows kept, {removed} removed")

    return df.reset_index(drop=True)


# ==============================================================================
# 💾 PERSISTING THE CLEAN DATASET
# ==============================================================================
def save_processed_data(df: pd.DataFrame, path: Path | None = None) -> Path:
    """Persist the clean dataset for the following pipeline steps."""
    path = path or PROCESSED_DATA_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)

    logger.info(f"Processed data saved: {path} ({len(df)} rows)")
    return path


def load_processed_data(path: Path | None = None) -> pd.DataFrame:
    """Reload the clean dataset produced by `preprocess()`."""
    path = path or PROCESSED_DATA_PATH

    if not path.is_file():
        raise FileNotFoundError(f"❌ No processed data at {path}\n   → Run this first: make run_preprocess")

    return pd.read_csv(path)


def load_data_to_bq(
    data: pd.DataFrame,
    gcp_project: str,
    bq_dataset: str,
    table: str,
    truncate: bool,
) -> None:
    """
    - Save the DataFrame to BigQuery
    - Empty the table beforehand if `truncate` is True, append otherwise
    """
    assert isinstance(data, pd.DataFrame)
    full_table_name = f"{gcp_project}.{bq_dataset}.{table}"
    logger.info(f"Save data to BigQuery @ {full_table_name}...")

    # Fix column names to BigQuery accepted format (cannot start with a number)
    data.columns = [
        f"_{column}" if not str(column)[0].isalpha() and not str(column)[0] == "_" else str(column)
        for column in data.columns
    ]

    client = bigquery.Client()

    # Define write mode and schema
    write_mode = "WRITE_TRUNCATE" if truncate else "WRITE_APPEND"
    job_config = bigquery.LoadJobConfig(write_disposition=write_mode)

    logger.info(f"{'Write' if truncate else 'Append'} {full_table_name} ({data.shape[0]} rows)")

    # Load data
    job = client.load_table_from_dataframe(data, full_table_name, job_config=job_config)
    job.result()  # wait for the job to complete

    logger.info(f"Data saved to bigquery, with shape {data.shape}")
