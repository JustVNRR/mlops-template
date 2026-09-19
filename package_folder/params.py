import os
from pathlib import Path

from dotenv import load_dotenv

# ==============================================================================
# 📂 CHEMINS DU PROJET
# ==============================================================================
# 💡 Cette ligne trouve dynamiquement la racine du projet :
# (__file__ = params.py -> .parent = le package -> .parent = la racine)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

LOCAL_DATA_PATH = PROJECT_ROOT / "data"
LOCAL_REGISTRY_PATH = PROJECT_ROOT / "models"

# ==============================================================================
# 🔐 CHARGEMENT DU .ENV
# ==============================================================================
# Indispensable : sans cet appel, le package n'est importable que depuis un
# shell ayant DÉJÀ exporté les variables (make, direnv). Un `pytest` lancé à la
# main, ou un `python -c "import ..."`, échouait alors bien plus loin avec un
# NameError/ValueError incompréhensible, sans lien visible avec le .env manquant.
#
# `override=False` : une variable déjà présente dans l'environnement (make,
# direnv, CI, Docker) reste prioritaire sur le contenu du fichier.
load_dotenv(PROJECT_ROOT / ".env", override=False)


# ==============================================================================
# 🛠️ LECTURE ET VALIDATION DES VARIABLES
# ==============================================================================
def _require(name: str) -> str:
    """Lire une variable obligatoire, avec un message d'erreur actionnable."""
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise ValueError(
            f"❌ {name} est absente ou vide.\n"
            f"   → Crée ton fichier .env à partir du modèle fourni :\n"
            f"     cp .env.sample .env"
        )
    return value.strip()


def _optional(name: str) -> str | None:
    """Lire une variable facultative (chaîne vide normalisée en None)."""
    value = os.environ.get(name)
    return value.strip() if value and value.strip() else None


def _int(name: str, default: int | None = None) -> int | None:
    """Lire un entier, en distinguant clairement « absent » de « mal saisi »."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(
            f"❌ {name} doit être un entier, reçu : {raw!r}\n"
            f"   → Corrige {name} dans ton fichier .env."
        ) from None


##################  VARIABLES  ##################

# --- Pipeline ---
DATA_SIZE = _optional("DATA_SIZE")
CHUNK_SIZE = _int("CHUNK_SIZE", 100_000)
MODEL_TARGET = (_optional("MODEL_TARGET") or "local").lower()

# --- Infrastructure GCP ---
GCP_PROJECT = _optional("GCP_PROJECT")
GCP_REGION = _optional("GCP_REGION")
BQ_DATASET = _optional("BQ_DATASET")
BQ_REGION = _optional("BQ_REGION")
BUCKET_NAME = _optional("BUCKET_NAME")
INSTANCE = _optional("INSTANCE")

# --- MLflow & Prefect ---
MLFLOW_TRACKING_URI = _optional("MLFLOW_TRACKING_URI")
MLFLOW_EXPERIMENT = _optional("MLFLOW_EXPERIMENT")
MLFLOW_MODEL_NAME = _optional("MLFLOW_MODEL_NAME")
PREFECT_FLOW_NAME = _optional("PREFECT_FLOW_NAME")
PREFECT_LOG_LEVEL = _optional("PREFECT_LOG_LEVEL")
EVALUATION_START_DATE = _optional("EVALUATION_START_DATE")

# --- Docker & Artifact Registry ---
GAR_IMAGE = _optional("GAR_IMAGE")
GAR_MEMORY = _optional("GAR_MEMORY")

# --- Notifications (webhook) ---
NOTIFY_BASE_URL = _optional("NOTIFY_BASE_URL")
NOTIFY_CHANNEL = _optional("NOTIFY_CHANNEL")
NOTIFY_AUTHOR = _optional("NOTIFY_AUTHOR")

##################  VALIDATIONS  ##################
VALID_MODEL_TARGETS = ("local", "gcs", "mlflow")

if MODEL_TARGET not in VALID_MODEL_TARGETS:
    raise NameError(
        f"❌ MODEL_TARGET invalide : {MODEL_TARGET!r}\n"
        f"   Valeurs acceptées : {', '.join(VALID_MODEL_TARGETS)}\n"
        f"   → Corrige MODEL_TARGET dans ton fichier .env ('local' est un bon défaut)."
    )

##################  DATA SCHEMA (TODO)  #################
# TODO: Define the exact column names of the raw dataset (required for BigQuery schema or CSV parsing).
# COLUMN_NAMES_RAW = ['feature_1', 'feature_2', 'target_variable']

# TODO: Enforce raw data types to optimize memory usage (e.g., use float32 instead of float64).
# DTYPES_RAW = {
#     "feature_1": "float32",
#     "feature_2": "int8",
#     "target_variable": "int8"
# }

# TODO: Define the final data type for the matrices after preprocessing.
# (import numpy as np to use np.float32)
# DTYPES_PROCESSED = None
