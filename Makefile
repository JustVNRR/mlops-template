# 1. Chargement du .env
-include .env

# 2. Export des variables pour qu'elles soient dispo dans le terminal
export

# 3. Création de l'email du Service Account dynamiquement
SA_EMAIL = $(SA_NAME)@$(GCP_PROJECT).iam.gserviceaccount.com

# 4. Import des sous-makefiles (Ordre logique MLOps)
# include make/local.mk # Étape 1 : Création de l'environnement local
# include make/gcp.mk
# include make/bigquery.mk
# include make/vm.mk
# include make/docker.mk
# include make/cloudrun.mk
# include make/pipeline.mk
# include make/github.mk
# include make/tests.mk
include make/*.mk

# --- Menu d'aide automatique ---
.DEFAULT_GOAL := help

help: ## Affiche ce menu d'aide
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<commande>\033[0m\n\nCommandes disponibles :\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ==============================================================================
# 🧹 PROJECT CLEANING & SETUP
# ==============================================================================

reinstall_package: ## Force a clean reinstall of the environment (bypasses uv cache)
	@echo "🔄 Reinstalling environment..."
	@uv sync --reinstall
	@echo "✅ Environment reinstalled successfully."

init_data_folders: ## Create the local data and model registry directories
	@echo "📁 Creating local folders..."
	@mkdir -p data/raw
	@mkdir -p data/processed
	@mkdir -p models/models
	@mkdir -p models/params
	@mkdir -p models/metrics
	@echo "✅ Folders created. Leurs contenus sont ignorés par git (data/, *.pkl, *.json)."

clean: ## Clean Python cache, build files, and hidden OS files
	@echo "🧹 Cleaning up project..."
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".ipynb_checkpoints" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name ".coverage" -delete
	@find . -type f -name "*Zone.Identifier" -delete
	@find . -type f -name ".DS_Store" -delete
	@rm -rf build/ dist/ *.egg-info/ *.dist-info/
	@rm -rf .pytest_cache/ .ruff_cache/ .mypy_cache/ .coverage
	@echo "✅ Cleaned up successfully."
