"""Types for tool fixtures configuration."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class ToolFixtures(BaseModel):
    """Configuration for tool fixtures.

    Tool fixtures enable deterministic testing by mocking shared.data functions
    (search, describe, get) with canned responses from YAML files.

    Examples:
        Mock mode - return canned responses:
            ToolFixtures(tools="fixtures/tools/data_explorer.yaml")

        Live mode - no mocking:
            ToolFixtures(tools="live")
    """

    tools: Path | Literal["live"]
    """Path to YAML file with canned responses, or "live" for no mocking."""

    model_config = {"extra": "forbid"}
