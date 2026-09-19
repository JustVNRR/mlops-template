import os
import re
import subprocess

import pytest
from httpx import AsyncClient

# This module queries an API actually served inside a container: it requires an
# external service, so it is excluded from the default run (see the markers in
# pyproject.toml). Start it explicitly with `make test_api_docker`.
pytestmark = pytest.mark.integration

# Valid payload, matching api/schemas.TripFeatures
TEST_PARAMS = {"distance_km": 5.0, "passengers": 2, "hour": 14, "day_of_week": "monday"}

# Field returned by /predict (see api/schemas.PredictionResponse)
EXPECTED_PREDICT_KEY = "fare"

IMAGE_NAME = f"{os.environ.get('GAR_IMAGE')}:dev"


def _running_container_port() -> str | None:
    """
    Port published by the container built from the local image, or None.

    No `shell=True`: the image name comes from the environment, and
    interpolating it into a shell command would open an injection. So this
    passes an argument list, with no shell involved.
    """
    result = subprocess.run(
        ["docker", "ps", "--filter", f"ancestor={IMAGE_NAME}", "--format", "{{.Ports}}"],
        capture_output=True,
        text=True,
        check=False,
    )

    match = re.search(r":(\d{4,5})->", result.stdout)
    return match.group(1) if match else None


@pytest.fixture(scope="module")
def service_url() -> str:
    """
    URL of the running container.

    The detection lives in a fixture rather than at module level: the previous
    version ran `docker ps` AT IMPORT time, i.e. during collection, including
    for tests from another file.
    """
    port = _running_container_port()

    if not port:
        pytest.fail(
            f"❌ No running container for image '{IMAGE_NAME}'.\n"
            f"   Check that:\n"
            f"     1. your container is running (make docker_run_local)\n"
            f"     2. the image is named $GAR_IMAGE:dev"
        )

    return f"http://localhost:{port}"


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


async def test_docker_api_predict_val_is_float(service_url):
    async with AsyncClient(base_url=service_url, timeout=10.0) as client:
        response = await client.get("/predict", params=TEST_PARAMS)

    assert isinstance(response.json()[EXPECTED_PREDICT_KEY], float)
