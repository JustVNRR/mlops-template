# ==============================================================================
# CLOUD RUN COMMANDS
# ==============================================================================

cloudrun_deploy: ## Deploy the container to Google Cloud Run
	$(call check_vars, GAR_IMAGE GCP_REGION GCP_PROJECT ARTIFACTSREPO CLOUDRUN_MEMORY)
	$(call confirm_action, Deploy to Cloud Run, GAR_IMAGE GCP_REGION GCP_PROJECT ARTIFACTSREPO CLOUDRUN_MEMORY)
	@echo "🚀 Deploying $(GAR_IMAGE) to Cloud Run..."
	gcloud run deploy $(GAR_IMAGE) \
		--image $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/$(ARTIFACTSREPO)/$(GAR_IMAGE):prod \
		--memory $(CLOUDRUN_MEMORY) \
		--region $(GCP_REGION) \
		--project $(GCP_PROJECT) \
		--allow-unauthenticated

cloudrun_list: ## List all active Cloud Run services in the project
	$(call check_vars, GCP_PROJECT)
	@echo "📋 Listing Cloud Run services..."
	gcloud run services list --project $(GCP_PROJECT)

cloudrun_url: ## Retrieve the live URL of the deployed API
	$(call check_vars, GAR_IMAGE GCP_REGION GCP_PROJECT)
	@echo "🌍 Your API is live at:"
	@gcloud run services describe $(GAR_IMAGE) \
		--region $(GCP_REGION) \
		--project $(GCP_PROJECT) \
		--format "value(status.url)"

cloudrun_logs: ## Tail the real-time logs of the Cloud Run service
	$(call check_vars, GAR_IMAGE GCP_REGION GCP_PROJECT)
	@echo "📜 Tailing logs for $(GAR_IMAGE)... (Press Ctrl+C to stop)"
	gcloud run services logs read $(GAR_IMAGE) \
		--region $(GCP_REGION) \
		--project $(GCP_PROJECT) \
		--limit 50

cloudrun_delete: ## Delete the Cloud Run service and take the API offline
	$(call check_vars, GAR_IMAGE GCP_REGION GCP_PROJECT)
	$(call confirm_action, Delete the Cloud Run service, GAR_IMAGE GCP_REGION GCP_PROJECT)
	@echo "🗑️ Deleting Cloud Run service $(GAR_IMAGE)..."
	gcloud run services delete $(GAR_IMAGE) \
		--region $(GCP_REGION) \
		--project $(GCP_PROJECT) \
		--quiet
