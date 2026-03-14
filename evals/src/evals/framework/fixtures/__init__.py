"""Tool fixtures for deterministic evaluation testing.

This module provides fixtures for mocking shared.data functions (search, describe, get)
with canned YAML responses, enabling deterministic testing of agents that use data tools.

Example:
    from evals.framework.fixtures import FixtureManager, ToolFixtures

    fixtures = ToolFixtures(tools="fixtures/tools/data_explorer.yaml")
    manager = FixtureManager()

    async with manager.apply(fixtures):
        # shared.data functions are mocked
        result = await agent.run(input)
"""

from evals.framework.fixtures.manager import FixtureManager
from evals.framework.fixtures.types import ToolFixtures

__all__ = ["FixtureManager", "ToolFixtures"]
