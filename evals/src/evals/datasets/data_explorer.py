"""Test case datasets for DataExplorer agent."""

from pydantic import BaseModel, ConfigDict
from pydantic_evals import Case
from pydantic_evals.evaluators import Evaluator

from agents.data_explorer.schemas import DataExplorerInput, DataExplorerOutput
from evals.evaluators.data_explorer import (
    AssetCountInRange,
    AssetPathContains,
    HasRecommendation,
    RationaleContains,
)


class DataExplorerCase(BaseModel):
    """DataExplorer test case with dict validation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    inputs: DataExplorerInput
    expected_output: DataExplorerOutput | None = None
    evaluators: list[Evaluator] = []
    metadata: dict = {}

    def to_case(self) -> Case[DataExplorerInput, DataExplorerOutput, dict]:
        """Convert to pydantic_evals Case for evaluation."""
        return Case(
            name=self.name,
            inputs=self.inputs,
            expected_output=self.expected_output,
            evaluators=tuple(self.evaluators),
            metadata=self.metadata,
        )


# ─────────────────────────────────────────────────────────────
# Economic Data Discovery
# ─────────────────────────────────────────────────────────────

GDP_SEARCH = DataExplorerCase.model_validate({
    "name": "gdp_search",
    "inputs": {
        "query": "Find GDP data for the United States",
        "focus_areas": ["economic"],
        "max_results": 5,
    },
    "evaluators": [
        AssetPathContains(keyword="gdp"),
        AssetCountInRange(min_count=1, max_count=5),
        HasRecommendation(),
        RationaleContains(must_contain=["gdp"]),
    ],
    "metadata": {"category": "economic", "difficulty": "easy"},
})

UNEMPLOYMENT_SEARCH = DataExplorerCase.model_validate({
    "name": "unemployment_search",
    "inputs": {
        "query": "What unemployment data is available?",
        "focus_areas": ["economic"],
        "max_results": 5,
    },
    "evaluators": [
        AssetCountInRange(min_count=1),
        HasRecommendation(),
    ],
    "metadata": {"category": "economic"},
})

# ─────────────────────────────────────────────────────────────
# Corporate Data Discovery
# ─────────────────────────────────────────────────────────────

SEC_FINANCIALS = DataExplorerCase.model_validate({
    "name": "sec_financials",
    "inputs": {
        "query": "Find company financial statements from SEC filings",
        "focus_areas": ["corporate"],
        "max_results": 5,
    },
    "evaluators": [
        AssetPathContains(keyword="sec"),
        HasRecommendation(),
        RationaleContains(must_contain=["sec"]),
    ],
    "metadata": {"category": "corporate"},
})

COMPANY_SEGMENTS = DataExplorerCase.model_validate({
    "name": "company_segments",
    "inputs": {
        "query": "How can I see revenue breakdown by region for companies?",
        "focus_areas": ["corporate"],
        "max_results": 5,
    },
    "evaluators": [
        AssetCountInRange(min_count=1),
        HasRecommendation(),
    ],
    "metadata": {"category": "corporate"},
})

# ─────────────────────────────────────────────────────────────
# Cross-domain Queries
# ─────────────────────────────────────────────────────────────

BROAD_SEARCH = DataExplorerCase.model_validate({
    "name": "broad_search",
    "inputs": {
        "query": "What data sources are available for economic analysis?",
        "max_results": 10,
    },
    "evaluators": [
        AssetCountInRange(min_count=1, max_count=10),
        HasRecommendation(),
    ],
    "metadata": {"category": "discovery", "difficulty": "medium"},
})

# ─────────────────────────────────────────────────────────────
# Exports
# ─────────────────────────────────────────────────────────────

_ECONOMIC = [GDP_SEARCH, UNEMPLOYMENT_SEARCH]
_CORPORATE = [SEC_FINANCIALS, COMPANY_SEGMENTS]
_DISCOVERY = [BROAD_SEARCH]

ECONOMIC_CASES = [c.to_case() for c in _ECONOMIC]
CORPORATE_CASES = [c.to_case() for c in _CORPORATE]
DISCOVERY_CASES = [c.to_case() for c in _DISCOVERY]
ALL_CASES = ECONOMIC_CASES + CORPORATE_CASES + DISCOVERY_CASES
