from typing import Any

import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sklearn.pipeline import Pipeline

from package_folder.ml_logic.preprocessor import build_preprocessor

# Alias générique : le template accepte n'importe quel estimateur exposant
# .fit() / .predict() (scikit-learn, XGBoost, un modèle Keras…).
Model = Any


def build_model(alpha: float = 1.0, **kwargs) -> Pipeline:
    """
    Instantiate the model.
    (For neural networks, this includes initializing weights and compiling).

    ⚠️ Le modèle renvoyé est un Pipeline scikit-learn COMPLET : préprocesseur
    + estimateur. C'est ce qui garantit qu'à la prédiction, les features
    subissent exactement la même transformation qu'à l'entraînement. Un modèle
    sérialisé sans son préprocesseur prédit faux, sans jamais lever d'erreur.

    TODO: remplace Ridge par ton estimateur (RandomForestRegressor, XGBoost,
    un réseau Keras…). Le reste du pipeline n'a pas à changer : `**kwargs`
    transmet les hyperparamètres depuis `train()`.
    """
    return Pipeline(
        steps=[
            ("preprocessor", build_preprocessor()),
            ("regressor", Ridge(alpha=alpha, **kwargs)),
        ]
    )


def train_model(
    model: Model,
    X: pd.DataFrame,
    y: pd.Series,
    **kwargs,
) -> tuple[Model, dict]:
    """
    Fit the model and return a tuple (fitted_model, history_or_metrics).
    """
    model.fit(X, y)

    # scikit-learn n'expose pas d'historique d'entraînement (contrairement à
    # Keras, dont `history.history` serait renvoyé ici).
    return model, {}


def evaluate_model(
    model: Model,
    X: pd.DataFrame,
    y: pd.Series,
    **kwargs,
) -> dict:
    """
    Evaluate trained model performance on the dataset.
    Returns a dictionary of metrics.
    """
    y_pred = model.predict(X)

    # float() explicite : scikit-learn renvoie des np.float64, que json.dump
    # refuse (voir registry._to_jsonable, qui les convertit de toute façon).
    return {
        "mae": float(mean_absolute_error(y, y_pred)),
        "rmse": float(root_mean_squared_error(y, y_pred)),
    }
