"""Pytest fixtures for agent evaluation."""

from unittest.mock import patch

import pytest
from dotenv import load_dotenv
from pydantic_evals import Dataset

from agents.data_explorer import DataExplorer
from agents.viz_designer import VisualizationDesigner
from evals.datasets import data_explorer, viz_designer
from evals.mocks.data import MOCK_ASSETS

# Load .env and .env.local for API keys and model configuration
load_dotenv()
load_dotenv(".env.local", override=True)


# ─────────────────────────────────────────────────────────────
# VisualizationDesigner Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def agent():
    """Create a VisualizationDesigner agent instance."""
    return VisualizationDesigner()


@pytest.fixture
def basic_dataset():
    """Dataset with basic test cases."""
    return Dataset(cases=viz_designer.BASIC_CASES)


@pytest.fixture
def full_dataset():
    """Dataset with all test cases."""
    return Dataset(cases=viz_designer.ALL_CASES)


# ─────────────────────────────────────────────────────────────
# DataExplorer Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def data_explorer_agent():
    """Create a DataExplorer agent instance with higher iteration limit."""
    return DataExplorer(max_iterations=10)


@pytest.fixture
def economic_dataset():
    """Dataset with economic data test cases."""
    return Dataset(cases=data_explorer.ECONOMIC_CASES)


@pytest.fixture
def data_explorer_full_dataset():
    """Dataset with all DataExplorer test cases."""
    return Dataset(cases=data_explorer.ALL_CASES)


# ─────────────────────────────────────────────────────────────
# Mock Data Layer Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def mock_data_layer():
    """Mock shared.data functions for DataExplorer integration tests.

    This fixture mocks the data layer (search, describe, get) so that
    integration tests can run without requiring actual data files while
    still using a real LLM to test the full agent flow.
    """
    with (
        patch("agents.tools.data_discovery.search") as mock_search,
        patch("agents.tools.data_discovery.describe") as mock_describe,
        patch("agents.tools.data_discovery.get") as mock_get,
    ):

        def search_handler(query: str) -> list[str]:
            q = query.lower()
            matches = []
            if "gdp" in q or "economic" in q or "growth" in q:
                matches.append("gold/economic/growth/gdp")
            if "sec" in q or "financial" in q or "revenue" in q or "corporate" in q:
                matches.append("gold/sec/financials")
            return matches

        def describe_handler(asset_path: str):
            if asset_path in MOCK_ASSETS:
                return MOCK_ASSETS[asset_path]["metadata"]
            raise ValueError(f"Unknown asset: {asset_path}")

        def get_handler(asset_path: str, partition: str | None = None):
            if asset_path in MOCK_ASSETS:
                return MOCK_ASSETS[asset_path]["data"]
            raise ValueError(f"Unknown asset: {asset_path}")

        mock_search.side_effect = search_handler
        mock_describe.side_effect = describe_handler
        mock_get.side_effect = get_handler

        yield
