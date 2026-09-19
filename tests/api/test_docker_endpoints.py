import os
import re
import subprocess

import pytest
from httpx import AsyncClient

# Ce module interroge une API réellement servie dans un conteneur : il exige un
# service externe, donc exclu de l'exécution par défaut (voir les markers dans
# pyproject.toml). Lance-le explicitement avec `make test_api_docker`.
pytestmark = pytest.mark.integration

# Charge utile valide, conforme à api/schemas.TripFeatures
TEST_PARAMS = {"distance_km": 5.0, "passengers": 2, "hour": 14, "day_of_week": "monday"}

# Champ renvoyé par /predict (voir api/schemas.PredictionResponse)
EXPECTED_PREDICT_KEY = "fare"

IMAGE_NAME = f"{os.environ.get('GAR_IMAGE')}:dev"


def _running_container_port() -> str | None:
    """
    Port publié par le conteneur issu de l'image locale, ou None.

    Pas de `shell=True` : le nom de l'image vient de l'environnement, et
    l'interpoler dans une commande shell ouvrirait une injection. On passe
    donc une liste d'arguments, sans passer par un shell.
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
    URL du conteneur en cours d'exécution.

    La détection vit dans une fixture et non au niveau du module : l'ancienne
    version lançait `docker ps` à l'IMPORT, donc dès la collecte, y compris
    pour les tests d'un autre fichier.
    """
    port = _running_container_port()

    if not port:
        pytest.fail(
            f"❌ Aucun conteneur en cours d'exécution pour l'image '{IMAGE_NAME}'.\n"
            f"   Vérifie que :\n"
            f"     1. ton conteneur tourne (make docker_run_local)\n"
            f"     2. l'image porte bien le nom $GAR_IMAGE:dev"
        )

    return f"http://localhost:{port}"


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


async def test_docker_api_predict_val_is_float(service_url):
    async with AsyncClient(base_url=service_url, timeout=10.0) as client:
        response = await client.get("/predict", params=TEST_PARAMS)

    assert isinstance(response.json()[EXPECTED_PREDICT_KEY], float)
