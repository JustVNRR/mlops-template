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

| Question | Default | What it drives |
|---|---|---|
| `project_name` | `My MLOps Project` | README title, `pyproject.toml` description |
| `package_name` | derived from the name above | `src/`, every import, `uvicorn`, custom commands |
| `author_name` | — | `pyproject.toml` |
| `author_email` | — | `pyproject.toml` |
| `license` | `Proprietary` | `pyproject.toml` |

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
registry, optional MLflow tracking and Prefect orchestration, BigQuery and Cloud
Run deployment paths, notebooks, and a test suite split by tier (in memory,
container, deployed). The generated `README.md` documents all of it.
