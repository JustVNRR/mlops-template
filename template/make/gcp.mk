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
	$(call check_vars, GCP_PROJECT)
	$(call confirm_action, Enable the Compute Engine API, GCP_PROJECT)
	@echo "⚙️ Enabling Compute Engine API..."
	gcloud services enable compute.googleapis.com --project=$(GCP_PROJECT)

gcs_list_buckets: ## List all Cloud Storage buckets in the project
	$(call check_vars, GCP_PROJECT)
	@echo "🪣 Listing Cloud Storage buckets..."
	gcloud storage ls --project=$(GCP_PROJECT)

gcs_create_bucket: ## Create a new Cloud Storage bucket
	$(call check_vars, BUCKET_NAME GCP_REGION GCP_PROJECT)
	$(call confirm_action, Create the Cloud Storage bucket, BUCKET_NAME GCP_REGION GCP_PROJECT)
	@echo "🪣 Creating bucket gs://$(BUCKET_NAME)..."
	gcloud storage buckets create gs://$(BUCKET_NAME) \
		--location=$(GCP_REGION) \
		--project=$(GCP_PROJECT)

gcs_delete_bucket: ## Delete the Cloud Storage bucket and all its contents
	$(call check_vars, BUCKET_NAME GCP_PROJECT)
	$(call confirm_action, Delete the bucket and everything in it, BUCKET_NAME GCP_PROJECT)
	@echo "💣 Deleting bucket gs://$(BUCKET_NAME)..."
	gcloud storage rm --recursive gs://$(BUCKET_NAME) --project=$(GCP_PROJECT)

iam_setup_service_account: ## Create the Service Account and assign IAM roles
	$(call check_vars, SA_NAME GCP_PROJECT)
	$(call confirm_action, Create the service account and its IAM roles, SA_NAME SA_EMAIL GCP_PROJECT)
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
