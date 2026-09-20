# 🚀 MLOps Template

A [Copier](https://copier.readthedocs.io) template for a Machine Learning
project: training, experiment tracking, a serving API and GCP deployment —
driven by a Makefile, checked by a CI, and **runnable straight away, with no
cloud account**.

## 🚀 Generate a project

```bash
copier copy gh:JustVNRR/mlops-template <project-folder>
cd <project-folder>
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
| `author_email` | **required**, refused unless it looks like an address | `pyproject.toml` |
| `license` | `Proprietary` by default | `pyproject.toml` |
| `modules` | all four by default | which optional building blocks the project gets |

The required ones have a `placeholder` and no `default`: the field shows an
example in grey, and the question comes back until something is typed. A
placeholder alone would accept an empty answer without a word, which is why
each of them also carries a `validator`. That also means `copier copy
--defaults` needs those three answers passed with `-d` — which is what the CI
does.

The email address is held to a tighter rule than "not empty", because the build
backend parses that field: hatchling reads `authors[].email` and refuses to
build a project whose address is malformed. A space, or a domain without a dot,
and the generated project cannot even `uv sync`. The validator accepts what
hatchling accepts, minus the exotic forms nobody types.

### The building blocks

`modules` is a multi-select. Untick what you do not need and the corresponding
files, dependencies, Makefile targets, tests, environment variables and README
sections simply are not there — not commented out, absent.

| Block | What it brings | Unticked, the project loses |
|---|---|---|
| `gcp` | BigQuery, Cloud Storage, a training VM, Cloud Run | `make/{gcp,bigquery,vm,cloudrun}.mk`, the cloud dependencies, the GCP tests, `DATA_SOURCE=bigquery` |
| `mlflow` | experiment tracking, model registry, aliases | the MLflow half of `registry.py`, the `@mlflow_run` decorators, the promotion step of the workflow |
| `prefect` | orchestration of the full retraining cycle | `interface/workflow.py` in its entirety, `make run_workflow` |

Every combination the questions allow is meant to work, and
`tests/test_project.py` tries all eight of them.

The container is deliberately **not** on that list. `Dockerfile`,
`docker-compose.yml`, `make/docker.mk` and the container tier of the API tests
have nothing to do with the cloud: they are how the API is run under the
conditions it meets in production, and how the image that a deployment needs
gets built. Unticking everything still leaves `make docker_build_local` and
`make test_api_docker`.

`gcp` reaches into `make/docker.mk` exactly once — publishing an image to
Artifact Registry needs both — so those targets live with the container, under
a `gcp` condition.

### What the project owns

Three files belong to the generated project from the moment it exists:
`.gitignore`, `README.md` and the notebooks. `_skip_if_exists` means the
template never touches them again — not on `copier update`, and not on a second
`copier copy --overwrite` — so the user can make them theirs without wondering
what the next update will do to them.

Nothing else is on that list. The files the generated `README.md` invites the
user to adapt — `params.py`, `data.py`, `model.py` and the rest — are code, and
a fix to code has to be able to reach a project that already exists. Updating
those is safe already: `copier update` applies a three-way patch, so a template
change lands without erasing what the user wrote around it, and a genuine
conflict is reported rather than applied.

## 🗂️ This repository

This repository is a **template**, not a project: there is no installable
package and nothing to run. Everything a generated project receives lives under
`template/`.

```
.
├── copier.yml      # an index: one !include per section, and nothing else
├── copier/         # the sections themselves — settings, messages, questions, flags
├── README.md       # this file — about the template
├── pyproject.toml  # the template's OWN tests: nothing is built or published
├── tests/          # generates projects, then asserts on what came out
├── .github/        # generates a project, then validates THAT project
└── template/       # everything the generated project receives, verbatim
```

`copier.yml` holds no configuration of its own. It is an index of YAML
documents, one `!include` each, and Copier merges them in order. The split
follows the file's four concerns: `settings.yml` (what is rendered, what is
excluded, what the project owns), `messages.yml` (the four moments Copier talks
to the user), `questions.yml` and `flags.yml`. Two rules come with it:

- **A key starting with `_` is a setting; anything else is a question.** That is
  Copier's own rule, not ours, and it is what makes the four sections
  interchangeable — `_message_after_copy` is the setting `message_after_copy`.
- **The four list-valued settings** (`_exclude`, `_skip_if_exists`, …)
  **are concatenated** across the documents, so their entries can be split
  wherever they read best. For any other key, the last document wins — which is
  why the flags, derived from the answers, are in the last one.

### Rules when editing the template

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

4. **A free-text answer is escaped before it lands in a file that has a syntax
   of its own.** The answer is free text; `pyproject.toml` and the docstring of
   `__init__.py` are not. Written raw, `Mr. "Quoted" Project` produced a
   `pyproject.toml` that nothing could parse — and Copier exited 0 without a
   word. So an answer goes through
   `replace('\\', '\\\\') | replace('"', '\\"')` — the backslash first, always —
   wherever a quote or a backslash would mean something. `package_name`
   (regex-validated) and `license` (a fixed list of choices) cannot contain
   either character, so they are injected as they are.

5. **A condition tests a computed flag, never the answer list.** `{% if with_gcp %}`
   rather than `{% if 'gcp' in modules %}`; the four flags are derived at the
   bottom of `copier/flags.yml`. The two are not interchangeable — `modules` is what
   was ticked, the flags are what the project is built with, and they differ
   the moment one block implies another, which is precisely what `with_docker`
   exists for. A file written against the list silently misses that.

Copier filters `template/` through `.gitignore` — **including the one at the
repository root**, since its rules apply at every level. That cuts both ways: a
leftover from a local run (a dataset, a virtualenv) is skipped for free, but a
file you *want* to ship must not match an ignore rule. This is exactly how
`.env.sample.jinja` disappeared once: `template/.gitignore` ignored `.env.*`,
and only `.env.sample` was exempted.

`_exclude` in `copier/settings.yml` covers the rest: the runtime directories under
`models/`, which no ignore rule mentions, and the optional building blocks.

## ✅ How this repository is validated

Most of the CI generates a real project from the template and runs lint, tests
and the Docker smoke test **inside it** — the only validation that means
anything, since the template's own sources are not valid Python.

```bash
uv sync && uv run pytest     # the fast loop, run from the repository root
```

`tests/` generates projects with [pytest-copie](https://github.com/12rambau/pytest-copie)
and reads the result from disk: every combination of building blocks, and the
answers that break files. It says nothing about whether a generated project
*works* — that is what the jobs below are for. When a building block gains or
loses a file, `FILES_PER_MODULE` in `tests/test_project.py` is the list to
update.

One job generates a project from hostile answers — a quote, a backslash, a
triple quote — and checks that each one comes back verbatim. An escaping bug is
invisible in the other jobs: they answer with friendly names. It also checks
that a malformed email address is refused, not written out.

Changes to the template are therefore still checked by pushing a branch and
reading the CI, which is what installs, lints and runs the generated projects.

## 📦 What a generated project contains

A FastAPI service, a scikit-learn pipeline driven by a Makefile, a local model
registry, notebooks, a test suite split by tier (in memory, container,
deployed), and — depending on the answer to `modules` — MLflow tracking,
Prefect orchestration and the Google Cloud deployment paths. The generated
`README.md` documents exactly what that project contains, and nothing else.
