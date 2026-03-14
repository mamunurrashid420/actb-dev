from __future__ import annotations

import re

from xlake.api import get_version


def test_version_format() -> None:
    """Ensure version is a semver-like string."""
    version = get_version()
    assert isinstance(version, str)
    assert re.match(r"^\d+\.\d+\.\d+$", version)
