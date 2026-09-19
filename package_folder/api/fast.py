from contextlib import asynccontextmanager
from typing import Annotated, Any

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from package_folder.api.schemas import (
    BatchPredictionResponse,
    PredictionResponse,
    TripFeatures,
)
from package_folder.ml_logic.registry import DEFAULT_ALIAS, load_model


# ==============================================================================
# 🚀 DÉMARRAGE
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Charger le modèle au démarrage — sans faire échouer ce démarrage.

    L'ancienne version appelait `load_model()` et faisait `assert model is not
    None` AU NIVEAU DU MODULE. Conséquence : sans modèle entraîné, importer ce
    fichier levait une exception. L'API ne démarrait donc pas, et surtout
    AUCUN test ne pouvait s'exécuter — pas même celui de la route `/`.

    Ici, l'API démarre toujours : `/predict` répond 503 tant qu'aucun modèle
    n'est chargé, avec la cause exacte de l'échec. `app.state.model_error`
    conserve le message pour le diagnostic.
    """
    app.state.model = None
    app.state.model_error = None

    try:
        app.state.model = load_model()
    except Exception as error:  # cible non implémentée, fichier corrompu, credentials…
        app.state.model_error = f"{type(error).__name__}: {error}"

    if app.state.model is None:
        print(
            "⚠️  Aucun modèle chargé : /predict répondra 503.\n"
            "   → Entraîne-en un (`make run_train`) ou recharge-le via PUT /model."
        )
    else:
        print("✅ Modèle chargé au démarrage.")

    yield

    app.state.model = None


app = FastAPI(
    title="MLOps Template API",
    description="API de prédiction du modèle entraîné par ce pipeline.",
    version="1.0.0",
    lifespan=lifespan,
)

# ⚠️ Piège CORS classique : allow_origins=["*"] ET allow_credentials=True est une
# combinaison INVALIDE. La spécification interdit d'envoyer des identifiants
# vers une origine générique ; les navigateurs rejettent alors la réponse, sans
# que le serveur ne signale quoi que ce soit.
# Ici, l'API n'utilise pas de cookie d'authentification : on peut garder "*".
# Si tu ajoutes de l'authentification par cookie, remplace "*" par la liste
# explicite de tes origines ET passe allow_credentials à True.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# 🔌 DÉPENDANCES
# ==============================================================================
def get_model(request: Request) -> Any:
    """
    Récupérer le modèle chargé, ou refuser la requête proprement.

    On lit `app.state` à chaque appel (et non une variable globale) : c'est ce
    qui permet à PUT /model de remplacer le modèle à chaud, sans redémarrage.
    """
    model = getattr(request.app.state, "model", None)
    if model is None:
        detail = "Aucun modèle disponible. Entraîne-en un (`make run_train`) ou recharge-le via PUT /model."
        if getattr(request.app.state, "model_error", None):
            detail += f" Cause du dernier échec : {request.app.state.model_error}"
        raise HTTPException(status_code=503, detail=detail)

    return model


# ==============================================================================
# 🩺 SANTÉ
# ==============================================================================
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """
    Silence 404 errors for favicon requests automatically sent by web browsers.
    """
    return Response(status_code=204)


@app.get("/")
def root() -> dict:
    """
    Root health-check endpoint.
    """
    return {"greeting": "Hello"}


@app.get("/model")
def model_info(request: Request) -> dict:
    """
    État du modèle actuellement servi.

    Utile en production pour vérifier qu'un déploiement a bien chargé un
    modèle, sans avoir à provoquer une prédiction.
    """
    loaded = getattr(request.app.state, "model", None) is not None

    return {
        "model_loaded": loaded,
        "model_error": getattr(request.app.state, "model_error", None),
    }


# ==============================================================================
# 🔄 CYCLE DE VIE DU MODÈLE
# ==============================================================================
@app.put("/model")
def update_model(stage: str = DEFAULT_ALIAS) -> dict:
    """
    Reload or swap the active machine learning model in application state on-the-fly.

    This endpoint allows hot-swapping the model loaded in memory without
    requiring an API process restart or causing service downtime.

    Args:
        stage (str, optional): ALIAS MLflow du modèle à charger. Les « stages »
                               (Staging/Production) sont obsolètes depuis
                               MLflow 2.x — voir registry.mlflow_set_alias.
                               Ignoré quand MODEL_TARGET=local, où le modèle
                               le plus récent est toujours chargé.

    Returns:
        dict: Confirmation payload detailing update status and active model stage.

    Raises:
        HTTPException: 404 if the target model cannot be found or loaded.
    """
    try:
        new_model = load_model(stage=stage)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading model for stage '{stage}': {error}",
        ) from error

    if new_model is None:
        raise HTTPException(
            status_code=404,
            detail=f"Model for stage '{stage}' could not be found or loaded from registry.",
        )

    # Hot-swap the loaded model stored in FastAPI application state
    app.state.model = new_model
    app.state.model_error = None

    return {
        "status": "success",
        "message": f"Model successfully updated to stage '{stage}'.",
    }


# ==============================================================================
# 🔮 PRÉDICTION
# ==============================================================================
@app.get("/predict", response_model=PredictionResponse)
def predict(
    params: Annotated[TripFeatures, Query()],
    model: Annotated[Any, Depends(get_model)],
) -> PredictionResponse:
    """
    Prédire pour une course.

    Les paramètres sont validés par Pydantic AVANT d'atteindre le modèle :
    une requête incomplète ou aberrante reçoit un 422 explicite.

    ⚠️ Aucun appel à preprocess_features() ici : le modèle est un Pipeline qui
    embarque déjà le préprocesseur entraîné. Le réappliquer à la main
    utiliserait d'autres moyennes et d'autres catégories que l'entraînement.
    """
    X_pred = pd.DataFrame([params.model_dump()])
    y_pred = model.predict(X_pred)

    return PredictionResponse(fare=float(y_pred[0]))


@app.post("/predict_batch", response_model=BatchPredictionResponse)
def predict_batch(
    inputs: list[TripFeatures],
    model: Annotated[Any, Depends(get_model)],
) -> BatchPredictionResponse:
    """
    Prédire pour un lot de courses en une seule requête JSON.

    Le corps attendu est une LISTE d'objets TripFeatures :
        [{"distance_km": 5.0, ...}, {"distance_km": 12.5, ...}]
    """
    if not inputs:
        raise HTTPException(status_code=422, detail="Le lot est vide : fournis au moins une course.")

    X_pred = pd.DataFrame([item.model_dump() for item in inputs])
    y_pred = model.predict(X_pred)

    return BatchPredictionResponse(fares=[float(value) for value in y_pred])
