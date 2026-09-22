# ==============================================================================
# BIGQUERY COMMANDS
# ==============================================================================

bigquery_create_dataset: ## Create the BigQuery dataset
	$(call check_vars, BQ_REGION GCP_PROJECT BQ_DATASET)
	$(call confirm_action, Create the BigQuery dataset, BQ_REGION GCP_PROJECT BQ_DATASET)
	@echo "🗄️ Creating BigQuery dataset $(BQ_DATASET)..."
	bq mk \
		--location=$(BQ_REGION) \
		--project_id=$(GCP_PROJECT) \
		$(BQ_DATASET)

bigquery_create_table: ## Create a new table in the dataset (req: TABLE_NAME)
	$(call check_vars, BQ_REGION GCP_PROJECT BQ_DATASET TABLE_NAME)
	$(call confirm_action, Create a BigQuery table, BQ_REGION GCP_PROJECT BQ_DATASET TABLE_NAME)
	@echo "📊 Creating table $(TABLE_NAME) in dataset $(BQ_DATASET)..."
	bq mk \
		--location=$(BQ_REGION) \
		--project_id=$(GCP_PROJECT) \
		$(GCP_PROJECT):$(BQ_DATASET).$(TABLE_NAME)

bigquery_show: ## Show details of the project, dataset, or table (opt: TABLE_NAME)
	$(call check_vars, GCP_PROJECT)
	@if [ -n "$(BQ_DATASET)" ] && [ -n "$(TABLE_NAME)" ]; then \
		echo "📊 Showing table: $(BQ_DATASET).$(TABLE_NAME)"; \
		bq show $(GCP_PROJECT):$(BQ_DATASET).$(TABLE_NAME); \
	elif [ -n "$(BQ_DATASET)" ]; then \
		echo "📂 Showing dataset: $(BQ_DATASET)"; \
		bq show $(GCP_PROJECT):$(BQ_DATASET); \
	else \
		echo "🌍 Showing global project datasets:"; \
		bq ls --project_id=$(GCP_PROJECT); \
	fi

bigquery_delete_table: ## Delete a specific table (req: TABLE_NAME)
	$(call check_vars, GCP_PROJECT BQ_DATASET TABLE_NAME)
	$(call confirm_action, Delete the BigQuery table, GCP_PROJECT BQ_DATASET TABLE_NAME)
	@echo "🗑️ Deleting table $(BQ_DATASET).$(TABLE_NAME)..."
	bq rm -f -t $(GCP_PROJECT):$(BQ_DATASET).$(TABLE_NAME)

bigquery_delete_dataset: ## Delete the dataset and all its tables
	$(call check_vars, GCP_PROJECT BQ_DATASET)
	$(call confirm_action, Delete the dataset and everything in it, GCP_PROJECT BQ_DATASET)
	@echo "💣 Deleting dataset $(BQ_DATASET) and all its contents..."
	bq rm -r -f -d $(GCP_PROJECT):$(BQ_DATASET)
