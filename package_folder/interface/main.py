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
    Load the raw data, clean it, and persist it for the following steps.

    `min_date` / `max_date` only matter for the BigQuery source; the
    demonstration dataset ignores them. Keeping them optional lets
    `make run_preprocess` run without arguments, while still allowing the
    Prefect workflow to target a specific period.
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

    `**model_params` are forwarded to `build_model()`: alpha=… for Ridge,
    learning_rate=… for a Keras network. The pipeline does not have to change
    when you swap the estimator.
    """
    print(Fore.MAGENTA + "\n⭐️ Use case: train" + Style.RESET_ALL)

    data = load_processed_data()

    # Reproducible split. On a time series, replace it with a CHRONOLOGICAL
    # split (rows are already ordered by date) — shuffling would mean training
    # on the future to predict the past:
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

    Return the MAE as a float, or None if no model is available.
    """
    print(Fore.MAGENTA + "\n⭐️ Use case: evaluate" + Style.RESET_ALL)

    model = load_model(stage=stage)
    if model is None:
        print("❌ No model to evaluate — train one first: make run_train")
        return None

    data = load_processed_data()
    if data.empty:
        print("❌ No data to evaluate on — run this first: make run_preprocess")
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

    Return the array of predictions, or None if no model is available.
    """
    print(Fore.MAGENTA + "\n⭐️ Use case: predict" + Style.RESET_ALL)

    if X_pred is None:
        # Sample payload: replace it with your own test cases.
        X_pred = pd.DataFrame(
            [
                {"distance_km": 5.0, "passengers": 2, "hour": 14, "day_of_week": "monday"},
                {"distance_km": 12.5, "passengers": 1, "hour": 23, "day_of_week": "saturday"},
            ]
        )

    model = load_model()
    if model is None:
        print("❌ No model to predict with — train one first: make run_train")
        return None

    # No call to preprocess_features() here: the model is a Pipeline that
    # ALREADY embeds the fitted preprocessor. Applying it again by hand would
    # use different means and different categories than training did.
    y_pred = model.predict(X_pred)

    print(f"✅ prediction done: {y_pred}\n")
    return y_pred


if __name__ == "__main__":
    preprocess()
    train()
    evaluate()
    pred()
