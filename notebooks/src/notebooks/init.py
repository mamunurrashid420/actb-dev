"""Notebooks initialization module - provides common imports and setup.

This module is designed to be imported at the start of notebooks to provide
commonly used libraries and configure the environment.

Usage:
    from notebooks import init
    # Now pd, plt, data are available via init.pd, init.plt, init.data
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from notebooks/.env and .env.local (local overrides)
NOTEBOOKS_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(NOTEBOOKS_ROOT / ".env")
load_dotenv(NOTEBOOKS_ROOT / ".env.local", override=True)

# Set data path for shared.data module
REPO_ROOT = NOTEBOOKS_ROOT.parent
os.environ.setdefault(
    "ACTBI_DATA_PATH", str(REPO_ROOT / "pipelines" / "_data" / "assets")
)

# Standard imports for notebooks
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

import shared.data as data  # noqa: E402

# Set default environment to local for notebook development
data.use_env("local")

__all__ = ["pd", "plt", "data"]
