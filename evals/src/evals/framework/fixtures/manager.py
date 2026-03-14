"""Fixture manager for applying tool mocks during evaluation."""

from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

import yaml

from evals.framework.fixtures.types import ToolFixtures


class FixtureManager:
    """Manages tool fixtures for deterministic testing.

    The FixtureManager applies tool fixtures via patching shared.data functions.
    This enables deterministic testing by returning canned responses instead of
    making real data calls.

    Example:
        fixtures = ToolFixtures(tools="fixtures/tools/example.yaml")
        manager = FixtureManager()

        async with manager.apply(fixtures):
            # shared.data.search, describe, get are mocked
            result = await agent.run(input)
    """

    @asynccontextmanager
    async def apply(self, fixtures: ToolFixtures | None):
        """Apply tool fixtures via patching shared.data functions.

        Args:
            fixtures: Fixture configuration, or None to skip mocking.

        Yields:
            None - context manager for use with async with.

        Raises:
            ValueError: If no fixture match is found for an input.
            FileNotFoundError: If the fixture file doesn't exist.
        """
        if not fixtures or fixtures.tools == "live":
            yield
            return

        # Load responses from YAML
        fixture_path = Path(fixtures.tools)
        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture file not found: {fixture_path}")

        responses = yaml.safe_load(fixture_path.read_text())

        # Patch shared.data functions
        with (
            patch(
                "shared.data.search",
                side_effect=self._make_mock(responses.get("search", [])),
            ),
            patch(
                "shared.data.describe",
                side_effect=self._make_mock(responses.get("describe", [])),
            ),
            patch(
                "shared.data.get",
                side_effect=self._make_mock(responses.get("get", [])),
            ),
        ):
            yield

    def _make_mock(self, responses: list[dict]) -> callable:
        """Create a mock function that matches inputs to canned responses.

        Args:
            responses: List of {input: {...}, output: ...} dicts.

        Returns:
            A function that returns the matching output for given inputs.
        """
        # Sort responses by specificity (more input keys = more specific)
        # This ensures more specific matches are tried first
        sorted_responses = sorted(
            responses, key=lambda r: len(r.get("input", {})), reverse=True
        )

        def mock_fn(*args, **kwargs):
            # Normalize: if positional args, convert to kwargs based on common patterns
            # shared.data functions typically use: search(query), describe(asset_path), get(asset_path, partition)
            if args:
                if len(args) >= 1:
                    # First arg is typically 'query' for search or 'asset_path' for describe/get
                    kwargs.setdefault("query", args[0])
                    kwargs.setdefault("asset_path", args[0])
                if len(args) >= 2:
                    kwargs.setdefault("partition", args[1])

            for r in sorted_responses:
                if self._inputs_match(r.get("input", {}), kwargs):
                    return r["output"]
            raise ValueError(f"No fixture match for input: {kwargs}")

        return mock_fn

    def _inputs_match(self, expected: dict, actual: dict) -> bool:
        """Check if actual inputs match expected fixture inputs.

        Uses partial matching: expected inputs must be a subset of actual inputs.
        This allows fixtures to specify only the inputs they care about.

        Args:
            expected: Expected input values from fixture.
            actual: Actual input values from function call.

        Returns:
            True if all expected keys match actual values, False otherwise.
        """
        for key, value in expected.items():
            if key not in actual or actual[key] != value:
                return False
        return True
