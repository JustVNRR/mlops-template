# ==============================================================================
# ARTIFACT REGISTRY — THE PRODUCTION IMAGE
# ==============================================================================
# Everything here needs a GCP project, so this file is only shipped to a
# project built with `gcp`. The container itself is not a building block:
# building it and running it on your machine lives in `docker.mk`, which every
# project receives.

artifact_registry_create: ## Create the Docker repository in Artifact Registry
	@echo "📦 Creating Artifact Registry repository $(ARTIFACTSREPO)..."
	gcloud artifacts repositories create $(ARTIFACTSREPO) \
		--repository-format=docker \
		--location=$(GCP_REGION) \
		--description="Docker repository $(ARTIFACTSREPO) for project $(GCP_PROJECT)" \
		--project=$(GCP_PROJECT) || true

artifact_registry_role: ## Grant yourself permission to push to Artifact Registry
	@echo "🔐 Adding Artifact Registry Writer role to your account..."
	gcloud projects add-iam-policy-binding $(GCP_PROJECT) \
		--member="user:$$(gcloud config get-value account)" \
		--role="roles/artifactregistry.writer"

artifact_registry_auth: ## Let your Docker push to Artifact Registry
	@echo "🔑 Configuring Docker authentication for GCP..."
	gcloud auth configure-docker $(GCP_REGION)-docker.pkg.dev --quiet

docker_build_prod: ## Build the Docker image for production (linux/amd64)
	@echo "🏗️ Building production image..."
	docker build \
		--platform linux/amd64 \
		--build-arg DOCKER_BASE_IMAGE=$(DOCKER_BASE_IMAGE) \
		-t $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/$(ARTIFACTSREPO)/$(GAR_IMAGE):prod \
		.

docker_push_prod: ## Push the production image to Artifact Registry
	@echo "🚀 Pushing image to Artifact Registry..."
	docker push $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/$(ARTIFACTSREPO)/$(GAR_IMAGE):prod
