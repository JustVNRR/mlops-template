import os

import pytest
from httpx import AsyncClient

# This module queries the DEPLOYED API: it requires an external service, so it
# is excluded from the default run (see the markers in pyproject.toml).
# Start it explicitly with `make test_api_cloud`.
pytestmark = pytest.mark.integration

# Valid payload, matching api/schemas.TripFeatures
TEST_PARAMS = {"distance_km": 5.0, "passengers": 2, "hour": 14, "day_of_week": "monday"}

# Field returned by /predict (see api/schemas.PredictionResponse)
EXPECTED_PREDICT_KEY = "fare"

SERVICE_URL = os.environ.get("SERVICE_URL")


@pytest.fixture
def service_url() -> str:
    if not SERVICE_URL:
        pytest.fail(
            "❌ SERVICE_URL is empty: cannot reach the deployed API.\n"
            "   → Get the URL with `make cloudrun_url`, then set SERVICE_URL in your .env."
        )

    return SERVICE_URL


# ==============================================================================
# HEALTH
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
# PREDICTION
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

    assert EXPECTED_PREDICT_KEY in response.json(), f"Key '{EXPECTED_PREDICT_KEY}' missing from the response"


async def test_cloud_api_predict_val_is_float(service_url):
    async with AsyncClient(base_url=service_url, timeout=10.0) as client:
        response = await client.get("/predict", params=TEST_PARAMS)

    assert isinstance(response.json()[EXPECTED_PREDICT_KEY], float)
