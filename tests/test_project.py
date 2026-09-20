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
        "make/artifact_registry.mk",
        "scripts/setup_vm.sh",
        "tests/infrastructure/test_gcp_setup.py",
        "tests/api/test_cloud_endpoints.py",
    ],
    "prefect": [f"src/{PACKAGE}/interface/workflow.py"],
}

# Every target that needs a GCP project. They live in a file of their own, which
# only a project built with `gcp` receives. `make/docker.mk` ships to all of
# them, so it must not know about any of these.
GCP_ONLY_TARGETS = [
    "artifact_registry_create",
    "artifact_registry_role",
    "artifact_registry_auth",
    "docker_build_prod",
    "docker_push_prod",
]

# What a file copied without being rendered keeps: a Jinja substitution
# (`{{ package_name }}`) or a tag (`{% if with_gcp %}`). The two shapes that
# must NOT count are the ones a verbatim file is entitled to carry — a GitHub
# expression (`${{ github.workflow }}`) and a Go template (`{{.Ports}}`, in the
# docker API test).
JINJA_LEFTOVER = re.compile(r"(?<!\$)\{\{\s*[A-Za-z_]|\{%")

# Directories a generated project fills with other people's files.
NOT_OURS = {".git", ".venv", "__pycache__", ".ruff_cache", ".pytest_cache"}

# One LICENSE file per license, each holding the text it is named after. The
# marker is a line that appears in that text and in no other — checked, since
# the six files are one careless copy-paste apart. `Proprietary` has no marker:
# a project that keeps its source closed has no license text to write.
LICENSE_MARKERS = {
    "Proprietary": None,
    "Apache-2.0": "Apache License",
    "MIT": "MIT License",
    "BSD-3-Clause": "BSD 3-Clause License",
    "ISC": "ISC License",
    "GPL-3.0-or-later": "GNU GENERAL PUBLIC LICENSE",
    "LGPL-3.0-or-later": "GNU LESSER GENERAL PUBLIC LICENSE",
}

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


@pytest.mark.parametrize("license", LICENSE_MARKERS)
def test_the_license_answer_decides_which_file_lands(generate, license):
    # The other five are absent, not empty: the condition lives in the FILENAME
    # and a name that renders to nothing is skipped. Looking only for the
    # expected file would not see a template that writes several of them.
    project = generate(license=license)
    landed = sorted(path.name for path in project.iterdir() if path.name.startswith("LICENSE"))

    marker = LICENSE_MARKERS[license]
    if marker is None:
        assert landed == [], "a project with no license gets no license file"
        return

    assert landed == ["LICENSE"]
    # The right TEXT, not merely a file: the six are one copy and one rename
    # apart, so a wrong condition is invisible from the file name alone.
    text = (project / "LICENSE").read_text()
    assert marker in text
    if license != "LGPL-3.0-or-later":
        # That one text carries no copyright line: the FSF's "how to apply"
        # appendix belongs to the GPL, and the LGPL as shipped has no such tag.
        assert BASE_ANSWERS["author_name"] in text


def test_mlflow_rewrites_content_instead_of_adding_files(generate):
    with_mlflow = generate(modules=["mlflow"])
    without = generate(modules=[])

    assert any(dependency.startswith("mlflow") for dependency in project_dependencies(with_mlflow))
    assert not any(dependency.startswith("mlflow") for dependency in project_dependencies(without))

    registry = f"src/{PACKAGE}/ml_logic/registry.py"
    assert "import mlflow" in (with_mlflow / registry).read_text()
    assert "import mlflow" not in (without / registry).read_text()


def test_the_container_file_knows_nothing_about_the_cloud(generate):
    # The container is in every project, so a cloud target left in its file
    # would land in a project without a cloud account. That is the rule the
    # split into `artifact_registry.mk` exists to hold.
    for modules in ([], ["gcp"]):
        docker_make = (generate(modules=modules) / "make/docker.mk").read_text()

        assert "docker_build_local" in docker_make
        for target in GCP_ONLY_TARGETS:
            assert target not in docker_make, f"{target} does not belong to the container file"


def test_the_gcp_targets_live_in_their_own_file(generate):
    registry_make = (generate(modules=["gcp"]) / "make/artifact_registry.mk").read_text()

    for target in GCP_ONLY_TARGETS:
        assert target in registry_make, f"{target} is missing from artifact_registry.mk"


def test_no_gcp_target_survives_without_gcp(generate):
    # The `reduced` CI job greps `make help` for the same thing; this version
    # reads the files, so it can name what it found.
    defined = defined_targets(generate(modules=[]))
    survivors = sorted(target for target in GCP_ONLY_TARGETS if target in defined)

    assert not survivors, f"these need a GCP project and survived: {survivors}"


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
    # keeps its `{{ ... }}` — the generated project then fails at runtime,
    # somewhere else entirely.
    offenders = [
        path.relative_to(project).as_posix()
        for path in project.rglob("*")
        if path.is_file()
        and not NOT_OURS.intersection(path.parts)
        and JINJA_LEFTOVER.search(path.read_text(errors="ignore"))
    ]
    assert not offenders, f"a file was copied without being rendered: {offenders}"


def test_the_generated_files_are_parseable(generate):
    project = generate()

    with (project / "pyproject.toml").open("rb") as handle:
        metadata = tomllib.load(handle)["project"]
    assert metadata["name"] == PACKAGE
    # Both of these have a default, so reading back the default would pass with
    # the wiring cut: the answers are deliberately not what the template would
    # have written on its own.
    assert metadata["version"] == BASE_ANSWERS["version"]
    assert metadata["description"] == BASE_ANSWERS["package_short_description"]

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
    assert answers["version"] == BASE_ANSWERS["version"]
    assert answers["package_short_description"] == BASE_ANSWERS["package_short_description"]
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
