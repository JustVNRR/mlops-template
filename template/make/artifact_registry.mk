# ==============================================================================
# ARTIFACT REGISTRY — THE PRODUCTION IMAGE
# ==============================================================================
# Everything here needs a GCP project, so this file is only shipped to a
# project built with `gcp`. The container itself is not a building block:
# building it and running it on your machine lives in `docker.mk`, which every
# project receives.

artifact_registry_create: ## Create the Docker repository in Artifact Registry
	$(call check_vars, ARTIFACTSREPO GCP_REGION GCP_PROJECT)
	$(call confirm_action, Create the Artifact Registry repository, ARTIFACTSREPO GCP_REGION GCP_PROJECT)
	@# Describe first and create only when it is absent: the target stays
	@# re-runnable, and a creation that really fails now fails the run - the
	@# `|| true` it replaces reported every failure (API disabled, permission
	@# denied, bad location) as a success, and the push found out much later.
	@if gcloud artifacts repositories describe $(ARTIFACTSREPO) \
		--location=$(GCP_REGION) \
		--project=$(GCP_PROJECT) >/dev/null 2>&1; then \
		echo "ℹ️  Repository $(ARTIFACTSREPO) already exists."; \
	else \
		echo "📦 Creating Artifact Registry repository $(ARTIFACTSREPO)..."; \
		gcloud artifacts repositories create $(ARTIFACTSREPO) \
			--repository-format=docker \
			--location=$(GCP_REGION) \
			--description="Docker repository $(ARTIFACTSREPO) for project $(GCP_PROJECT)" \
			--project=$(GCP_PROJECT); \
	fi

artifact_registry_role: ## Grant yourself permission to push to Artifact Registry
	$(call check_vars, GCP_PROJECT)
	$(call confirm_action, Grant the Artifact Registry Writer role, GCP_PROJECT)
	@echo "🔐 Adding Artifact Registry Writer role to your account..."
	gcloud projects add-iam-policy-binding $(GCP_PROJECT) \
		--member="user:$$(gcloud config get-value account)" \
		--role="roles/artifactregistry.writer"

artifact_registry_auth: ## Let your Docker push to Artifact Registry
	$(call check_vars, GCP_REGION)
	@echo "🔑 Configuring Docker authentication for GCP..."
	gcloud auth configure-docker $(GCP_REGION)-docker.pkg.dev --quiet

artifact_registry_build: ## Build the production image (linux/amd64)
	$(call check_vars, DOCKER_BASE_IMAGE GCP_REGION GCP_PROJECT ARTIFACTSREPO GAR_IMAGE)
	@echo "🏗️ Building production image..."
	docker build \
		--platform linux/amd64 \
		--build-arg DOCKER_BASE_IMAGE=$(DOCKER_BASE_IMAGE) \
		-t $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/$(ARTIFACTSREPO)/$(GAR_IMAGE):prod \
		.

artifact_registry_push: ## Push the production image to Artifact Registry
	$(call check_vars, GCP_REGION GCP_PROJECT ARTIFACTSREPO GAR_IMAGE)
	$(call confirm_action, Push the production image to Artifact Registry, GCP_REGION GCP_PROJECT ARTIFACTSREPO GAR_IMAGE)
	@echo "🚀 Pushing image to Artifact Registry..."
	docker push $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/$(ARTIFACTSREPO)/$(GAR_IMAGE):prod
