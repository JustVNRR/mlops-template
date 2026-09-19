import numpy as np
import pandas as pd
import pytest

from package_folder.ml_logic.data import (
    clean_data,
    generate_toy_data,
    load_processed_data,
    save_processed_data,
)
from package_folder.params import ALL_FEATURES, DTYPES_RAW, TARGET_COLUMN

# ==============================================================================
# DEMONSTRATION DATASET
# ==============================================================================


def test_generate_toy_data_has_expected_schema():
    df = generate_toy_data(n_samples=100)

    assert len(df) == 100
    assert list(df.columns) == ALL_FEATURES + [TARGET_COLUMN]


def test_generate_toy_data_is_reproducible():
    """
    Same seed -> same data. Without this, no metric is comparable from one run
    to the next, and the CI cannot assert anything stable.
    """
    pd.testing.assert_frame_equal(generate_toy_data(50, seed=1), generate_toy_data(50, seed=1))


def test_generate_toy_data_varies_across_seeds():
    assert not generate_toy_data(50, seed=1).equals(generate_toy_data(50, seed=2))


def test_generate_toy_data_has_no_missing_values():
    assert not generate_toy_data(200).isna().any().any()


def test_generate_toy_data_has_variability():
    """A constant dataset would make any metric meaningless."""
    df = generate_toy_data(200)

    assert df[TARGET_COLUMN].std() > 0
    assert df["day_of_week"].nunique() > 1
    assert df[TARGET_COLUMN].min() > 0


# ==============================================================================
# CLEANING
# ==============================================================================


def test_clean_data_removes_duplicates_and_missing_values():
    df = generate_toy_data(50)

    # 5 EXACT duplicates (rows 50-54 = rows 0-4)…
    dirty = pd.concat([df, df.iloc[:5]], ignore_index=True)
    # …and 1 missing value on a NON-duplicated row. Putting the NaN on row 0
    # would make it differ from its own duplicate, and drop_duplicates would
    # then remove only 4 of them: the test would be measuring something other
    # than what its name claims.
    dirty.loc[10, TARGET_COLUMN] = np.nan

    cleaned = clean_data(dirty)

    assert len(cleaned) == 49  # 55 - 5 duplicates - 1 missing value
    assert not cleaned.isna().any().any()


def test_clean_data_applies_declared_dtypes():
    """The types from params.py cut memory usage and expose a broken schema."""
    cleaned = clean_data(generate_toy_data(50))

    for column, expected_dtype in DTYPES_RAW.items():
        assert str(cleaned[column].dtype) == expected_dtype, column


def test_clean_data_drops_domain_outliers():
    """Zero or negative distance, zero fare: data-entry artefacts."""
    df = generate_toy_data(50)
    df.loc[0, "distance_km"] = 0
    df.loc[1, "distance_km"] = -5
    df.loc[2, TARGET_COLUMN] = 0

    assert len(clean_data(df)) == 47


def test_clean_data_resets_index():
    """A gappy index would break row-by-row selections downstream."""
    cleaned = clean_data(generate_toy_data(30))

    assert list(cleaned.index) == list(range(len(cleaned)))


def test_clean_data_is_idempotent():
    """Cleaning an already clean dataset must remove nothing."""
    once = clean_data(generate_toy_data(100))

    assert len(clean_data(once)) == len(once)


# ==============================================================================
# PERSISTENCE BETWEEN STEPS
# ==============================================================================


def test_save_and_load_processed_data_roundtrip(tmp_path):
    df = generate_toy_data(20)
    path = tmp_path / "processed.csv"

    save_processed_data(df, path=path)
    loaded = load_processed_data(path=path)

    assert len(loaded) == len(df)
    assert list(loaded.columns) == list(df.columns)
    assert path.is_file()


def test_save_processed_data_creates_missing_directories(tmp_path):
    """`make run_preprocess` must work on a fresh clone, with no mkdir."""
    path = tmp_path / "deep" / "processed.csv"

    save_processed_data(generate_toy_data(5), path=path)

    assert path.is_file()


def test_load_processed_data_error_points_to_the_fix(tmp_path):
    """The message must name the command to run, not just 'file not found'."""
    with pytest.raises(FileNotFoundError, match="run_preprocess"):
        load_processed_data(path=tmp_path / "missing.csv")
