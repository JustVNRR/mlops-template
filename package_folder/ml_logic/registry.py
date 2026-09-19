import functools
import json
import pickle
import time
from pathlib import Path
from typing import Any

import mlflow
import numpy as np
from colorama import Fore, Style
from mlflow.tracking import MlflowClient

from package_folder.params import (
    LOCAL_REGISTRY_PATH,
    MLFLOW_EXPERIMENT,
    MLFLOW_MODEL_NAME,
    MLFLOW_TRACKING_URI,
    MODEL_TARGET,
)

# ==============================================================================
# 🗂️ ARBORESCENCE DU REGISTRE LOCAL
# ==============================================================================
#   models/                  <- LOCAL_REGISTRY_PATH
#   ├── models/              <- poids des modèles, horodatés <timestamp>.pkl
#   ├── params/              <- hyperparamètres,      <timestamp>.json
#   └── metrics/             <- métriques,            <timestamp>.json
#
# Le dossier est créé automatiquement à la première sauvegarde : rien à faire
# à la main, et le pipeline fonctionne sur un clone frais.
MODELS_DIR = LOCAL_REGISTRY_PATH / "models"
PARAMS_DIR = LOCAL_REGISTRY_PATH / "params"
METRICS_DIR = LOCAL_REGISTRY_PATH / "metrics"

# Alias MLflow désignant le modèle servi en production (voir plus bas).
DEFAULT_ALIAS = "champion"


# ==============================================================================
# 🛠️ HELPERS
# ==============================================================================
def _to_jsonable(obj: Any) -> Any:
    """
    Convertit récursivement les types numpy (et Path) en types Python natifs.

    Indispensable : un `metrics` calculé par scikit-learn contient des
    `np.float64`, que `json.dump` refuse avec un laconique
    "Object of type float64 is not JSON serializable".
    """
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, np.generic):
        return obj.item()  # np.float64 -> float, np.int64 -> int
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, Path):
        return str(obj)
    return obj


