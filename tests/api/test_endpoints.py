import pytest
from httpx import ASGITransport, AsyncClient

from package_folder.api.fast import app
from package_folder.ml_logic import registry
from package_folder.ml_logic.data import clean_data, generate_toy_data
from package_folder.ml_logic.model import build_model
from package_folder.params import ALL_FEATURES, TARGET_COLUMN

# Valid payload, matching api/schemas.TripFeatures
TEST_PARAMS = {"distance_km": 5.0, "passengers": 2, "hour": 14, "day_of_week": "monday"}

# Field returned by /predict (see api/schemas.PredictionResponse)
EXPECTED_PREDICT_KEY = "fare"


@pytest.fixture
async def client(tmp_path, monkeypatch):
    """
    HTTP client wired to the ASGI app, with a model trained on the fly.

    Three precautions, each fixing a real trap:

    1. The registry is redirected to a temporary directory: the test does not
       depend on a prior `make run_train` and does not pollute the real registry.
    2. The model is trained right here (a few hundred rows, a few milliseconds):
       the suite is self-contained, hence runnable in CI.
    3. The `lifespan` is run EXPLICITLY. `ASGITransport` does not trigger
       startup events: without this `async with`, `app.state.model` would stay
       empty and every prediction would answer 503.
    """
    monkeypatch.setattr(registry, "MODEL_TARGET", "local")
    monkeypatch.setattr(registry, "MODELS_DIR", tmp_path / "models")

    data = clean_data(generate_toy_data(200))
    model = build_model()
    model.fit(data[ALL_FEATURES], data[TARGET_COLUMN])
    registry.save_model(model)

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http_client:
            yield http_client


# ==============================================================================
# HEALTH
# ==============================================================================


async def test_root_is_up(client):
    response = await client.get("/")

    assert response.status_code == 200


async def test_root_returns_greeting(client):
    response = await client.get("/")

    assert response.json() == {"greeting": "Hello"}


async def test_model_reports_being_loaded(client):
    """
    /model must expose the real state of the served model: that is what lets
    you check a deployment without triggering a prediction.
    """
    response = await client.get("/model")

    assert response.status_code == 200
    assert response.json()["model_loaded"] is True


# ==============================================================================
# /predict
# ==============================================================================


async def test_predict_is_up(client):
    response = await client.get("/predict", params=TEST_PARAMS)

    assert response.status_code == 200


async def test_predict_is_dict(client):
    response = await client.get("/predict", params=TEST_PARAMS)

    assert isinstance(response.json(), dict)


async def test_predict_has_expected_key(client):
    response = await client.get("/predict", params=TEST_PARAMS)

    assert EXPECTED_PREDICT_KEY in response.json(), f"Key '{EXPECTED_PREDICT_KEY}' missing from the response"


async def test_predict_val_is_float(client):
    response = await client.get("/predict", params=TEST_PARAMS)

    assert isinstance(response.json()[EXPECTED_PREDICT_KEY], float)


async def test_predict_rejects_invalid_input(client):
    """
    Pydantic validation must reject a nonsensical input BEFORE the model.
    Without it, a negative distance would produce a silently wrong prediction
    instead of an error.
    """
    response = await client.get("/predict", params={**TEST_PARAMS, "distance_km": -1})

    assert response.status_code == 422


async def test_predict_rejects_missing_field(client):
    incomplete = {key: value for key, value in TEST_PARAMS.items() if key != "day_of_week"}

    response = await client.get("/predict", params=incomplete)

    assert response.status_code == 422


# ==============================================================================
# /predict_batch
# ==============================================================================


async def test_predict_batch_returns_one_value_per_input(client):
    payload = [TEST_PARAMS, {**TEST_PARAMS, "distance_km": 12.5}]

    response = await client.post("/predict_batch", json=payload)

    assert response.status_code == 200
    assert len(response.json()["fares"]) == len(payload)


async def test_predict_batch_rejects_empty_payload(client):
    response = await client.post("/predict_batch", json=[])

    assert response.status_code == 422
