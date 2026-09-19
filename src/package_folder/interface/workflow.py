from datetime import datetime

import requests
from dateutil.relativedelta import relativedelta
from prefect import flow, task

from package_folder.interface.main import evaluate, preprocess, train
from package_folder.ml_logic.registry import DEFAULT_ALIAS, mlflow_set_alias
from package_folder.params import (
    EVALUATION_START_DATE,
    MAE_THRESHOLD,
    NOTIFY_AUTHOR,
    NOTIFY_BASE_URL,
    NOTIFY_CHANNEL,
    PREFECT_FLOW_NAME,
)


@task
def preprocess_new_data(min_date: str, max_date: str) -> None:
    return preprocess(min_date=min_date, max_date=max_date)


@task
def evaluate_production_model(min_date: str, max_date: str) -> float | None:
    return evaluate(min_date=min_date, max_date=max_date)


@task
def re_train(min_date: str, max_date: str, split_ratio: float) -> float:
    return train(min_date=min_date, max_date=max_date, split_ratio=split_ratio)


@task
def promote(alias: str = DEFAULT_ALIAS) -> None:
    """
    Point the MLflow alias at the latest registered version.

    Aliases are the current mechanism: the model-stages API (Staging →
    Production) is obsolete since MLflow 2.x. See `registry.mlflow_set_alias`.
    """
    return mlflow_set_alias(alias=alias)


@task
def notify(old_mae: float | None, new_mae: float) -> None:
    """
    Notify about the performance.
    """
    # With no webhook configured, say so and stop there: a notification that
    # cannot be sent must not fail an otherwise successful pipeline.
    if not NOTIFY_BASE_URL or not NOTIFY_CHANNEL:
        print("ℹ️  Notifications disabled (NOTIFY_BASE_URL / NOTIFY_CHANNEL empty in .env).")
        return

    url = f"{NOTIFY_BASE_URL}/{NOTIFY_CHANNEL}/messages"

    if new_mae < MAE_THRESHOLD:
        content = f"🚀 New model replacing old in production with MAE: {new_mae} the Old MAE was: {old_mae}"
    elif old_mae is not None and old_mae < MAE_THRESHOLD:
        content = f"✅ Old model still good enough: Old MAE: {old_mae} - New MAE: {new_mae}"
    else:
        content = f"🚨 No model good enough: Old MAE: {old_mae} - New MAE: {new_mae}"

    data = dict(author=NOTIFY_AUTHOR, content=content)

    response = requests.post(url, data=data)
    response.raise_for_status()


@flow(name=PREFECT_FLOW_NAME)
def train_flow() -> dict:
    """
    Run the full model-refresh cycle as a Prefect flow:

    - preprocess one month of new data, starting from EVALUATION_START_DATE
    - compute `old_mae`: the production model, evaluated over that period
    - compute `new_mae`: the retrained model, evaluated over the same period
    - promote the new model if it beats the old one
    - notify with the outcome
    """
    if not EVALUATION_START_DATE:
        raise ValueError(
            "❌ EVALUATION_START_DATE is empty: cannot delimit the evaluation period.\n"
            "   → Set it in your .env using the YYYY-MM-DD format (e.g. 2024-01-01)."
        )

    min_date = EVALUATION_START_DATE
    max_date = str(datetime.strptime(min_date, "%Y-%m-%d") + relativedelta(months=1)).split()[0]
    print(f"📅 Evaluation period: {min_date} → {max_date}")

    # 1. Prepare the new data
    preprocess_new_data.submit(min_date=min_date, max_date=max_date).result()

    # 2. Evaluate the model CURRENTLY in production, BEFORE retraining.
    #    The order is what makes this comparison valid: `train()` saves a new
    #    model, and an `evaluate()` run afterwards would load that one — comparing
    #    the new model against itself and basing the promotion on it.
    old_mae = evaluate_production_model.submit(min_date=min_date, max_date=max_date).result()

    # 3. Retrain
    new_mae = re_train.submit(min_date=min_date, max_date=max_date, split_ratio=0.2).result()

    # 4. Promote if the new model does better
    if old_mae is None:
        print(f"ℹ️  No model in production: the new one (MAE {new_mae:.3f}) becomes the reference.")
        should_promote = True
    elif new_mae < old_mae:
        print(f"🚀 New model replacing old in production with MAE: {new_mae} the Old MAE was: {old_mae}")
        should_promote = True
    else:
        print(f"✅ Old model kept in place with MAE: {old_mae}. The new MAE was: {new_mae}")
        should_promote = False

    if should_promote:
        promote.submit(alias=DEFAULT_ALIAS).result()

    notify.submit(old_mae, new_mae).result()

    return {
        "min_date": min_date,
        "max_date": max_date,
        "old_mae": old_mae,
        "new_mae": new_mae,
        "promoted": should_promote,
    }


if __name__ == "__main__":
    train_flow()