def _write_json(path: Path, payload: dict) -> None:
    """Écrire un JSON lisible (indenté), en créant l'arborescence au besoin."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(_to_jsonable(payload), file, indent=2, ensure_ascii=False)
    print(f"✅ Saved: {path}")


def _latest_file(directory: Path, pattern: str = "*") -> Path | None:
    """
    Renvoyer le fichier le plus RÉCEMMENT MODIFIÉ correspondant à `pattern`.

    On trie par date de modification, jamais par nom. Un tri alphabétique
    (l'ancien `sorted(paths)[-1]`) sélectionne 'zzz.pkl' plutôt que le dernier
    entraînement, et devient silencieusement faux dès qu'un fichier ne suit pas
    la convention <timestamp>.pkl — par exemple un `best_model.pkl`.
    """
    if not directory.is_dir():
        return None

    files = [path for path in directory.glob(pattern) if path.is_file()]
    if not files:
        return None

    return max(files, key=lambda path: path.stat().st_mtime)


# ==============================================================================
# 💾 SAUVEGARDE
# ==============================================================================
def save_results(params: dict | None = None, metrics: dict | None = None) -> None:
    """
    Persist params & metrics locally on the hard drive.
    If MODEL_TARGET='mlflow', also persist them on MLflow.
    """
    timestamp = time.strftime("%Y%m%d-%H%M%S")

    # 1. Sauvegarde locale en JSON.
    #    L'ancienne version utilisait pickle : illisible à l'œil, non diffable
    #    dans git, et impossible à relire depuis une autre version de Python.
    if params is not None:
        _write_json(PARAMS_DIR / f"{timestamp}.json", params)

    if metrics is not None:
        _write_json(METRICS_DIR / f"{timestamp}.json", metrics)

    print(Fore.GREEN + f"✅ Results saved locally ({LOCAL_REGISTRY_PATH})" + Style.RESET_ALL)

    # 2. Sauvegarde sur MLflow
    #    Rappel : log_params/log_metrics n'ont de sens qu'À L'INTÉRIEUR d'un run
    #    actif, ce dont se charge le décorateur @mlflow_run sur train()/evaluate().
    if MODEL_TARGET == "mlflow":
        if params is not None:
            mlflow.log_params(params)
        if metrics is not None:
            mlflow.log_metrics(metrics)
        print("✅ Results saved on MLflow")


def save_model(model: Any) -> None:
    """
    Persist trained model locally on the hard drive.
    - if MODEL_TARGET='gcs', also persist it in the GCS bucket
    - if MODEL_TARGET='mlflow', also persist it on MLflow
    """
    # On valide la cible AVANT d'écrire quoi que ce soit : sinon on laisserait
    # un modèle sur le disque tout en levant une exception, ce qui donne un
    # succès partiel très difficile à diagnostiquer.
    if MODEL_TARGET == "gcs":
        raise NotImplementedError(
            "❌ MODEL_TARGET='gcs' : l'upload vers Cloud Storage n'est pas implémenté.\n"
            "   → Implémente-le ici (google.cloud.storage), ou passe MODEL_TARGET=local dans ton .env."
        )

    if MODEL_TARGET == "mlflow":
        raise NotImplementedError(
            "❌ MODEL_TARGET='mlflow' : l'enregistrement du modèle n'est pas implémenté.\n"
            "   → Décommente le bloc mlflow.<framework>.log_model ci-dessous, ou passe MODEL_TARGET=local dans ton .env."
        )

    # --- MODEL_TARGET == "local" ---
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    model_path = MODELS_DIR / f"{timestamp}.pkl"

    # TODO: Addapter la sérialisation au framework choisi (Keras .keras,
    # PyTorch .pt, XGBoost .json...) — pickle convient à scikit-learn.
    model_path.parent.mkdir(parents=True, exist_ok=True)
    with open(model_path, "wb") as file:
        pickle.dump(model, file)

    print(Fore.GREEN + f"✅ Model saved locally: {model_path}" + Style.RESET_ALL)

    # TODO (MODEL_TARGET='mlflow' — décommenter dans la branche dédiée) :
    # mlflow.sklearn.log_model(
    #     sk_model=model,
    #     artifact_path="model",
    #     registered_model_name=MLFLOW_MODEL_NAME,
    # )


# ==============================================================================
# 📥 CHARGEMENT
# ==============================================================================
def load_model(stage: str = DEFAULT_ALIAS) -> Any | None:
    """
    Return a saved model:
    - locally the most recent one (by modification time)
    - or from GCS (most recent one) if MODEL_TARGET == 'gcs'
    - or from MLflow, by alias, if MODEL_TARGET == 'mlflow'

    `stage` est conservé pour la compatibilité de signature ; il désigne
    désormais l'ALIAS MLflow (voir mlflow_set_alias).
    """
    if MODEL_TARGET == "local":
        print(Fore.BLUE + "\nLoad latest model from local registry..." + Style.RESET_ALL)

        model_path = _latest_file(MODELS_DIR, pattern="*.pkl")
        if model_path is None:
            print(f"❌ No model found in {MODELS_DIR}\n   → Entraîne-en un d'abord : `make run_train`")
            return None

        print(f"✅ Loading model: {model_path.name}")
        with open(model_path, "rb") as file:
            return pickle.load(file)

    if MODEL_TARGET == "gcs":
        raise NotImplementedError(
            "❌ MODEL_TARGET='gcs' : le téléchargement depuis Cloud Storage n'est pas implémenté.\n"
            "   → Implémente-le ici (google.cloud.storage), ou passe MODEL_TARGET=local dans ton .env."
        )

    if MODEL_TARGET == "mlflow":
        raise NotImplementedError(
            "❌ MODEL_TARGET='mlflow' : le chargement depuis MLflow n'est pas implémenté.\n"
            "   → Utilise mlflow.<framework>.load_model avec l'alias, ou passe MODEL_TARGET=local dans ton .env."
        )

    return None


# ==============================================================================
# 🏷️ ALIAS MLFLOW (remplace les "model stages")
# ==============================================================================
def mlflow_latest_version() -> str | None:
    """Renvoie la version la plus élevée enregistrée sous MLFLOW_MODEL_NAME."""
    if not MLFLOW_MODEL_NAME:
        return None

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = MlflowClient()

    versions = client.search_model_versions(f"name='{MLFLOW_MODEL_NAME}'")
    if not versions:
        return None

    return max(versions, key=lambda version: int(version.version)).version


def mlflow_set_alias(version: str | int | None = None, alias: str = DEFAULT_ALIAS) -> None:
    """
    Pointer `alias` sur une version donnée du modèle enregistré.

    Remplace l'API "model stages" (`transition_model_version_stage`), obsolète :
    les stages Staging/Production sont dépréciés depuis MLflow 2.x au profit des
    ALIAS. Un alias est plus souple — une même version peut en porter plusieurs,
    et promouvoir un modèle n'efface plus l'historique du précédent.

    Si `version` est None, la dernière version enregistrée est utilisée.
    """
    if not MLFLOW_MODEL_NAME:
        raise ValueError(
            "❌ MLFLOW_MODEL_NAME est vide : impossible d'identifier le modèle dans le registre.\n"
            "   → Renseigne MLFLOW_MODEL_NAME dans ton .env."
        )

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = MlflowClient()

    if version is None:
        version = mlflow_latest_version()
        if version is None:
            print(f"❌ No registered model named {MLFLOW_MODEL_NAME}")
            return None

    client.set_registered_model_alias(
        name=MLFLOW_MODEL_NAME,
        alias=alias,
        version=str(version),
    )

    print(Fore.GREEN + f"✅ {MLFLOW_MODEL_NAME} version {version} is now aliased as '{alias}'" + Style.RESET_ALL)
    return None


# ==============================================================================
# 🔁 DÉCORATEUR DE RUN MLFLOW
# ==============================================================================
def mlflow_run(func):
    """
    Generic function to log params and results to MLflow along with universal auto-logging.

    Args:
        - func (function): Function you want to run within the MLflow run
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Un run resté ouvert (exception précédente, cellule de notebook
        # interrompue...) ferait échouer start_run(). On le ferme au lieu de
        # laisser remonter une erreur qui n'a rien à voir avec l'appel courant.
        if mlflow.active_run():
            mlflow.end_run()

        # Sans URI explicite, MLflow écrit dans ./mlruns (ignoré par git) :
        # pratique pour développer en local sans serveur de tracking.
        if MLFLOW_TRACKING_URI:
            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

        if MLFLOW_EXPERIMENT:
            mlflow.set_experiment(experiment_name=MLFLOW_EXPERIMENT)

        with mlflow.start_run():
            # autolog() couvre TensorFlow/Keras, scikit-learn, XGBoost, PyTorch…
            # sans code spécifique au framework.
            mlflow.autolog()
            results = func(*args, **kwargs)

        print("✅ mlflow_run auto-log done")

        return results

    return wrapper
