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
# JEU DE DÉMONSTRATION
# ==============================================================================

def test_generate_toy_data_has_expected_schema():
    df = generate_toy_data(n_samples=100)

    assert len(df) == 100
    assert list(df.columns) == ALL_FEATURES + [TARGET_COLUMN]


def test_generate_toy_data_is_reproducible():
    """
    Même graine -> mêmes données. Sans cela, aucune métrique n'est comparable
    d'une exécution à l'autre, et la CI ne peut rien affirmer de stable.
    """
    pd.testing.assert_frame_equal(generate_toy_data(50, seed=1), generate_toy_data(50, seed=1))


def test_generate_toy_data_varies_across_seeds():
    assert not generate_toy_data(50, seed=1).equals(generate_toy_data(50, seed=2))


def test_generate_toy_data_has_no_missing_values():
    assert not generate_toy_data(200).isna().any().any()


def test_generate_toy_data_has_variability():
    """Un jeu constant rendrait toute métrique trompeuse."""
    df = generate_toy_data(200)

    assert df[TARGET_COLUMN].std() > 0
    assert df["day_of_week"].nunique() > 1
    assert df[TARGET_COLUMN].min() > 0


# ==============================================================================
# NETTOYAGE
# ==============================================================================

def test_clean_data_removes_duplicates_and_missing_values():
    df = generate_toy_data(50)

    # 5 doublons EXACTS (lignes 50-54 = lignes 0-4)…
    dirty = pd.concat([df, df.iloc[:5]], ignore_index=True)
    # …et 1 valeur manquante sur une ligne NON dupliquée. Mettre le NaN sur la
    # ligne 0 la rendrait différente de son doublon, et drop_duplicates n'en
    # retirerait plus que 4 : le test mesurerait autre chose que son intitulé.
    dirty.loc[10, TARGET_COLUMN] = np.nan

    cleaned = clean_data(dirty)

    assert len(cleaned) == 49  # 55 - 5 doublons - 1 valeur manquante
    assert not cleaned.isna().any().any()


def test_clean_data_applies_declared_dtypes():
    """Les types de params.py limitent la mémoire et détectent un schéma rompu."""
    cleaned = clean_data(generate_toy_data(50))

    for column, expected_dtype in DTYPES_RAW.items():
        assert str(cleaned[column].dtype) == expected_dtype, column


def test_clean_data_drops_domain_outliers():
    """Distance nulle/négative ou tarif nul : artefacts de saisie."""
    df = generate_toy_data(50)
    df.loc[0, "distance_km"] = 0
    df.loc[1, "distance_km"] = -5
    df.loc[2, TARGET_COLUMN] = 0

    assert len(clean_data(df)) == 47


def test_clean_data_resets_index():
    """Un index troué casserait les sélections ligne à ligne en aval."""
    cleaned = clean_data(generate_toy_data(30))

    assert list(cleaned.index) == list(range(len(cleaned)))


def test_clean_data_is_idempotent():
    """Nettoyer un jeu déjà propre ne doit rien retirer."""
    once = clean_data(generate_toy_data(100))

    assert len(clean_data(once)) == len(once)


# ==============================================================================
# PERSISTANCE ENTRE ÉTAPES
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
    """`make run_preprocess` doit fonctionner sur un clone frais, sans mkdir."""
    path = tmp_path / "profond" / "processed.csv"

    save_processed_data(generate_toy_data(5), path=path)

    assert path.is_file()


def test_load_processed_data_error_points_to_the_fix(tmp_path):
    """Le message doit indiquer la commande à lancer, pas juste « fichier absent »."""
    with pytest.raises(FileNotFoundError, match="run_preprocess"):
        load_processed_data(path=tmp_path / "inexistant.csv")
