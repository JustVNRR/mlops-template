# 🚀 MLOps Template

A starter template for a Machine Learning project: training, experiment
tracking, a serving API and GCP deployment — driven by a Makefile, checked by a
CI, and **runnable straight away, with no cloud account**.

---

## 📋 Prerequisites

| Tool | Why | Install |
|---|---|---|
| **GNU make** | Every project command goes through it | `sudo apt install make` (preinstalled on macOS) |
| **uv** | Python environments and dependencies | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Docker** | Step 2 of the API tests, and the image build | [Docker Desktop](https://www.docker.com/products/docker-desktop/) |
| **git** | Obviously | — |
| **gcloud CLI** | *Optional* — only for GCP | [Install](https://cloud.google.com/sdk/docs/install) |

> **On Windows: use WSL2.** This project is *nix-first (make, bash, sed, Docker,
> Ubuntu CI). In a native Git Bash terminal, `make` and `uv` are not installed by
> default and the initialisation scripts do not work. Run `wsl --install`, then
> work from `/mnt/c/...` or — better — clone into the Linux filesystem.

Python itself is **not** to be installed by hand: `uv` reads `.python-version`
and downloads the required interpreter.

---

## 🚀 Quick start

```bash
git clone https://github.com/JustVNRR/mlops-template.git my-project
cd my-project

cp .env.sample .env            # then fill in PACKAGE_NAME
make init_project              # renames package_folder -> your package name

make local_setup               # uv sync: installs Python + the dependencies
make run_all                   # preprocess -> train -> evaluate -> predict
make run_api                   # the API starts on http://127.0.0.1:8000
```

`make run_all` works with **no cloud account at all**: the template generates a
synthetic dataset, trains a reference scikit-learn model and produces
predictions. Replace the pieces one at a time with your own afterwards (see
[Adapting this template](#-adapting-this-template)).

`make init_project` is a one-shot script: it renames the package everywhere,
then **deletes itself** along with its Makefile target.

---

## 🗂️ Project structure

```
.
├── src/                       # src layout: only importable code lives here
│   └── package_folder/        #   the Python package (renamed by init_project)
│       ├── params.py          #     configuration: schema, thresholds, env vars
│       ├── api/
│       │   ├── fast.py        #     FastAPI application (lifespan, routes)
│       │   └── schemas.py     #     Pydantic input/output contract
│       ├── interface/
│       │   ├── main.py        #     pipeline: preprocess / train / evaluate / pred
│       │   └── workflow.py    #     Prefect orchestration
│       └── ml_logic/
│           ├── data.py        #     loading, cleaning, persistence
│           ├── preprocessor.py#    scikit-learn transformations
│           ├── model.py       #     build / train / evaluate
│           ├── registry.py    #     model lifecycle (local, MLflow)
│           └── encoders.py    #     a place for your custom encoders
├── make/                      # Makefile targets, grouped by domain
├── tests/
│   ├── api/                   #   the 3 tiers (local, docker, cloud)
│   ├── ml_logic/              #   unit tests of the pipeline
│   └── infrastructure/        #   GCP setup checks
├── notebooks/                 # exploration + API usage
├── models/                    # local registry (git-ignored)
├── scripts/                   # init_project, VM provisioning
├── .github/workflows/ci.yml   # CI: lint, tests, Docker build
├── pyproject.toml             # dependencies, ruff, pytest
└── uv.lock                    # locked versions (committed)
```

`make help` lists the **56 available targets**.

---

## ⚙️ Configuration

Everything goes through `.env` (git-ignored — see `.env.sample` for the full,
commented contract). The variables that matter at startup:

| Variable | Default | Purpose |
|---|---|---|
| `PACKAGE_NAME` | — | Package name, used once by `make init_project` |
| `MODEL_TARGET` | `local` | Where models are stored: `local`, `gcs` or `mlflow` |
| `DATA_SOURCE` | `toy` | Data source: `toy` (synthetic) or `bigquery` |
| `DATA_SIZE` | `2000` | Size of the synthetic dataset (`1k`, `200k`, `all`…) |
| `MAE_THRESHOLD` | `3.0` | Quality bar below which a model gets promoted |
| `MLFLOW_*`, `GCP_*`, `BUCKET_NAME` | — | Only needed for the cloud |

**The defaults are enough to run everything locally.** No variable is mandatory
as long as you stay on `MODEL_TARGET=local` and `DATA_SOURCE=toy`.

---

## 🧪 The pipeline

Four steps, runnable independently — each one persists its result, so
`make run_train` works even if `make run_preprocess` ran in another terminal:

```bash
make run_preprocess    # load, clean and save -> data/processed/
make run_train         # fit, save the model and its metrics
make run_evaluate      # evaluate the latest model
make run_pred          # predict on a sample

make run_all           # all four in a row
```

Models and metrics land in `models/` (JSON for metrics, pickle for models). The
**most recent model** is always the one being served, chosen by modification
time.

### Orchestration (Prefect)

`make run_workflow` runs the full cycle: data preparation, evaluation of the
model in production, retraining, promotion if the new model does better, and a
notification. Set `EVALUATION_START_DATE` in `.env` to define the evaluation
period.

---

## 🌐 The API

```bash
make run_api
```

| Route | Description |
|---|---|
| `GET /` | Service health |
| `GET /model` | State of the loaded model, and the cause of failure if any |
| `PUT /model` | Hot-swaps the model, with no service restart |
| `GET /predict` | Prediction for one trip (query parameters) |
| `POST /predict_batch` | Prediction for a list of trips |

Interactive documentation: <http://127.0.0.1:8000/docs>.

**The API starts even with no model**: `/predict` then answers `503` with the
exact cause, instead of failing the container at startup. That is what makes it
deployable and testable independently of training.

### The 3 validation tiers

Each tier catches what the previous one cannot see:

```bash
# 1. In memory: logic and API contract
make test_api_local

# 2. Inside the container: missing dependencies, broken image
make docker_build_local
make docker_run_local
make test_api_docker

# 3. In production: the actually deployed URL
make test_api_cloud
```

### Tests

```bash
make test_all            # default run: 46 tests, no service required
make test_integration    # the 18 tests needing GCP / Docker / a deployed API
make lint                # ruff check
make format              # ruff format
```

Tests requiring an external service carry the `integration` marker and are
**excluded by default**: that is what lets the CI run with no secrets at all.

---

## ☁️ GCP deployment

### Training VM

```bash
make vm_create      # creates the VM and its service account
make vm_setup       # provisions the VM (uv, zsh, direnv)
make vm_connect     # SSH
```

> ⚠️ **Cost management**: run `make vm_stop` as soon as you stop working (the CPU
> is no longer billed, files are kept), `make vm_start` to resume, and
> `make vm_delete` at the end of the project.

### Data and artefacts

```bash
make bigquery_create_dataset
make gcs_create_bucket
make iam_setup_service_account
```

### API in production

```bash
make docker_build_prod      # linux/amd64 image
make docker_push_prod       # to Artifact Registry
make cloudrun_deploy        # to Cloud Run
make cloudrun_url           # fetch the URL for SERVICE_URL
```

---

## 🔁 Continuous integration

`.github/workflows/ci.yml` runs on every push and has three jobs:

| Job | Checks |
|---|---|
| **Lint** | `ruff check` + `ruff format --check` |
| **Tests** | The 46 tests, with no secrets (the `.env` is recreated from `.env.sample`) |
| **Docker** | The image builds **and** the API actually answers inside the container |

The Docker job is the only place where the `Dockerfile` is validated
automatically — handy when step 2 of the API tests is not run locally.

---

## 🌿 Git workflow

The repository follows one simple rule: **one work batch = one branch = one
commit**.

```bash
git switch -c fix/my-topic           # prefixes: chore, fix, feat, ci, refactor, docs
# ... work, `make test_all`, `make lint` ...
git commit -m "fix: ..."
git push -u origin fix/my-topic      # the CI runs on the branch

git switch main
git merge --no-ff fix/my-topic       # --no-ff: keeps the batch visible
git push origin main
git branch -d fix/my-topic           # -d refuses an unmerged branch
git push origin --delete fix/my-topic
```

`--no-ff` is not cosmetic: without it, git performs a *fast-forward*, the batch
disappears from the history and becomes impossible to revert as a whole
(`git revert -m 1 <merge>`).

---

## 🔧 Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `make: command not found` | On Windows: work inside WSL2, not native Git Bash |
| `503 No model available` | Expected before the first training run: `make run_train` |
| `SERVICE_URL is not set` | Fetch the URL with `make cloudrun_url`, then set `SERVICE_URL` |
| The GCP tests fail by default | They are marked `integration`. Run `make test_integration` once GCP is configured |
| `uv sync --frozen` fails | `uv.lock` no longer matches `pyproject.toml`: `uv lock` |
| Every file shows as modified | CRLF/LF line endings. `.gitattributes` normalises them: `git add --renormalize .` |
| `Permission denied` on push | The GitHub token is missing a scope (`Contents`, `Workflows`…) |
| `make: No rule to make target` | The target was renamed: `make help` lists the real ones |

---

## 🎯 Adapting this template

The template runs end to end, but is deliberately generic. To reorient it, in
this order:

1. **`params.py`** — declare your columns (`NUMERIC_FEATURES`,
   `CATEGORICAL_FEATURES`, `TARGET_COLUMN`), your types (`DTYPES_RAW`) and your
   business thresholds. The rest of the code refers to them.
2. **`ml_logic/demo_data.py`** — replace `generate_demo_data()` with your real
   loading logic (the TODO in `get_raw_data()` holds the BigQuery query to
   complete), and adapt `clean_data()` to your cleaning rules.
3. **`ml_logic/preprocessor.py`** — adapt the transformations to your columns.
4. **`ml_logic/model.py`** — replace `Ridge` with your own estimator. The rest
   of the pipeline does not change: `train(**model_params)` forwards the
   hyperparameters.
5. **`api/schemas.py`** — align the input contract with your features.
6. **`ml_logic/registry.py`** — implement MLflow or GCS loading if you want to
   move beyond the local registry.
7. **Swagger documentation** — the API title and description live in
   `api/fast.py`.
