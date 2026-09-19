import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from google.cloud import storage

# Ces tests exécutent de VRAIS appels à Google Cloud : ils exigent un compte,
# un service account et un bucket existant. Ils sont donc exclus de
# l'exécution par défaut (voir les markers dans pyproject.toml) et se lancent
# avec `make test_integration`.
pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Chargé ici pour que les variables soient disponibles sans dépendre de
# `make` ou direnv — un `pytest` lancé à la main doit fonctionner.
load_dotenv(PROJECT_ROOT / ".env")


def test_setup_key_env():
    """Verify that $GOOGLE_APPLICATION_CREDENTIALS is defined."""
    assert os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), (
        "❌ GOOGLE_APPLICATION_CREDENTIALS n'est pas définie.\n"
        "   → Renseigne le chemin de ta clé de service account dans ton .env."
    )


def test_setup_key_path():
    """Verify that $GOOGLE_APPLICATION_CREDENTIALS points to an existing file."""
    service_account_key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    assert service_account_key_path, "❌ GOOGLE_APPLICATION_CREDENTIALS n'est pas définie."
    assert os.path.exists(service_account_key_path), (
        f"❌ Clé GCP introuvable à l'emplacement indiqué : {service_account_key_path}"
    )


def test_code_get_project():
    """Verify we can authenticate and retrieve the default GCP project id."""
    try:
        client = storage.Client()
        assert client.project is not None, "❌ Authentification GCP impossible : vérifie ton service account."
    except Exception as error:
        pytest.fail(f"❌ Connexion à Google Cloud impossible : {error}")


def test_setup_project_id():
    """Verify that the provided project id matches the authenticated one."""
    gcp_project = os.getenv("GCP_PROJECT")
    assert gcp_project, "❌ GCP_PROJECT n'est pas définie dans ton environnement."

    client = storage.Client()
    assert client.project == gcp_project, (
        f"❌ Le projet authentifié '{client.project}' diffère de GCP_PROJECT '{gcp_project}'"
    )


def test_setup_bucket_name():
    """Verify that the provided bucket exists and is accessible."""
    bucket_name = os.getenv("BUCKET_NAME")
    assert bucket_name, "❌ BUCKET_NAME n'est pas définie dans ton environnement."

    client = storage.Client()
    try:
        client.get_bucket(bucket_name, timeout=10.0)
    except Exception as error:
        pytest.fail(f"❌ Bucket '{bucket_name}' introuvable ou inaccessible : {error}")
