import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from package_folder.params import CATEGORICAL_FEATURES, NUMERIC_FEATURES


def build_preprocessor() -> ColumnTransformer:
    """
    Build the feature transformation pipeline (NOT fitted).

    ⚠️ A preprocessor must be FITTED on the training data only, then reused
    as-is to validate, evaluate and predict. That is why `build_model()` wraps
    it in a scikit-learn Pipeline: it then gets serialised along with the model,
    and `model.predict()` applies the learned transformation automatically.

    TODO: adapt the transformations to your columns (imputation, time features,
    geohash…) — the column lists come from params.py.
    """
    return ColumnTransformer(
        transformers=[
            ("numeric", StandardScaler(), NUMERIC_FEATURES),
            # handle_unknown="ignore": in production, a category never seen
            # during training yields a row of zeros instead of raising — an API
            # should not go down over that.
            ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ],
        remainder="drop",  # any column outside the schema is ignored
    )


def preprocess_features(X: pd.DataFrame) -> np.ndarray:
    """
    Transform raw features into a numeric matrix.

    ⚠️ STATELESS FUNCTION: it fits a brand new preprocessor on `X`. Handy to
    explore a dataset or test a transformation, but do NOT use it to serve a
    model: the means, standard deviations and categories it learns would not be
    the ones from training, which yields silently wrong predictions (no error
    is ever raised).

    In production, call `model.predict(X)` directly: the model is a Pipeline
    that already embeds this preprocessor.
    """
    return build_preprocessor().fit_transform(X)
