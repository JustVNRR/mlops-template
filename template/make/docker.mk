# ==============================================================================
# CONTAINER COMMANDS — ON YOUR MACHINE
# ==============================================================================
# The container is not an optional building block: this file ships to every
# project. Publishing the image to GCP is a cloud concern, and lives in
# `artifact_registry.mk`, which only a project built with `gcp` receives.

docker_build_local: ## Build the Docker image locally for testing
	$(call check_vars, DOCKER_BASE_IMAGE GAR_IMAGE)
	@echo "🐳 Building local Docker image $(GAR_IMAGE):dev..."
	docker build \
		--build-arg DOCKER_BASE_IMAGE=$(DOCKER_BASE_IMAGE) \
		--tag=$(GAR_IMAGE):dev .

docker_run_local: ## Run the local Docker container on port 8000
	$(call check_vars, GAR_IMAGE)
	@echo "🏃‍♂️ Running container $(GAR_IMAGE):dev..."
	@echo "👉 Go to http://localhost:8000"
	docker run -it -e PORT=8000 -p 8000:8000 $(GAR_IMAGE):dev
