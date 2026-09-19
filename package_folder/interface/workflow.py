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
    Pointer l'alias MLflow sur la dernière version enregistrée.

    Remplace l'ancienne transition « Staging → Production » (API "model
    stages", obsolète depuis MLflow 2.x — voir registry.mlflow_set_alias).
    """
    return mlflow_set_alias(alias=alias)


@task
def notify(old_mae: float | None, new_mae: float) -> None:
    """
    Notify about the performance.
    """
    # Sans webhook configuré, on prévient et on s'arrête là : une notification
    # impossible à envoyer ne doit pas faire échouer un pipeline réussi.
    if not NOTIFY_BASE_URL or not NOTIFY_CHANNEL:
        print("ℹ️  Notifications désactivées (NOTIFY_BASE_URL / NOTIFY_CHANNEL vides dans .env).")
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
    Build the Prefect workflow for the pipeline. It should:
        - preprocess 1 month of new data, starting from EVALUATION_START_DATE
        - compute `old_mae` by evaluating the current production model on this new month period
        - compute `new_mae` by re-training, then evaluating the new model on this new month period
        - if the new one is better than the old one, promote it
        - send a notification with the outcome
    """
    if not EVALUATION_START_DATE:
        raise ValueError(
            "❌ EVALUATION_START_DATE est vide : impossible de délimiter la période d'évaluation.\n"
            "   → Renseigne-la dans ton .env au format YYYY-MM-DD (ex. 2024-01-01)."
        )

    min_date = EVALUATION_START_DATE
    max_date = str(datetime.strptime(min_date, "%Y-%m-%d") + relativedelta(months=1)).split()[0]
    print(f"📅 Période d'évaluation : {min_date} → {max_date}")

    # 1. Préparer les nouvelles données
    preprocess_new_data.submit(min_date=min_date, max_date=max_date).result()

    # 2. Évaluer le modèle ACTUELLEMENT en production, AVANT de réentraîner.
    #    L'ancienne version soumettait ces deux étapes EN PARALLÈLE : or
    #    `train()` sauvegarde un nouveau modèle, que `evaluate()` pouvait
    #    alors charger à la place de l'ancien. On comparait le nouveau modèle
    #    à lui-même, et la promotion était décidée sur une comparaison fausse.
    old_mae = evaluate_production_model.submit(min_date=min_date, max_date=max_date).result()

    # 3. Réentraîner
    new_mae = re_train.submit(min_date=min_date, max_date=max_date, split_ratio=0.2).result()

    # 4. Promouvoir si le nouveau modèle fait mieux
    if old_mae is None:
        print(f"ℹ️  Aucun modèle en production : le nouveau (MAE {new_mae:.3f}) devient la référence.")
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
