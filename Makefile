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
# include make/tests.mk
include make/*.mk

# --- Menu d'aide automatique ---
.DEFAULT_GOAL := help

help: ## Affiche ce menu d'aide
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<commande>\033[0m\n\nCommandes disponibles :\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ==============================================================================
# 🧹 PROJECT CLEANING & SETUP
# ==============================================================================

reinstall_package: ## Force uninstall and reinstall the package with dev dependencies
	@echo "🔄 Reinstalling package..."
	@pip uninstall -y package_folder || :
	@pip install -e ".[dev]"
	@echo "✅ Package reinstalled successfully."

init_data_folders: ## Create local directories for data and model outputs
	@echo "📁 Creating local data folders..."
	@mkdir -p data/raw
	@mkdir -p data/processed
	@mkdir -p training_outputs/metrics
	@mkdir -p training_outputs/models
	@mkdir -p training_outputs/params
	@echo "✅ Folders created. (Make sure they are in your .gitignore!)"

clean: ## Clean Python cache, build files, and hidden OS files
	@echo "🧹 Cleaning up project..."
	@rm -f */version.txt
	@rm -f .coverage
	@rm -fr **/__pycache__ **/*.pyc
	@rm -fr **/build **/dist
	@rm -fr *.dist-info
	@rm -fr *.egg-info
	@rm -f **/.DS_Store
	@rm -f **/*Zone.Identifier
	@rm -f **/.ipynb_checkpoints
	@echo "✅ Cleaned up successfully."
