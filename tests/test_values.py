"""The answers that break files, and the one the template refuses.

`project_name` and `author_name` are free text, and they land inside a TOML
string and a Python docstring. Answered with a plausible name they do nothing;
answered with the names below they used to produce a project that no longer
parsed — silently, with Copier exiting 0.

Escaping has to be sufficient for these values and no more than sufficient: an
apostrophe or an ampersand must come back exactly as typed, or the file reads
as if something went wrong. That is what rules out `tojson`, which would turn
both into a unicode escape.

Each value is used as the project name AND as the author name, in a single
generation: they go through the same escaping, and a failure names the value.
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


@pytest.mark.parametrize("name", HOSTILE_NAMES, ids=repr)
def test_the_names_survive_generation(generate, name):
    project = generate(project_name=name, author_name=name)

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
