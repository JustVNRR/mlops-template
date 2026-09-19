from pathlib import Path

import numpy as np
import pandas as pd
from colorama import Fore, Style
from google.cloud import bigquery

from package_folder.params import (
    ALL_FEATURES,
    BQ_DATASET,
    DATA_SIZE,
    DATA_SOURCE,
    DTYPES_RAW,
    GCP_PROJECT,
    LOCAL_DATA_PATH,
    TARGET_COLUMN,
)

# Jeu de données nettoyé produit par `preprocess()` et consommé par `train()`.
# C'est ce qui rend les étapes du pipeline indépendantes : `make run_train`
# fonctionne même si `make run_preprocess` a tourné dans un autre shell.
PROCESSED_DATA_PATH = LOCAL_DATA_PATH / "processed" / "processed.csv"

DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


# ==============================================================================
# 🧪 JEU DE DONNÉES DE DÉMONSTRATION
# ==============================================================================
def _n_samples_from_data_size() -> int:
    """Traduire DATA_SIZE ('1k', '200k', 'all', …) en nombre de lignes."""
    if not DATA_SIZE:
        return 2_000

    size = str(DATA_SIZE).strip().lower()
    if size == "all":
        return 50_000
    if size.endswith("k"):
        return int(float(size[:-1]) * 1_000)
    return int(size)


def generate_toy_data(n_samples: int | None = None, seed: int = 42) -> pd.DataFrame:
    """
    Générer un jeu de données synthétique de type « course de taxi ».

    Objectif : rendre le template exécutable de bout en bout (`make run_all`)
    sans compte GCP et sans fichier de données à versionner. La relation est
    volontairement simple (linéaire + bruit gaussien) pour que le modèle de
    référence atteigne une MAE stable et comparable d'une exécution à l'autre.

    ⚠️ À remplacer par ta vraie source de données : voir `get_raw_data`.
    """
    n_samples = n_samples if n_samples is not None else _n_samples_from_data_size()
    rng = np.random.default_rng(seed)  # reproductible : mêmes données à chaque run

    distance_km = rng.uniform(0.5, 30.0, n_samples)
    passengers = rng.integers(1, 5, n_samples)
    hour = rng.integers(0, 24, n_samples)
    day_of_week = rng.choice(DAY_NAMES, n_samples)

    is_night = (hour < 6) | (hour >= 22)
    is_weekend = np.isin(day_of_week, ["saturday", "sunday"])

    fare = (
        3.0                              # prise en charge
        + 1.8 * distance_km              # tarif au kilomètre
        + 0.4 * passengers               # supplément passager
        + 2.5 * is_night                 # majoration de nuit
        + 1.5 * is_weekend               # majoration week-end
        + rng.normal(0, 1.5, n_samples)  # bruit irréductible
    )

    return pd.DataFrame(
        {
            "distance_km": distance_km,
            "passengers": passengers,
            "hour": hour,
            "day_of_week": day_of_week,
            TARGET_COLUMN: fare,
        }
    )


