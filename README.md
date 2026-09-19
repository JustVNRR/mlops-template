# 🚀 MLOps Template

A [Copier](https://copier.readthedocs.io) template for a Machine Learning
project: training, experiment tracking, a serving API and GCP deployment —
driven by a Makefile, checked by a CI, and **runnable straight away, with no
cloud account**.

## 🚀 Generate a project

```bash
copier copy gh:JustVNRR/mlops-template my-project
cd my-project
```

Copier asks a few questions, writes the project, and prints the next steps. No
`git clone`, no renaming script, nothing to delete afterwards.

The generated project runs `make run_all` immediately: it ships with a
synthetic demonstration dataset, so the whole pipeline — preprocess, train,
evaluate, predict — works before you have a cloud account or a single row of
real data. Replacing the demonstration pieces with your own is the subject of
the generated `README.md`.

## ❓ The questions

| Question | Answer | What it drives |
|---|---|---|
| `project_name` | **required** — suggested in grey as a placeholder | README title, `pyproject.toml` description |
| `package_name` | derived from the name above | `src/`, every import, `uvicorn`, custom commands |
| `author_name` | **required** | `pyproject.toml` |
| `author_email` | **required** | `pyproject.toml` |
| `license` | `Proprietary` by default | `pyproject.toml` |
| `modules` | all four by default | which optional building blocks the project gets |

The required ones have a `placeholder` and no `default`: the field shows an
example in grey, and the question comes back until something is typed. A
placeholder alone would accept an empty answer without a word, which is why
each of them also carries a `validator`. That also means `copier copy
--defaults` needs those three answers passed with `-d` — which is what the CI
does.

### The building blocks

`modules` is a multi-select. Untick what you do not need and the corresponding
files, dependencies, Makefile targets, tests, environment variables and README
sections simply are not there — not commented out, absent.

| Block | What it brings | Unticked, the project loses |
|---|---|---|
| `gcp` | BigQuery, Cloud Storage, a training VM, Cloud Run | `make/{gcp,bigquery,vm,cloudrun}.mk`, the cloud dependencies, the GCP tests, `DATA_SOURCE=bigquery` |
| `mlflow` | experiment tracking, model registry, aliases | the MLflow half of `registry.py`, the `@mlflow_run` decorators, the promotion step of the workflow |
| `prefect` | orchestration of the full retraining cycle | `interface/workflow.py` in its entirety, `make run_workflow` |
| `docker` | packaging the API as an image | the `Dockerfile`, `docker-compose.yml`, `make/docker.mk`, the Docker CI workflow |

Every combination is meant to work. Only two are checked by the CI: the full
project and a project with no block at all.

`gcp` and `docker` overlap once: publishing an image to Artifact Registry needs
both, so those targets live in `make/docker.mk` under a `gcp` condition.

## 🗂️ This repository

This repository is a **template**, not a project: it has no `pyproject.toml`, no
installable package, nothing to run. Everything a generated project receives
lives under `template/`.

```
.
├── copier.yml      # the questions, the file exclusions, the closing message
├── README.md       # this file — about the template
├── .github/        # generates a project, then validates THAT project
└── template/       # everything the generated project receives, verbatim
```

### Two rules when editing the template

1. **A file whose content depends on an answer must be named `*.jinja`.** Copier
   copies every other file byte for byte; only suffixed files are rendered, and
   the suffix is stripped on output. A file left without the suffix keeps
   `{{ package_name }}` literally — a silent, confusing failure.

2. **A file that must NOT be rendered has to stay without the suffix.** GitHub
   Actions expressions (`${{ github.workflow }}`) and Go templates
   (`{{.Ports}}`) are perfectly valid inside un-suffixed files, and Jinja would
   choke on them. This is why the shipped CI workflow carries no suffix.

3. **A Jinja tag does not swallow the newline that follows it** — only the text
   after the tag on the same line is emitted. So `{% endif %}` at the end of a
   line always emits that newline, while `{% endif %}` followed by content
   emits the content and nothing more. Two consequences, both met in practice:
   a closing tag at the end of a file leaves a trailing blank line that
   `ruff format --check` rejects, and a guard whose two branches need different
   blank-line counts cannot satisfy both. The shape that works everywhere is an
   opening tag glued to the first line of content and a closing tag glued to
   the next line of content; when that is not enough, move the guard away from
   the boundary it sits on.

Copier filters `template/` through `.gitignore` — **including the one at the
repository root**, since its rules apply at every level. That cuts both ways: a
leftover from a local run (a dataset, a virtualenv) is skipped for free, but a
file you *want* to ship must not match an ignore rule. This is exactly how
`.env.sample.jinja` disappeared once: `template/.gitignore` ignored `.env.*`,
and only `.env.sample` was exempted.

`_exclude` in `copier.yml` covers the rest: the runtime directories under
`models/`, which no ignore rule mentions, and the optional building blocks.

## ✅ How this repository is validated

There is nothing to lint, test or build at the root. The CI generates a real
project from the template and runs lint, tests and the Docker smoke test
**inside it** — the only validation that means anything here.

Because of that, changes to the template are checked by pushing a branch and
reading the CI, not by running `make` locally.

## 📦 What a generated project contains

A FastAPI service, a scikit-learn pipeline driven by a Makefile, a local model
registry, notebooks, a test suite split by tier (in memory, container,
deployed), and — depending on the answer to `modules` — MLflow tracking,
Prefect orchestration and the Google Cloud deployment paths. The generated
`README.md` documents exactly what that project contains, and nothing else.
