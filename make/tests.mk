# ==============================================================================
# TESTING COMMANDS
# ==============================================================================

lint: ## Check code style and quality with ruff
	uv run ruff check .

lint_fix: ## Auto-fix what ruff can fix
	uv run ruff check --fix .

format: ## Format the code with ruff
	uv run ruff format .

test_all: ## Run all tests in the project
	uv run pytest

test_infrastructure: ## Run sanity checks for GCP setup and credentials
	uv run pytest tests/infrastructure/

test_api_local: ## Run API tests locally (FastAPI in memory)
	uv run pytest tests/api/test_endpoints.py

test_api_docker: ## Run API tests on the local Docker container
	uv run pytest tests/api/test_docker_endpoints.py

test_api_cloud: ## Run API tests on the deployed Cloud Run endpoint
	uv run pytest tests/api/test_cloud_endpoints.py

test_integration: ## Run the tests that need real GCP credentials (excluded by default)
	uv run pytest -m integration
