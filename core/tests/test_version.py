"""Tests for version consistency.

Ensure the in-package __version__ matches the `project.version` in pyproject.toml
when running tests from the repository. If `pyproject.toml` cannot be found the test
will be skipped (useful when running against an installed package where the file
is not available).
"""

from pathlib import Path

import pytest
import tomllib
from stocksense import __version__


def _find_pyproject(start: Path) -> Path | None:
    """Search up the directory tree for pyproject.toml starting at `start`."""
    for parent in [start] + list(start.parents):
        candidate = parent / "pyproject.toml"
        if candidate.exists():
            return candidate
    return None


def test_version_matches_pyproject() -> None:
    pyproject = _find_pyproject(Path(__file__).resolve())
    if pyproject is None:
        pytest.skip(
            "pyproject.toml not found in parent tree; skipping version match test"
        )

    with pyproject.open("rb") as f:
        data = tomllib.load(f)

    proj_version = data.get("project", {}).get("version")
    assert proj_version is not None, "`project.version` is missing from pyproject.toml"
    assert proj_version == __version__, (
        f"Version mismatch: pyproject.toml has {proj_version!r} but stocksense.__version__ is {__version__!r}"
    )
