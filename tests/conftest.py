"""Shared answers and the generation fixture.

The answers every test starts from are deliberately ordinary. What happens when
they are not is the subject of test_values.py.
"""

import pytest

BASE_ANSWERS = {
    "project_name": "Churn Prediction",
    "package_name": "churn_prediction",
    "author_name": "Jane Doe",
    "author_email": "jane@example.com",
    "license": "MIT",
}

PACKAGE = BASE_ANSWERS["package_name"]

MODULES = ["gcp", "mlflow", "prefect", "docker"]


@pytest.fixture
def generate(copie):
    """Generate a project and return its directory, failing loudly otherwise."""

    def _generate(**overrides):
        result = copie.copy(extra_answers={**BASE_ANSWERS, **overrides})
        assert result.exit_code == 0, f"generation failed: {result.exception!r}"
        assert result.project_dir is not None
        return result.project_dir

    return _generate
