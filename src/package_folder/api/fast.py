from contextlib import asynccontextmanager
from typing import Annotated, Any

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from package_folder.api.schemas import (
    BatchPredictionResponse,
    ModelFeatures,
    PredictionResponse,
)
from package_folder.ml_logic.registry import DEFAULT_ALIAS, load_model


# ==============================================================================
# 🚀 STARTUP
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Load the model at startup, without letting that startup fail.

    The API must start even with no trained model: `/predict` then answers 503
    with the exact cause, while every other route stays reachable. That is what
    keeps the service deployable and testable independently of training.
    `app.state.model_error` holds the failure message for diagnosis.
    """
    app.state.model = None
    app.state.model_error = None

    try:
        app.state.model = load_model()
    except Exception as error:  # unimplemented target, corrupt file, credentials…
        app.state.model_error = f"{type(error).__name__}: {error}"

    if app.state.model is None:
        logger.warning(
            "No model loaded: /predict will answer 503 - train one (`make run_train`) or reload it through PUT /model"
        )
    else:
        logger.info("Model loaded at startup.")

    yield

    app.state.model = None


app = FastAPI(
    title="MLOps Template API",
    description="Prediction API for the model trained by this pipeline.",
    version="1.0.0",
    lifespan=lifespan,
)

# ⚠️ Classic CORS trap: allow_origins=["*"] AND allow_credentials=True is an
# INVALID combination. The spec forbids sending credentials to a wildcard
# origin; browsers then reject the response, while the server reports nothing.
# This API uses no authentication cookie, so "*" is fine.
# If you add cookie-based authentication, replace "*" with the explicit list of
# your origins AND set allow_credentials to True.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# 🔌 DEPENDENCIES
# ==============================================================================
def get_model(request: Request) -> Any:
    """
    Fetch the loaded model, or reject the request cleanly.

    `app.state` is read on every call (rather than a module-level global): that
    is what lets PUT /model swap the model at runtime, without a restart.
    """
    model = getattr(request.app.state, "model", None)
    if model is None:
        detail = "No model available. Train one (`make run_train`) or reload it through PUT /model."
        if getattr(request.app.state, "model_error", None):
            detail += f" Last failure cause: {request.app.state.model_error}"
        raise HTTPException(status_code=503, detail=detail)

    return model


# ==============================================================================
# 🩺 HEALTH
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
    return {"status": "ok", "message": "API is running"}


@app.get("/model")
def model_info(request: Request) -> dict:
    """
    State of the model currently being served.

    Useful in production to check that a deployment did load a model, without
    having to trigger a prediction.
    """
    loaded = getattr(request.app.state, "model", None) is not None

    return {
        "model_loaded": loaded,
        "model_error": getattr(request.app.state, "model_error", None),
    }


# ==============================================================================
# 🔄 MODEL LIFECYCLE
# ==============================================================================
@app.put("/model")
def update_model(stage: str = DEFAULT_ALIAS) -> dict:
    """
    Hot-swap the model held in memory, with no service restart.

    `stage` is the MLflow alias of the model to load; it is ignored when
    MODEL_TARGET=local, where the most recent model always wins. Answers 404
    when the model cannot be found and 500 when loading it fails.
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
# 🔮 PREDICTION
# ==============================================================================
@app.get("/predict", response_model=PredictionResponse)
def predict(
    params: Annotated[ModelFeatures, Query()],
    model: Annotated[Any, Depends(get_model)],
) -> PredictionResponse:
    """
    Predict for a single row.

    The parameters are validated by Pydantic BEFORE reaching the model: an
    incomplete or nonsensical request receives an explicit 422.

    ⚠️ No call to preprocess_features() here: the model is a Pipeline that
    already embeds the fitted preprocessor. Reapplying it by hand would use
    different means and different categories than training did.
    """
    X_pred = pd.DataFrame([params.model_dump()])
    y_pred = model.predict(X_pred)

    return PredictionResponse(prediction=float(y_pred[0]))


@app.post("/predict_batch", response_model=BatchPredictionResponse)
def predict_batch(
    inputs: list[ModelFeatures],
    model: Annotated[Any, Depends(get_model)],
) -> BatchPredictionResponse:
    """
    Predict for a batch of rows in a single JSON request.

    The body is expected to be a LIST of ModelFeatures objects:
        [{"numeric_feature_1": 5.0, ...}, {"numeric_feature_1": 12.5, ...}]
    """
    if not inputs:
        raise HTTPException(status_code=422, detail="Empty batch: provide at least one row.")

    X_pred = pd.DataFrame([item.model_dump() for item in inputs])
    y_pred = model.predict(X_pred)

    return BatchPredictionResponse(predictions=[float(value) for value in y_pred])
