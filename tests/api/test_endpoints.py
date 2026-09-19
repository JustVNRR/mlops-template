import pytest
from httpx import ASGITransport, AsyncClient

from package_folder.api.fast import app
from package_folder.ml_logic import registry
from package_folder.ml_logic.data import clean_data, generate_toy_data
from package_folder.ml_logic.model import build_model
from package_folder.params import ALL_FEATURES, TARGET_COLUMN

# Charge utile valide, conforme à api/schemas.TripFeatures
TEST_PARAMS = {"distance_km": 5.0, "passengers": 2, "hour": 14, "day_of_week": "monday"}

# Champ renvoyé par /predict (voir api/schemas.PredictionResponse)
EXPECTED_PREDICT_KEY = "fare"


@pytest.fixture
async def client(tmp_path, monkeypatch):
    """
    Client HTTP branché sur l'app ASGI, avec un modèle entraîné à la volée.

    Trois précautions, chacune corrigeant un piège réel :

    1. Le registre est redirigé vers un dossier temporaire : le test ne dépend
       pas d'un `make run_train` préalable et ne pollue pas le registre réel.
    2. Le modèle est entraîné ici même (quelques centaines de lignes, quelques
       millisecondes) : la suite est autoportante, donc exécutable en CI.
    3. Le `lifespan` est exécuté EXPLICITEMENT. `ASGITransport` ne déclenche
       pas les événements de démarrage : sans ce `async with`, `app.state.model`
       resterait vide et toutes les prédictions répondraient 503.
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
# SANTÉ
# ==============================================================================

async def test_root_is_up(client):
    response = await client.get("/")

    assert response.status_code == 200


async def test_root_returns_greeting(client):
    response = await client.get("/")

    assert response.json() == {"greeting": "Hello"}


async def test_model_reports_being_loaded(client):
    """
    /model doit exposer l'état réel du modèle servi : c'est ce qui permet de
    vérifier un déploiement sans provoquer de prédiction.
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

    assert EXPECTED_PREDICT_KEY in response.json(), f"Clé '{EXPECTED_PREDICT_KEY}' absente de la réponse"


async def test_predict_val_is_float(client):
    response = await client.get("/predict", params=TEST_PARAMS)

    assert isinstance(response.json()[EXPECTED_PREDICT_KEY], float)


async def test_predict_rejects_invalid_input(client):
    """
    La validation Pydantic doit rejeter une entrée aberrante AVANT le modèle.
    Sans elle, une distance négative produirait une prédiction silencieusement
    fausse au lieu d'une erreur.
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
