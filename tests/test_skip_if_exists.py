"""Regenerating over a project that already exists.

`_skip_if_exists` in copier.yml promises that four files belong to the project
from the moment it is generated, and that the template will never touch them
again. That promise has to hold on the second pass, not only the first — which
is the pass `copier update` performs, and the one that can destroy work.

`copier update` itself is not exercised here: it resolves the template through
git, so it needs a clean working tree, and a test that only passes on a clean
tree is worse than no test. What it does at heart is render the template over
an existing directory, which is what this file does, with `overwrite=True` so
nothing can pass by simply not writing.
"""

from copier import run_copy

from conftest import BASE_ANSWERS

# The marker is the same in every file, so one search serves for all of them.
MINE = "# mine\n"

OWNED_BY_THE_PROJECT = [
    ".gitignore",
    "README.md",
    "notebooks/data_exploration.ipynb",
    "LICENSE",
]

# Not in the list: the template has to be able to fix it in a project that
# already exists.
REWRITTEN_BY_THE_TEMPLATE = "pyproject.toml"


def test_the_projects_own_files_survive_a_second_pass(copie, tmp_path):
    project = tmp_path / "project"
    source = str(copie.default_template_dir)

    run_copy(src_path=source, dst_path=str(project), defaults=True, unsafe=True, user_defaults=BASE_ANSWERS)

    for name in [*OWNED_BY_THE_PROJECT, REWRITTEN_BY_THE_TEMPLATE]:
        (project / name).write_text(MINE)

    run_copy(
        src_path=source,
        dst_path=str(project),
        defaults=True,
        unsafe=True,
        overwrite=True,
        user_defaults=BASE_ANSWERS,
    )

    for name in OWNED_BY_THE_PROJECT:
        assert (project / name).read_text() == MINE, f"{name} is the project's and was overwritten"
    assert MINE not in (project / REWRITTEN_BY_THE_TEMPLATE).read_text()