# ==============================================================================
# 🔌 CHARGEMENT DES DONNÉES BRUTES
# ==============================================================================
def get_raw_data(min_date: str | None = None, max_date: str | None = None) -> pd.DataFrame:
    """
    Charger les données brutes depuis la source configurée par DATA_SOURCE.

    - "toy"      : jeu synthétique, aucun accès réseau (défaut)
    - "bigquery" : requête sur la table brute du projet GCP
    """
    if DATA_SOURCE == "toy":
        print(Fore.BLUE + "\nGenerating toy dataset..." + Style.RESET_ALL)
        return generate_toy_data()

    # --- DATA_SOURCE == "bigquery" ---
    if not GCP_PROJECT or not BQ_DATASET:
        raise ValueError(
            "❌ DATA_SOURCE='bigquery' exige GCP_PROJECT et BQ_DATASET dans ton .env.\n"
            "   → Renseigne-les, ou passe DATA_SOURCE=toy pour travailler hors ligne."
        )

    # TODO: adapte cette requête aux colonnes de TA table brute, puis renvoie
    #       le résultat de get_data_with_cache() :
    #
    #   query = f\"\"\"
    #       SELECT {', '.join(COLUMN_NAMES_RAW)}
    #       FROM `{GCP_PROJECT}.{BQ_DATASET}.raw_data`
    #       WHERE date BETWEEN '{min_date}' AND '{max_date}'
    #   \"\"\"
    #   cache_path = LOCAL_DATA_PATH / "raw" / f"raw_{min_date}_{max_date}.csv"
    #   return get_data_with_cache(GCP_PROJECT, query, cache_path)
    raise NotImplementedError(
        "❌ DATA_SOURCE='bigquery' : la requête sur ta table brute reste à écrire.\n"
        "   → Complète le TODO ci-dessus dans ml_logic/data.py,\n"
        "     ou passe DATA_SOURCE=toy dans ton .env pour utiliser le jeu de démonstration."
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
        print(Fore.BLUE + "\nLoad data from local CSV..." + Style.RESET_ALL)
        df = pd.read_csv(cache_path, header="infer" if data_has_header else None)
    else:
        print(Fore.BLUE + "\nLoad data from BigQuery server..." + Style.RESET_ALL)
        client = bigquery.Client(project=gcp_project)
        query_job = client.query(query)
        result = query_job.result()
        df = result.to_dataframe()

        # Store as CSV if the BQ query returned at least one valid line
        if df.shape[0] > 1:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(cache_path, header=data_has_header, index=False)

    print(f"✅ Data loaded, with shape {df.shape}")

    return df


# ==============================================================================
# 🧹 NETTOYAGE
# ==============================================================================
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean raw data by:
    - assigning correct dtypes to each column
    - removing buggy or irrelevant rows
    """
    initial_rows = len(df)

    # 1. Types explicites : float32 au lieu de float64 divise l'empreinte
    #    mémoire par deux sur les gros volumes, sans perte utile ici.
    #    On ne caste QUE les colonnes présentes : un dataset utilisateur peut
    #    ne pas suivre exactement ce schéma.
    dtypes = {column: dtype for column, dtype in DTYPES_RAW.items() if column in df.columns}
    df = df.astype(dtypes)

    # 2. Doublons stricts
    df = df.drop_duplicates()

    # 3. Lignes incomplètes — on ne teste que les colonnes du schéma
    required_columns = [c for c in ALL_FEATURES + [TARGET_COLUMN] if c in df.columns]
    df = df.dropna(subset=required_columns)

    # 4. Valeurs aberrantes.
    #    TODO: adapte ces règles à ton domaine. Ici : une course à distance
    #    nulle ou négative, ou un tarif nul, sont des artefacts de saisie.
    if "distance_km" in df.columns:
        df = df[df["distance_km"] > 0]
    if TARGET_COLUMN in df.columns:
        df = df[df[TARGET_COLUMN] > 0]

    removed = initial_rows - len(df)
    print(f"✅ Data cleaned: {len(df)} rows kept, {removed} removed")

    return df.reset_index(drop=True)


# ==============================================================================
# 💾 PERSISTANCE DU JEU NETTOYÉ
# ==============================================================================
def save_processed_data(df: pd.DataFrame, path: Path | None = None) -> Path:
    """Persister le jeu nettoyé pour les étapes suivantes du pipeline."""
    path = path or PROCESSED_DATA_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)

    print(f"✅ Processed data saved: {path} ({len(df)} rows)")
    return path


def load_processed_data(path: Path | None = None) -> pd.DataFrame:
    """Recharger le jeu nettoyé produit par `preprocess()`."""
    path = path or PROCESSED_DATA_PATH

    if not path.is_file():
        raise FileNotFoundError(
            f"❌ Aucune donnée prétraitée dans {path}\n"
            f"   → Lance d'abord : make run_preprocess"
        )

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
    print(Fore.BLUE + f"\nSave data to BigQuery @ {full_table_name}...:" + Style.RESET_ALL)

    # Fix column names to BigQuery accepted format (cannot start with a number)
    data.columns = [
        f"_{column}" if not str(column)[0].isalpha() and not str(column)[0] == "_" else str(column)
        for column in data.columns
    ]

    client = bigquery.Client()

    # Define write mode and schema
    write_mode = "WRITE_TRUNCATE" if truncate else "WRITE_APPEND"
    job_config = bigquery.LoadJobConfig(write_disposition=write_mode)

    print(f"\n{'Write' if truncate else 'Append'} {full_table_name} ({data.shape[0]} rows)")

    # Load data
    job = client.load_table_from_dataframe(data, full_table_name, job_config=job_config)
    job.result()  # wait for the job to complete

    print(f"✅ Data saved to bigquery, with shape {data.shape}")
