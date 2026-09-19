import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Le .env vit à la RACINE du projet, pas dans le dossier courant : un test
# lancé depuis un sous-dossier doit le trouver malgré tout.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"


def test_env_file_exists():
    """Verify that the .env file exists at the root of the project."""
    assert ENV_PATH.is_file(), f"❌ {ENV_PATH} est absent ! Lance d'abord : cp .env.sample .env"


@pytest.mark.integration
def test_critical_env_variables_are_set():
    """
    Verify that critical variables are filled and not left empty.

    Marqué `integration` : ce test exige un projet ENTIÈREMENT configuré, GCP
    compris. Sur une machine de développement sans compte cloud, il échouerait
    pour une raison parfaitement légitime. Il ne doit donc ni bloquer
    l'exécution par défaut, ni faire échouer la CI.

    → À lancer avec `make test_integration` une fois GCP configuré.
    """
    load_dotenv(ENV_PATH)

    # Ajoute ici toute variable absolument nécessaire à ton projet.
    critical_vars = [
        "PACKAGE_NAME",
        "GCP_PROJECT",
        "GCP_REGION",
        "BUCKET_NAME",
    ]

    for var in critical_vars:
        value = os.getenv(var)
        assert value, f"❌ '{var}' est vide dans ton fichier .env : renseigne-la."
