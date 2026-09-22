# ==============================================================================
# GCP INFRASTRUCTURE & IAM COMMANDS
# ==============================================================================

gcp_project_list: ## List all GCP projects available to your account
	@echo "📋 Listing GCP projects..."
	gcloud projects list
	# Useful alternatives:
	# gcloud projects list --format="value(projectId)" # lists only IDs
	# gcloud config get-value project # shows only the active project ID

gcp_enable_compute: ## Enable the Compute Engine API for the project
	@echo "⚙️ Enabling Compute Engine API..."
	gcloud services enable compute.googleapis.com --project=$(GCP_PROJECT)

gcs_list_buckets: ## List all Cloud Storage buckets in the project
	@echo "🪣 Listing Cloud Storage buckets..."
	gcloud storage ls --project=$(GCP_PROJECT)

gcs_create_bucket: ## Create a new Cloud Storage bucket
	@echo "🪣 Creating bucket gs://$(BUCKET_NAME)..."
	gcloud storage buckets create gs://$(BUCKET_NAME) \
		--location=$(GCP_REGION) \
		--project=$(GCP_PROJECT)

gcs_delete_bucket: ## Delete the Cloud Storage bucket and all its contents
	@echo "💣 Deleting bucket gs://$(BUCKET_NAME)..."
	gcloud storage rm --recursive gs://$(BUCKET_NAME)

iam_setup_service_account: ## Create the Service Account and assign IAM roles
	@# Describe first, create only when absent - same shape as
	@# artifact_registry_create, for the same reason: `|| true` reported every
	@# failure (permission denied, API not enabled, name already taken) as a
	@# success, and the two bindings below then failed on an account that was
	@# never created. `vm_create` depends on this target, so the VM was built
	@# anyway, with a service account that did not exist.
	@if gcloud iam service-accounts describe "$(SA_EMAIL)" --project="$(GCP_PROJECT)" >/dev/null 2>&1; then \
		echo "ℹ️  Service account $(SA_EMAIL) already exists."; \
	else \
		echo "🤖 Creating Service Account $(SA_NAME)..."; \
		gcloud iam service-accounts create $(SA_NAME) \
			--display-name="Service Account for $(INSTANCE) VM" \
			--project=$(GCP_PROJECT); \
	fi
	@echo "🔐 Adding BigQuery Data Editor role..."
	gcloud projects add-iam-policy-binding $(GCP_PROJECT) \
		--member="serviceAccount:$(SA_EMAIL)" \
		--role="roles/bigquery.dataEditor" \
		--quiet
	@echo "🔐 Adding Cloud Storage Object Admin role..."
	gcloud projects add-iam-policy-binding $(GCP_PROJECT) \
		--member="serviceAccount:$(SA_EMAIL)" \
		--role="roles/storage.objectAdmin" \
		--quiet
