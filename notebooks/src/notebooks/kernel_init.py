"""actBI kernel initialization - runs when kernel starts."""

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
