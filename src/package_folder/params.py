import os
from pathlib import Path

from dotenv import load_dotenv


# ==============================================================================
# 📂 PROJECT PATHS
# ==============================================================================
# The project root is found by walking UP until pyproject.toml appears, rather
# than by counting `.parent` levels. Counting is what breaks silently: under the
# src layout this file sits at src/<package>/params.py, so a hardcoded
# `parent.parent` resolves to `src/` and quietly writes data/ and models/ there —
# with nothing raised.
def _find_project_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate

    raise RuntimeError(
        f"❌ Cannot locate the project root from {__file__}: no pyproject.toml "
        f"found in any parent directory.\n"
        f"   → This usually means the package was installed NON-editable (copied "
        f"into site-packages).\n"
        f"     Run `uv sync`: it installs the project in editable mode."
    )


PROJECT_ROOT = _find_project_root()

LOCAL_DATA_PATH = PROJECT_ROOT / "data"
LOCAL_REGISTRY_PATH = PROJECT_ROOT / "models"

# ==============================================================================
# 🔐 LOADING THE .ENV FILE
# ==============================================================================
# This call is essential: without it, the package is only importable from a
# shell that has ALREADY exported the variables (make, direnv). Running pytest
# by hand, or `python -c "import ..."`, would fail much further down with an
# inscrutable NameError/ValueError showing no trace of the missing .env file.
#
# `override=False`: variables already present in the environment (make, direnv,
# CI, Docker) take precedence over the file contents.
load_dotenv(PROJECT_ROOT / ".env", override=False)


# ==============================================================================
# 🛠️ READING AND VALIDATING VARIABLES
# ==============================================================================
def _require(name: str) -> str:
    """Read a mandatory variable, with an actionable error message."""
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise ValueError(
            f"❌ {name} is missing or empty.\n"
            f"   → Create your .env file from the provided template:\n"
            f"     cp .env.sample .env"
        )
    return value.strip()


def _optional(name: str) -> str | None:
    """Read an optional variable (empty strings normalised to None)."""
    value = os.environ.get(name)
    return value.strip() if value and value.strip() else None


def _int(name: str, default: int | None = None) -> int | None:
    """Read an integer, clearly telling 'absent' apart from 'malformed'."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"❌ {name} must be an integer, got: {raw!r}\n   → Fix {name} in your .env file.") from None


def _float(name: str, default: float | None = None) -> float | None:
    """Read a number, with the same error handling as `_int`."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"❌ {name} must be a number, got: {raw!r}\n   → Fix {name} in your .env file.") from None


##################  VARIABLES  ##################

# --- Pipeline ---
DATA_SIZE = _optional("DATA_SIZE")
CHUNK_SIZE = _int("CHUNK_SIZE", 100_000)
MODEL_TARGET = (_optional("MODEL_TARGET") or "local").lower()
# Source of the raw data:
#   "toy"      -> synthetic dataset generated in memory, no cloud account needed
#   "bigquery" -> query against BigQuery, requires GCP_PROJECT and BQ_DATASET
DATA_SOURCE = (_optional("DATA_SOURCE") or "toy").lower()

# --- GCP infrastructure ---
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
VALID_DATA_SOURCES = ("toy", "bigquery")

if MODEL_TARGET not in VALID_MODEL_TARGETS:
    raise NameError(
        f"❌ Invalid MODEL_TARGET: {MODEL_TARGET!r}\n"
        f"   Accepted values: {', '.join(VALID_MODEL_TARGETS)}\n"
        f"   → Fix MODEL_TARGET in your .env file ('local' is a good default)."
    )

if DATA_SOURCE not in VALID_DATA_SOURCES:
    raise NameError(
        f"❌ Invalid DATA_SOURCE: {DATA_SOURCE!r}\n"
        f"   Accepted values: {', '.join(VALID_DATA_SOURCES)}\n"
        f"   → Fix DATA_SOURCE in your .env file ('toy' requires no cloud account)."
    )

##################  DATA SCHEMA  #################
# Schema of the DEMONSTRATION dataset (see ml_logic/demo_data.py). Reorienting
# the template means rewriting this block and that module: no other file reads
# a column name.
#
# ⚠️ Replace these with the columns of YOUR dataset. They drive the cleaning
#    step, the preprocessor and the API contract.
TARGET_COLUMN = "target"

# The features are named after the preprocessing branch each one feeds, not
# after any business meaning — these two lists are what decide how the
# ColumnTransformer treats each column.
NUMERIC_FEATURES = ["numeric_feature_1", "numeric_feature_2", "numeric_feature_3"]
CATEGORICAL_FEATURES = ["categorical_feature_1"]
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

COLUMN_NAMES_RAW = ALL_FEATURES + [TARGET_COLUMN]

# Types enforced when loading: this cuts memory usage and makes a file whose
# schema has changed fail immediately rather than silently downstream.
DTYPES_RAW = {
    "numeric_feature_1": "float32",
    "numeric_feature_2": "int8",
    "numeric_feature_3": "int8",
    "categorical_feature_1": "category",
    TARGET_COLUMN: "float32",
}

##################  BUSINESS THRESHOLDS  #################
# MAE below which a model is considered acceptable by the promotion workflow
# (see interface/workflow.py). Configurable through .env: a quality target
# changes often, the code should not have to.
MAE_THRESHOLD = _float("MAE_THRESHOLD", 3.0)
