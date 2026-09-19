import numpy as np
import pandas as pd
from colorama import Fore, Style

from package_folder.ml_logic.data import (
    clean_data,
    get_raw_data,
    load_processed_data,
    save_processed_data,
)
from package_folder.ml_logic.model import build_model, evaluate_model, train_model
from package_folder.ml_logic.registry import (
    DEFAULT_ALIAS,
    load_model,
    mlflow_run,
    save_model,
    save_results,
)
from package_folder.params import ALL_FEATURES, TARGET_COLUMN


def preprocess(min_date: str | None = None, max_date: str | None = None) -> None:
    """
    Charger les données brutes, les nettoyer, et les persister pour les étapes
    suivantes du pipeline.

    `min_date` / `max_date` ne servent qu'à la source BigQuery ; le jeu de
    démonstration les ignore. Les rendre optionnels permet à `make run_preprocess`
    de fonctionner sans argument, tout en gardant le workflow Prefect capable
    de cibler une période précise.
    """
    print(Fore.MAGENTA + "\n⭐️ Use case: preprocess" + Style.RESET_ALL)

    raw_data = get_raw_data(min_date=min_date, max_date=max_date)
    data_cleaned = clean_data(raw_data)
    save_processed_data(data_cleaned)

    print("✅ preprocess() done \n")


@mlflow_run
def train(
    min_date: str | None = None,
    max_date: str | None = None,
    split_ratio: float = 0.2,
    **model_params,
) -> float:
    """
    - Load the processed dataset produced by `preprocess()`
    - Split it into train / validation
    - Fit the model, persist it and its metrics

    Return the validation MAE as a float.

    `**model_params` sont transmis à `build_model()` : alpha=… pour Ridge,
    learning_rate=… pour un réseau Keras. Le pipeline n'a pas à changer quand
    tu remplaces l'estimateur.
    """
    print(Fore.MAGENTA + "\n⭐️ Use case: train" + Style.RESET_ALL)

    data = load_processed_data()

    # Split reproductible. Sur une série temporelle, remplace-le par un split
    # CHRONOLOGIQUE (les lignes sont déjà ordonnées par date) — mélanger
    # reviendrait à entraîner sur le futur pour prédire le passé :
    #   train_size = int(len(data) * (1 - split_ratio))
    #   train_df, val_df = data.iloc[:train_size], data.iloc[train_size:]
    train_df = data.sample(frac=1 - split_ratio, random_state=42)
    val_df = data.drop(train_df.index)

    X_train, y_train = train_df[ALL_FEATURES], train_df[TARGET_COLUMN]
    X_val, y_val = val_df[ALL_FEATURES], val_df[TARGET_COLUMN]

    model = build_model(**model_params)
    model, _ = train_model(model, X_train, y_train)

    metrics = evaluate_model(model, X_val, y_val)

    save_model(model)
    save_results(
        params=dict(
            context="train",
            row_count=len(X_train),
            split_ratio=split_ratio,
            **model_params,
        ),
        metrics=metrics,
    )

    print("✅ train() done \n")
    return metrics["mae"]


@mlflow_run
def evaluate(
    min_date: str | None = None,
    max_date: str | None = None,
    stage: str = DEFAULT_ALIAS,
) -> float | None:
    """
    Evaluate the performance of the latest production model on processed data.

    Return the MAE as a float, or None si aucun modèle n'est disponible.
    """
    print(Fore.MAGENTA + "\n⭐️ Use case: evaluate" + Style.RESET_ALL)

    model = load_model(stage=stage)
    if model is None:
        print("❌ No model to evaluate — entraîne-en un d'abord : make run_train")
        return None

    data = load_processed_data()
    if data.empty:
        print("❌ No data to evaluate on — lance d'abord : make run_preprocess")
        return None

    X, y = data[ALL_FEATURES], data[TARGET_COLUMN]
    metrics = evaluate_model(model, X, y)

    save_results(
        params=dict(context="evaluate", row_count=len(X)),
        metrics=metrics,
    )

    print("✅ evaluate() done \n")
    return metrics["mae"]


def pred(X_pred: pd.DataFrame | None = None) -> np.ndarray | None:
    """
    Make a prediction using the latest trained model.

    Return the array of predictions, or None si aucun modèle n'est disponible.
    """
    print(Fore.MAGENTA + "\n⭐️ Use case: predict" + Style.RESET_ALL)

    if X_pred is None:
        # Exemple de charge utile : remplace-la par tes propres cas de test.
        X_pred = pd.DataFrame(
            [
                {"distance_km": 5.0, "passengers": 2, "hour": 14, "day_of_week": "monday"},
                {"distance_km": 12.5, "passengers": 1, "hour": 23, "day_of_week": "saturday"},
            ]
        )

    model = load_model()
    if model is None:
        print("❌ No model to predict with — entraîne-en un d'abord : make run_train")
        return None

    # Aucun appel à preprocess_features() ici : le modèle est un Pipeline qui
    # embarque DÉJÀ le préprocesseur entraîné. Le réappliquer à la main
    # utiliserait d'autres moyennes et d'autres catégories que l'entraînement.
    y_pred = model.predict(X_pred)

    print(f"✅ prediction done: {y_pred}\n")
    return y_pred


if __name__ == "__main__":
    preprocess()
    train()
    evaluate()
    pred()
