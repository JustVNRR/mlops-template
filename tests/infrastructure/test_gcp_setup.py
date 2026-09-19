import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from google.cloud import storage

# These tests make REAL calls to Google Cloud: they require an account, a
# service account and an existing bucket. They are therefore excluded from the
# default run (see the markers in pyproject.toml) and are started with
# `make test_integration`.
pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Loaded here so the variables are available without depending on `make` or
# direnv — a `pytest` launched by hand must work.
load_dotenv(PROJECT_ROOT / ".env")


def test_setup_key_env():
    """Verify that $GOOGLE_APPLICATION_CREDENTIALS is defined."""
    assert os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), (
        "❌ GOOGLE_APPLICATION_CREDENTIALS is not defined.\n"
        "   → Set the path to your service account key in your .env file."
    )


def test_setup_key_path():
    """Verify that $GOOGLE_APPLICATION_CREDENTIALS points to an existing file."""
    service_account_key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    assert service_account_key_path, "❌ GOOGLE_APPLICATION_CREDENTIALS is not defined."
    assert os.path.exists(service_account_key_path), (
        f"❌ GCP key not found at the given path: {service_account_key_path}"
    )


def test_code_get_project():
    """Verify we can authenticate and retrieve the default GCP project id."""
    try:
        client = storage.Client()
        assert client.project is not None, "❌ GCP authentication failed: check your service account."
    except Exception as error:
        pytest.fail(f"❌ Could not connect to Google Cloud: {error}")


def test_setup_project_id():
    """Verify that the provided project id matches the authenticated one."""
    gcp_project = os.getenv("GCP_PROJECT")
    assert gcp_project, "❌ GCP_PROJECT is not defined in your environment."

    client = storage.Client()
    assert client.project == gcp_project, (
        f"❌ Authenticated project '{client.project}' differs from GCP_PROJECT '{gcp_project}'"
    )


def test_setup_bucket_name():
    """Verify that the provided bucket exists and is accessible."""
    bucket_name = os.getenv("BUCKET_NAME")
    assert bucket_name, "❌ BUCKET_NAME is not defined in your environment."

    client = storage.Client()
    try:
        client.get_bucket(bucket_name, timeout=10.0)
    except Exception as error:
        pytest.fail(f"❌ Bucket '{bucket_name}' not found or not accessible: {error}")
