# ==============================================================================
# LOCAL ENVIRONMENT SETUP
# ==============================================================================

local_setup: ## Create the local environment with uv (Python + dependencies)
	@if [ ! -f pyproject.toml ]; then \
		echo "❌ CRITICAL ERROR: pyproject.toml not found! Cannot install the package."; \
		exit 1; \
	fi
	@echo "📦 Syncing the environment with uv (installs the pinned Python if needed)..."
	uv sync
	@echo "✅ Local setup complete!"
	@echo "👉 Prefix your commands with 'uv run' (e.g. 'uv run pytest'), or activate the venv:"
	@echo "   source .venv/bin/activate"
