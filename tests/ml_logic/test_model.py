import numpy as np
import pandas as pd
import pytest

from package_folder.ml_logic.data import clean_data, generate_toy_data
from package_folder.ml_logic.model import build_model, evaluate_model, train_model
from package_folder.ml_logic.preprocessor import build_preprocessor, preprocess_features
from package_folder.params import ALL_FEATURES, TARGET_COLUMN


@pytest.fixture(scope="module")
def dataset():
    """Clean demonstration dataset, shared by the tests in this module."""
    df = clean_data(generate_toy_data(400))
    return df[ALL_FEATURES], df[TARGET_COLUMN]


# ==============================================================================
# PREPROCESSOR
# ==============================================================================


def test_preprocessor_covers_every_feature():
    """
    Every feature declared in params.py must actually be transformed.

    A forgotten column would be silently ignored by the ColumnTransformer
    (`remainder="drop"`): the model would train without it, and no error would
    ever be raised.
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
# MODEL
# ==============================================================================


def test_model_embeds_its_preprocessor(dataset):
    """
    The model MUST be a complete Pipeline. A bare estimator would force you to
    reapply the transformation by hand on the API side — with different means
    and different categories than those learned during training.
    """
    X, y = dataset
    model, _ = train_model(build_model(), X, y)

    assert "preprocessor" in dict(model.named_steps)
    assert "regressor" in dict(model.named_steps)


def test_model_predicts_from_a_raw_dataframe(dataset):
    """
    Regression test: `model.predict()` must accept a RAW DataFrame, with no
    prior call to `preprocess_features()`. That is exactly what the API does.
    """
    X, y = dataset
    model, _ = train_model(build_model(), X, y)

    raw = pd.DataFrame([{"distance_km": 5.0, "passengers": 2, "hour": 14, "day_of_week": "monday"}])
    predictions = model.predict(raw)

    assert len(predictions) == 1
    assert predictions[0] > 0


def test_model_handles_a_category_never_seen_in_training(dataset):
    """
    An unknown category must not take the API down: `handle_unknown` produces a
    row of zeros rather than an exception.
    """
    X, y = dataset
    model, _ = train_model(build_model(), X, y)

    unseen = pd.DataFrame([{"distance_km": 5.0, "passengers": 2, "hour": 14, "day_of_week": "unknown_day"}])

    assert np.isfinite(model.predict(unseen)).all()


def test_model_learns_something(dataset):
    """
    The model must beat predicting the mean, otherwise the pipeline "works" end
    to end without learning anything.
    """
    X, y = dataset
    model, _ = train_model(build_model(), X, y)
    metrics = evaluate_model(model, X, y)

    baseline_mae = float(np.abs(y - y.mean()).mean())

    assert metrics["mae"] < baseline_mae


def test_model_params_are_forwarded_to_the_estimator():
    """`**model_params` from train() must reach build_model() then the estimator."""
    model = build_model(alpha=12.5)

    assert model.named_steps["regressor"].alpha == 12.5


# ==============================================================================
# METRICS
# ==============================================================================


def test_evaluate_model_returns_python_floats(dataset):
    """
    np.float64 values are not JSON-serialisable — yet save_results() writes the
    metrics as JSON (see registry._to_jsonable).
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
    assert metrics["rmse"] >= metrics["mae"]  # always true for a given series
