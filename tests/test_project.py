"""What the template generates, and what each building block adds to it.

Nothing is imported from the template: it is not a package, its sources are not
valid Python (`src/{{ package_name }}/`), and there is nothing to call. Every
test here generates a project with pytest-copie and reads the result from disk,
which is the only way to check a Copier template.

The fixture runs Copier in-process with `defaults=True`, so the questions are
never asked — and the validators still run, exactly as they do under
`copier copy --defaults`.

Generating is not enough on its own: the CI also installs, lints, tests and
runs the projects it generates. What this file adds is breadth — every
combination of building blocks, where the CI samples two.
"""

import json
import re
import tomllib
from itertools import combinations
from pathlib import Path

import pytest
import yaml

from conftest import BASE_ANSWERS, MODULES, PACKAGE

# What every project receives, whatever was ticked. The container is not a
# building block: `make docker_build_local`, `make test_api_docker` and the
# docker-compose file have nothing to do with the cloud, and the container tier
# is the only way to run the API under the conditions it meets in production.
ALWAYS_THERE = [
    "Dockerfile",
    ".dockerignore",
    "docker-compose.yml",
    "make/docker.mk",
    "tests/api/test_docker_endpoints.py",
    ".github/workflows/docker.yml",
]

# What each building block adds. `mlflow` is missing on purpose: it adds no
# file, it rewrites the content of files that are always there, so it gets its
# own test.
FILES_PER_MODULE = {
    "gcp": [
        "make/gcp.mk",
        "make/bigquery.mk",
        "make/vm.mk",
        "make/cloudrun.mk",
        "scripts/setup_vm.sh",
        "tests/infrastructure/test_gcp_setup.py",
        "tests/api/test_cloud_endpoints.py",
    ],
    "prefect": [f"src/{PACKAGE}/interface/workflow.py"],
}

# `gcp` reaches into make/docker.mk: publishing an image to Artifact Registry
# needs both, and those targets live with the container, not with the cloud.
GCP_TARGETS_IN_DOCKER_MAKE = ["artifact_registry", "docker_push_prod"]

ALL_SUBSETS = [list(combo) for size in range(len(MODULES) + 1) for combo in combinations(MODULES, size)]


@pytest.mark.parametrize("modules", ALL_SUBSETS, ids=lambda modules: "+".join(modules) or "none")
def test_each_building_block_brings_exactly_its_files(generate, modules):
    project = generate(modules=modules)

    for path in ALWAYS_THERE:
        assert (project / path).exists(), f"{path} belongs to every project"

    for module, files in FILES_PER_MODULE.items():
        for path in files:
            exists = (project / path).exists()
            if module in modules:
                assert exists, f"{path} is missing from a project built with {module}"
            else:
                assert not exists, f"{path} survived in a project built without {module}"


def test_mlflow_rewrites_content_instead_of_adding_files(generate):
    with_mlflow = generate(modules=["mlflow"])
    without = generate(modules=[])

    assert any(dependency.startswith("mlflow") for dependency in project_dependencies(with_mlflow))
    assert not any(dependency.startswith("mlflow") for dependency in project_dependencies(without))

    registry = f"src/{PACKAGE}/ml_logic/registry.py"
    assert "import mlflow" in (with_mlflow / registry).read_text()
    assert "import mlflow" not in (without / registry).read_text()


def test_the_gcp_targets_stay_out_when_gcp_was_not_ticked(generate):
    docker_make = (generate(modules=[]) / "make/docker.mk").read_text()

    assert "docker_build_local" in docker_make
    for target in GCP_TARGETS_IN_DOCKER_MAKE:
        assert target not in docker_make, f"{target} needs GCP and should not be there"


def test_the_gcp_targets_are_back_when_gcp_was_ticked(generate):
    docker_make = (generate(modules=["gcp"]) / "make/docker.mk").read_text()

    for target in GCP_TARGETS_IN_DOCKER_MAKE:
        assert target in docker_make


def test_the_readme_only_names_targets_the_project_has(generate):
    # Documenting a target the project does not have is worse than omitting a
    # real one: the reader types it, make refuses, and the project looks broken.
    # It is also invisible to a search for the building block's name — the cloud
    # tier is reached through `test_api_cloud`, which says neither GCP nor
    # gcloud.
    full = generate(modules=MODULES)
    minimal = generate(modules=[])
    mentioned = {project: mentioned_targets(project) for project in (full, minimal)}

    for project, targets in mentioned.items():
        invented = targets - defined_targets(project)
        assert not invented, f"the README documents targets that do not exist: {sorted(invented)}"

    # The guard above must not be satisfied by documenting nothing at all: the
    # cloud tier is named where its target exists.
    assert "test_api_cloud" in mentioned[full]
    assert "test_api_cloud" not in mentioned[minimal]


def test_no_answer_placeholder_survives(generate):
    project = generate()

    # A file whose name lost its `.jinja` suffix is copied byte for byte, and
    # keeps the placeholder — the generated project then fails at runtime,
    # somewhere else entirely.
    offenders = [
        path.relative_to(project).as_posix()
        for path in project.rglob("*")
        if path.is_file() and "package_folder" in path.read_text(errors="ignore")
    ]
    assert not offenders, f"a file was copied without being rendered: {offenders}"


def test_the_generated_files_are_parseable(generate):
    project = generate()

    with (project / "pyproject.toml").open("rb") as handle:
        assert tomllib.load(handle)["project"]["name"] == PACKAGE

    # A notebook that does not parse is a corrupted file, not a broken notebook.
    notebooks = list((project / "notebooks").glob("*.ipynb"))
    assert notebooks
    for notebook in notebooks:
        assert json.loads(notebook.read_text())["nbformat"] == 4


def test_the_answers_file_records_what_was_answered(generate):
    # `copier update` reads this file back: a project generated without it can
    # never be updated.
    project = generate()
    answers = yaml.safe_load((project / ".copier-answers.yml").read_text())

    assert answers["project_name"] == BASE_ANSWERS["project_name"]
    assert answers["package_name"] == PACKAGE
    assert answers["author_name"] == BASE_ANSWERS["author_name"]
    assert answers["modules"] == MODULES


def project_dependencies(project: Path) -> list[str]:
    with (project / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]["dependencies"]


def mentioned_targets(project: Path) -> set[str]:
    """Every `make <target>` the README invites the reader to run.

    Two shapes count: a command on a line of its own inside a fenced block, and
    a backticked mention in prose. The README also talks about make without
    naming a target — the `Makefile`, the `make: No rule to make target` error —
    so the word alone is not enough.
    """
    readme = (project / "README.md").read_text()
    targets = set(re.findall(r"`make ([a-z][a-z0-9_]*)`", readme))

    in_fence = False
    for line in readme.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        elif in_fence and (command := re.match(r"make ([a-z][a-z0-9_]*)", line)):
            targets.add(command.group(1))

    return targets


def defined_targets(project: Path) -> set[str]:
    """Every target the project's Makefile defines, sub-makefiles included."""
    sources = [project / "Makefile", *sorted((project / "make").glob("*.mk"))]
    return {
        target.group(1)
        for source in sources
        for target in re.finditer(r"^([a-z][a-z0-9_-]*):", source.read_text(), re.MULTILINE)
    }
