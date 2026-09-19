import os

import pytest
from httpx import AsyncClient

# Ce module interroge l'API DÉPLOYÉE : il exige un service externe, donc exclu
# de l'exécution par défaut (voir les markers dans pyproject.toml).
# Lance-le explicitement avec `make test_api_cloud`.
pytestmark = pytest.mark.integration

# Charge utile valide, conforme à api/schemas.TripFeatures
TEST_PARAMS = {"distance_km": 5.0, "passengers": 2, "hour": 14, "day_of_week": "monday"}

# Champ renvoyé par /predict (voir api/schemas.PredictionResponse)
EXPECTED_PREDICT_KEY = "fare"

SERVICE_URL = os.environ.get("SERVICE_URL")


@pytest.fixture
def service_url() -> str:
    if not SERVICE_URL:
        pytest.fail(
            "❌ SERVICE_URL est vide : impossible de joindre l'API déployée.\n"
            "   → Récupère l'URL avec `make cloudrun_url`, puis renseigne SERVICE_URL dans ton .env."
        )

    return SERVICE_URL


# ==============================================================================
# SANTÉ
# ==============================================================================


async def test_root_is_up(service_url):
    async with AsyncClient(base_url=service_url, timeout=10.0) as client:
        response = await client.get("/")

    assert response.status_code == 200


async def test_root_returns_greeting(service_url):
    async with AsyncClient(base_url=service_url, timeout=10.0) as client:
        response = await client.get("/")

    assert response.json() == {"greeting": "Hello"}


# ==============================================================================
# PRÉDICTION
# ==============================================================================


async def test_predict_is_up(service_url):
    async with AsyncClient(base_url=service_url, timeout=10.0) as client:
        response = await client.get("/predict", params=TEST_PARAMS)

    assert response.status_code == 200


async def test_predict_is_dict(service_url):
    async with AsyncClient(base_url=service_url, timeout=10.0) as client:
        response = await client.get("/predict", params=TEST_PARAMS)

    assert isinstance(response.json(), dict)


async def test_predict_has_key(service_url):
    async with AsyncClient(base_url=service_url, timeout=10.0) as client:
        response = await client.get("/predict", params=TEST_PARAMS)

    assert EXPECTED_PREDICT_KEY in response.json(), f"Clé '{EXPECTED_PREDICT_KEY}' absente de la réponse"


async def test_cloud_api_predict_val_is_float(service_url):
    async with AsyncClient(base_url=service_url, timeout=10.0) as client:
        response = await client.get("/predict", params=TEST_PARAMS)

    assert isinstance(response.json()[EXPECTED_PREDICT_KEY], float)
