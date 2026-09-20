"""The answers that break files, and the ones the template refuses.

`project_name`, `author_name` and `package_short_description` are free text, and
they land inside a Python docstring and two TOML strings. Answered with a
plausible name they do nothing; answered with the names below they used to
produce a project that no longer parsed — silently, with Copier exiting 0.

Escaping has to be sufficient for these values and no more than sufficient: an
apostrophe or an ampersand must come back exactly as typed, or the file reads
as if something went wrong. That is what rules out `tojson`, which would turn
both into a unicode escape.

Each value is used as all three, in a single generation: they go through the
same escaping, and a failure names the value.

The refusals below are the other half. An answer the build backend would choke
on has to be refused at the prompt, while it can still be corrected — escaping
it would only move the failure to the first `uv sync` on someone else's machine.
"""

import ast
import tomllib

import pytest

from conftest import BASE_ANSWERS, PACKAGE

HOSTILE_NAMES = [
    'Mr. "Quoted" Project',
    "Mr. O'Keefe",
    "Tom & Jerry",
    "Back\\slash",
    "Trailing backslash \\",
    'Triple "quoted" and """ closed',
]

MALFORMED_EMAILS = [
    "jane doe@example.com",
    "jane@example",
    "jane",
    '"o\'keefe"@example.com',
]

# `1.0` and `v1.0.0` are the interesting ones: hatchling builds a project with
# either, so refusing them is the template being harder on the answer than the
# backend is — the price of naming one shape in the message instead of a
# grammar. `abc` is the case where both agree.
MALFORMED_VERSIONS = ["abc", "1.0", "v1.0.0"]


@pytest.mark.parametrize("name", HOSTILE_NAMES, ids=repr)
def test_the_names_survive_generation(generate, name):
    project = generate(project_name=name, author_name=name, package_short_description=name)

    with (project / "pyproject.toml").open("rb") as handle:
        parsed = tomllib.load(handle)["project"]
    assert parsed["description"] == name
    assert parsed["authors"][0]["name"] == name

    source = (project / f"src/{PACKAGE}/__init__.py").read_text()
    docstring = ast.get_docstring(ast.parse(source))
    assert docstring is not None
    assert docstring.splitlines()[0] == f"{name}."


@pytest.mark.parametrize("email", MALFORMED_EMAILS)
def test_a_malformed_email_is_refused(copie, email):
    # The build backend parses this field, so escaping it would only hide the
    # problem: the answer has to be refused while it can still be corrected.
    result = copie.copy(extra_answers={**BASE_ANSWERS, "author_email": email})

    assert result.exit_code != 0
    assert "author_email" in str(result.exception)


@pytest.mark.parametrize("version", MALFORMED_VERSIONS)
def test_a_malformed_version_is_refused(copie, version):
    result = copie.copy(extra_answers={**BASE_ANSWERS, "version": version})

    assert result.exit_code != 0
    assert "version" in str(result.exception)
