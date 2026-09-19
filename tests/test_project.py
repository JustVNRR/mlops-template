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
import tomllib
from itertools import combinations
from pathlib import Path

import pytest
import yaml
from conftest import BASE_ANSWERS, MODULES, PACKAGE

# What each building block puts on disk. `mlflow` is missing on purpose: it adds
# no file, it rewrites the content of files that are always there, so it gets
# its own test.
FILES_PER_MODULE = {
    "docker": [
        "Dockerfile",
        ".dockerignore",
        "docker-compose.yml",
        "make/docker.mk",
        "tests/api/test_docker_endpoints.py",
        ".github/workflows/docker.yml",
    ],
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

# `docker` and `gcp` overlap exactly once: publishing an image to Artifact
# Registry needs both, and those targets live in make/docker.mk.
GCP_TARGETS_IN_DOCKER_MAKE = ["artifact_registry", "docker_push_prod"]

ALL_SUBSETS = [list(combo) for size in range(len(MODULES) + 1) for combo in combinations(MODULES, size)]


@pytest.mark.parametrize("modules", ALL_SUBSETS, ids=lambda modules: "+".join(modules) or "none")
def test_each_building_block_brings_exactly_its_files(generate, modules):
    project = generate(modules=modules)

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


def test_the_gcp_targets_stay_out_of_a_docker_only_project(generate):
    docker_make = (generate(modules=["docker"]) / "make/docker.mk").read_text()

    assert "docker_build_local" in docker_make
    for target in GCP_TARGETS_IN_DOCKER_MAKE:
        assert target not in docker_make, f"{target} needs GCP and should not be there"


def test_the_gcp_targets_are_back_in_a_project_that_has_both(generate):
    docker_make = (generate(modules=["docker", "gcp"]) / "make/docker.mk").read_text()

    for target in GCP_TARGETS_IN_DOCKER_MAKE:
        assert target in docker_make


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
