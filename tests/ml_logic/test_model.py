import numpy as np
import pandas as pd
import pytest

from package_folder.ml_logic.data import clean_data, generate_toy_data
from package_folder.ml_logic.model import build_model, evaluate_model, train_model
from package_folder.ml_logic.preprocessor import build_preprocessor, preprocess_features
from package_folder.params import ALL_FEATURES, TARGET_COLUMN


@pytest.fixture(scope="module")
def dataset():
    """Jeu de démonstration nettoyé, partagé par les tests de ce module."""
    df = clean_data(generate_toy_data(400))
    return df[ALL_FEATURES], df[TARGET_COLUMN]


# ==============================================================================
# PRÉPROCESSEUR
# ==============================================================================


def test_preprocessor_covers_every_feature():
    """
    Chaque feature déclarée dans params.py doit être effectivement transformée.

    Une colonne oubliée serait silencieusement ignorée par le ColumnTransformer
    (`remainder="drop"`) : le modèle s'entraînerait sans elle, sans qu'aucune
    erreur ne soit levée.
    """
    preprocessor = build_preprocessor()
    covered = {column for _, _, columns in preprocessor.transformers for column in columns}

    assert covered == set(ALL_FEATURES)


def test_preprocess_features_returns_a_numeric_matrix(dataset):
    X, _ = dataset
    transformed = preprocess_features(X)

    assert isinstance(transformed, np.ndarray)
    assert transformed.shape[0] == len(X)
    assert np.isfinite(transformed).all()


# ==============================================================================
# MODÈLE
# ==============================================================================


def test_model_embeds_its_preprocessor(dataset):
    """
    Le modèle DOIT être un Pipeline complet. Un estimateur nu obligerait à
    réappliquer la transformation à la main côté API — avec d'autres moyennes
    et d'autres catégories que celles apprises à l'entraînement.
    """
    X, y = dataset
    model, _ = train_model(build_model(), X, y)

    assert "preprocessor" in dict(model.named_steps)
    assert "regressor" in dict(model.named_steps)


def test_model_predicts_from_a_raw_dataframe(dataset):
    """
    Régression : `model.predict()` doit accepter un DataFrame BRUT, sans appel
    préalable à `preprocess_features()`. C'est exactement ce que fait l'API.
    """
    X, y = dataset
    model, _ = train_model(build_model(), X, y)

    raw = pd.DataFrame([{"distance_km": 5.0, "passengers": 2, "hour": 14, "day_of_week": "monday"}])
    predictions = model.predict(raw)

    assert len(predictions) == 1
    assert predictions[0] > 0


def test_model_handles_a_category_never_seen_in_training(dataset):
    """
    Une catégorie inconnue ne doit pas faire tomber l'API : `handle_unknown`
    produit une ligne de zéros plutôt qu'une exception.
    """
    X, y = dataset
    model, _ = train_model(build_model(), X, y)

    unseen = pd.DataFrame([{"distance_km": 5.0, "passengers": 2, "hour": 14, "day_of_week": "jour_inconnu"}])

    assert np.isfinite(model.predict(unseen)).all()


def test_model_learns_something(dataset):
    """
    Le modèle doit faire mieux que de prédire la moyenne, sinon le pipeline
    « fonctionne » de bout en bout sans rien apprendre.
    """
    X, y = dataset
    model, _ = train_model(build_model(), X, y)
    metrics = evaluate_model(model, X, y)

    baseline_mae = float(np.abs(y - y.mean()).mean())

    assert metrics["mae"] < baseline_mae


def test_model_params_are_forwarded_to_the_estimator():
    """`**model_params` de train() doit atteindre build_model() puis l'estimateur."""
    model = build_model(alpha=12.5)

    assert model.named_steps["regressor"].alpha == 12.5


# ==============================================================================
# MÉTRIQUES
# ==============================================================================


def test_evaluate_model_returns_python_floats(dataset):
    """
    Des np.float64 ne sont pas sérialisables en JSON — or save_results() écrit
    les métriques en JSON (voir registry._to_jsonable).
    """
    X, y = dataset
    model, _ = train_model(build_model(), X, y)
    metrics = evaluate_model(model, X, y)

    assert type(metrics["mae"]) is float
    assert type(metrics["rmse"]) is float


def test_evaluate_model_reports_both_metrics(dataset):
    X, y = dataset
    model, _ = train_model(build_model(), X, y)
    metrics = evaluate_model(model, X, y)

    assert set(metrics) == {"mae", "rmse"}
    assert metrics["rmse"] >= metrics["mae"]  # toujours vrai pour une même série
