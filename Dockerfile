# 1. Retrieve the base image dynamically (passed by the Makefile / .env)
ARG DOCKER_BASE_IMAGE
FROM ${DOCKER_BASE_IMAGE}

# 2. Bring in uv (official static binary). No pip, no requirements.txt:
#    uv.lock is the single source of truth for versions.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /api

# Deterministic, container-friendly uv behaviour:
#   UV_COMPILE_BYTECODE : pre-compile .pyc for faster cold starts
#   UV_LINK_MODE=copy   : cache and target live on different layers, hardlinks
#                         are not possible there
#   PYTHONUNBUFFERED    : logs reach Cloud Run immediately, not on container exit
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/api/.venv \
    PATH="/api/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# 3. Install DEPENDENCIES FIRST, alone. This layer stays cached as long as
#    pyproject.toml / uv.lock do not change: editing code does not reinstall
#    the dependency tree.
#    README.md is required here because the project metadata references it.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# 4. Copy the source code, then install the project itself
#    (--no-dev: production image, no pytest/ruff/ipykernel)
COPY package_folder package_folder
RUN uv sync --frozen --no-dev

# 5. Run as a NON-ROOT user.
#    If the application — or one of its dependencies — is compromised, the
#    attacker does not gain root inside the container. The venv and the code
#    remain readable by this user.
RUN useradd --create-home --uid 1001 appuser
USER appuser

# Optional: Uncomment if you have models to ship inside the image.
# ⚠️ By default the image contains NO model: /predict answers 503 until one is
#    loaded (through PUT /model, or by implementing MLflow/GCS loading in
#    ml_logic/registry.py). That is deliberate: a model quickly weighs hundreds
#    of megabytes, and freezing it into the image forces a rebuild and a redeploy
#    on every retraining.
# COPY models models

# 6. Start the API (using exec to handle signals properly like CTRL+C)
CMD ["sh", "-c", "exec uvicorn package_folder.api.fast:app --host 0.0.0.0 --port $PORT"]
