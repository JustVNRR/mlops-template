import json
import os
import pickle

import numpy as np
import pytest

from package_folder.ml_logic import registry


@pytest.fixture
def local_registry(tmp_path, monkeypatch):
    """
    Redirige le registre local vers un dossier temporaire.

    Sans cette isolation, les tests écriraient dans le vrai models/ du projet
    et pollueraient le registre de l'utilisateur.
    """
    monkeypatch.setattr(registry, "LOCAL_REGISTRY_PATH", tmp_path)
    monkeypatch.setattr(registry, "MODELS_DIR", tmp_path / "models")
    monkeypatch.setattr(registry, "PARAMS_DIR", tmp_path / "params")
    monkeypatch.setattr(registry, "METRICS_DIR", tmp_path / "metrics")
    monkeypatch.setattr(registry, "MODEL_TARGET", "local")
    return tmp_path


def _write_model(path, payload, mtime):
    """Déposer un faux modèle en forçant sa date de modification."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as file:
        pickle.dump(payload, file)
    os.utime(path, (mtime, mtime))


# ==============================================================================
# MODÈLES
# ==============================================================================


def test_save_model_then_load_model_roundtrip(local_registry):
    registry.save_model({"poids": [1, 2, 3]})

    assert registry.load_model() == {"poids": [1, 2, 3]}


def test_load_model_picks_most_recent_by_mtime(local_registry):
    """
    Régression : l'ancien code faisait `sorted(paths)[-1]`, donc un tri
    ALPHABÉTIQUE. Il sélectionnait 'zzz.pkl' même quand 'aaa.pkl' était
    l'entraînement le plus récent — un bug silencieux, qui ne se voit que
    le jour où les noms ne suivent plus la convention <timestamp>.pkl.
    """
    _write_model(local_registry / "models" / "zzz.pkl", "ancien", mtime=1_000_000)
    _write_model(local_registry / "models" / "aaa.pkl", "recent", mtime=2_000_000)

    # Un tri alphabétique renverrait "ancien".
    assert registry.load_model() == "recent"


def test_load_model_ignores_non_pickle_files(local_registry):
    """Un fichier parasite dans models/ ne doit pas être chargé comme modèle."""
    _write_model(local_registry / "models" / "vrai.pkl", "le bon", mtime=1_000_000)
    (local_registry / "models" / "notes.txt").write_text("pas un modèle")

    assert registry.load_model() == "le bon"


def test_load_model_returns_none_on_empty_registry(local_registry):
    """Un registre vide renvoie None au lieu de lever une exception."""
    assert registry.load_model() is None


def test_load_model_creates_nothing_when_directory_missing(local_registry):
    """Aucun modèle et pas même de dossier : comportement identique."""
    assert not (local_registry / "models").exists()
    assert registry.load_model() is None


# ==============================================================================
# RÉSULTATS (params / metrics)
# ==============================================================================


def test_save_results_writes_readable_json(local_registry):
    registry.save_results(params={"learning_rate": 0.001}, metrics={"mae": 2.5})

    params_file = next((local_registry / "params").glob("*.json"))
    metrics_file = next((local_registry / "metrics").glob("*.json"))

    assert json.loads(params_file.read_text()) == {"learning_rate": 0.001}
    assert json.loads(metrics_file.read_text()) == {"mae": 2.5}


def test_save_results_converts_numpy_types(local_registry):
    """
    scikit-learn renvoie des np.float64, que json.dump refuse. La conversion
    doit être transparente, sinon save_results explose sur des métriques
    parfaitement valides.
    """
    registry.save_results(
        metrics={
            "mae": np.float64(2.5),
            "rmse": np.float32(3.5),
            "row_count": np.int64(100),
            "confusion": np.array([[1, 2], [3, 4]]),
            "nested": {"score": np.float64(0.9)},
        }
    )

    metrics_file = next((local_registry / "metrics").glob("*.json"))
    written = json.loads(metrics_file.read_text())

    assert written == {
        "mae": 2.5,
        "rmse": 3.5,
        "row_count": 100,
        "confusion": [[1, 2], [3, 4]],
        "nested": {"score": 0.9},
    }
    assert isinstance(written["mae"], float)
    assert isinstance(written["row_count"], int)


def test_save_results_accepts_partial_payloads(local_registry):
    """params et metrics sont indépendamment facultatifs."""
    registry.save_results(params={"a": 1})
    assert list((local_registry / "metrics").glob("*.json")) == []

    registry.save_results(metrics={"b": 2})
    assert list((local_registry / "params").glob("*.json")) != []


# ==============================================================================
# CIBLES NON IMPLÉMENTÉES
# ==============================================================================


@pytest.mark.parametrize("target", ["gcs", "mlflow"])
def test_save_model_raises_on_unimplemented_target(local_registry, monkeypatch, target):
    """Une cible non implémentée doit échouer clairement, pas en silence."""
    monkeypatch.setattr(registry, "MODEL_TARGET", target)

    with pytest.raises(NotImplementedError, match=target):
        registry.save_model(object())


@pytest.mark.parametrize("target", ["gcs", "mlflow"])
def test_save_model_writes_nothing_on_unimplemented_target(local_registry, monkeypatch, target):
    """
    La validation de la cible intervient AVANT l'écriture : sinon on laisserait
    un modèle sur le disque tout en levant une exception (succès partiel).
    """
    monkeypatch.setattr(registry, "MODEL_TARGET", target)

    with pytest.raises(NotImplementedError):
        registry.save_model(object())

    assert not (local_registry / "models").exists()
