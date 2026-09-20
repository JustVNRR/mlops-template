# 🚀 MLOps Template

A [Copier](https://copier.readthedocs.io) template for a Machine Learning
project: training, experiment tracking, a serving API and GCP deployment —
driven by a Makefile, checked by a CI, and **runnable straight away, with no
cloud account**.

## 📋 Prerequisites

Three things on your machine:

| | What it is for | Install |
|---|---|---|
| **uv** | runs everything in the generated project — the virtualenv, the lock file, every Makefile target | `pip install uv`, or the [standalone installer](https://docs.astral.sh/uv/getting-started/installation/) |
| **Copier** | generates the project — once | `uv tool install copier` |
| **git** | Copier clones the template from GitHub before it can ask anything | your package manager, or [git-scm.com](https://git-scm.com/downloads) |

uv is the one that stays: Copier runs once, at generation, while uv sits behind
every command the project will ever run. It also brings its own Python — the
project pins its version in `.python-version`, and uv installs it if you do not
have it.

## 🚀 Generate a project

```bash
copier copy gh:JustVNRR/mlops-template <project-folder>
cd <project-folder>
```

Copier asks a few questions, writes the project, and prints the next steps. No
`git clone`, no renaming script, nothing to delete afterwards.

The generated project runs `make run_pipeline` immediately: it ships with a
synthetic demonstration dataset, so the whole pipeline — preprocess, train,
evaluate, predict — works before you have a cloud account or a single row of
real data. Replacing the demonstration pieces with your own is the subject of
the generated `README.md`.

## ❓ The questions

| Question | Answer | What it drives |
|---|---|---|
| `project_name` | **required** — suggested in grey as a placeholder | README title, the package docstring |
| `package_name` | derived from the name above | `src/`, every import, `uvicorn`, custom commands |
| `version` | `0.1.0`, refused unless it is `MAJOR.MINOR.PATCH` | `pyproject.toml` |
| `package_short_description` | the project name | `pyproject.toml` description |
| `author_name` | **required** | `pyproject.toml` |
| `author_email` | **required**, refused unless it looks like an address | `pyproject.toml` |
| `license` | `Proprietary` by default | `pyproject.toml`, and the `LICENSE` file |
| `copyright_holder` | the author — asked only for an open license | `LICENSE` |
| `modules` | all three by default | which optional building blocks the project gets |

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

The version is held to a rule of its own, for the same reason: hatchling reads
`project.version` and refuses to build what it cannot parse — `abc` and an
empty string both stop it. The rule runs the **other way** from the email rule,
though: it is narrower than what hatchling takes. `MAJOR.MINOR.PATCH` is the one
shape everybody writes, and asking only for that lets the message name an
example instead of a grammar. So `1.0`, which hatchling accepts, is refused with
an instruction to write `1.0.0`.

`package_short_description` is the one question whose default is another answer,
which keeps the generated `pyproject.toml` unchanged for anyone who presses
Enter. A title is a poor description, but it is a better one than an empty
string.

The license list is the one [NLeSC/python-template](https://github.com/NLeSC/python-template)
offers — Apache-2.0, MIT, BSD-3-Clause, ISC, GPL-3.0-or-later, LGPL-3.0-or-later
— with `Proprietary` in place of their `Other`. "Not one of these, all rights
reserved" is a decision a project can make, not a blank to fill in later, and it
is the default. The six open licenses each write their `LICENSE` text, and ask
who holds the copyright; `Proprietary` writes no file and asks nothing, because
there is no text to put the name in.

Only one of the six is ever written, and the condition is in the **filename**:
`{% if license == 'MIT' %}LICENSE{% endif %}.jinja` renders to nothing for the
other five, and a name that renders to nothing is a file Copier skips. That is
also why the tests look for the five missing files rather than the one expected
one — a broken condition writes all six, or none.

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

Four files belong to the generated project from the moment it exists:
`.gitignore`, `README.md`, the notebooks and `LICENSE`. `_skip_if_exists` means
the template never touches them again — not on `copier update`, and not on a
second `copier copy --overwrite` — so the user can make them theirs without
wondering what the next update will do to them.

`LICENSE` is on that list for a reason of its own. A legal document is not
something the template should keep an opinion about after the fact: it carries
the year of generation and nothing the template will ever need to correct, and
a project that added its own clauses would lose them to an update that had no
business touching it.

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
├── LICENSE         # Apache-2.0, the license of the template itself
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
   rather than `{% if 'gcp' in modules %}`; the three flags are derived in
   `copier/flags.yml`. The two are not interchangeable — `modules` is what was
   ticked, the flags are what the project is built with, and they part company
   the moment one block implies another. None does today, which is why each
   flag is a single line, but a file written against the list would silently
   miss the first block that does.

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
