"""
MLOps project package.

Renamed by `make init_project`; the import name is declared in pyproject.toml.
"""

from package_folder.logging_config import setup_logging

# Configure logging on import. This package IS the application, not a library
# meant to be embedded: importing it anywhere — the API, the pipeline, a
# notebook, the tests — yields one coherent log stream, and no entry point can
# forget to set it up.
setup_logging()
