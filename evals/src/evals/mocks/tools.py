"""Deterministic tool mocks for evaluation."""

import hashlib
import json
from typing import Any

from agents.tools.sql_execution import SQLOutput


class DeterministicMock:
    """Returns canned responses based on input hash.

    This allows for reproducible evaluations by returning the same
    response for the same inputs every time.
    """

    def __init__(self, responses: dict[str, Any]):
        self.responses = responses

    def _hash_input(self, **kwargs) -> str:
        return hashlib.md5(json.dumps(kwargs, sort_keys=True).encode()).hexdigest()[:8]

    def __call__(self, **kwargs) -> Any:
        key = self._hash_input(**kwargs)
        if key in self.responses:
            return self.responses[key]
        raise ValueError(f"No mock response for input hash: {key}")


# Pre-computed mock responses for SQL execution
# Add responses as needed during test development
SQL_MOCK_RESPONSES: dict[str, SQLOutput] = {
    # Example: hash of {"query": "SELECT date, revenue FROM sales"}
    # "a1b2c3d4": SQLOutput(columns=["date", "revenue"], rows=[...], row_count=365),
}

sql_execution_mock = DeterministicMock(SQL_MOCK_RESPONSES)
