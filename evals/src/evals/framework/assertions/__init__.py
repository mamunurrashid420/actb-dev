"""Assertion-based evaluation system.

This module provides the core assertion system for evaluating agent outputs.
It includes:

- Assertion: Pydantic model for configuring assertions
- AssertionResult: Result of evaluating an assertion
- EvalContext: Execution context with performance metrics
- AssertionEngine: Engine for evaluating assertions using JSONPath
- EVALUATORS: Registry of assertion evaluator functions

Example:
    from evals.framework.assertions import (
        Assertion,
        AssertionEngine,
        EvalContext,
    )

    engine = AssertionEngine()
    output = {"task": "consult", "assets": [{"path": "gdp"}, {"path": "unemployment"}]}
    assertions = [
        Assertion(type="equals", field="task", value="consult"),
        Assertion(type="any-contains", field="assets[*].path", value="gdp"),
    ]
    ctx = EvalContext(duration_seconds=1.5, total_tokens=500)
    results = engine.evaluate_all(output, assertions, ctx)

    for result in results:
        print(result)  # "PASS: equals [task]" or "FAIL: ..."

Assertion Types (22):
    Presence:
        - not-null: field exists and is not None
        - is-null: field is None or missing

    Equality:
        - equals: exact value match
        - not-equals: value differs
        - one-of: value in allowed set

    String:
        - contains: substring present (case-insensitive)
        - not-contains: substring absent (case-insensitive)
        - regex: matches regular expression
        - matches: alias for regex
        - starts-with: string starts with prefix (case-insensitive)
        - ends-with: string ends with suffix (case-insensitive)

    Collection:
        - any-contains: any element contains value
        - all-contain: all elements contain value
        - count-range: array length in [min, max]
        - includes: array includes exact value
        - count: exact array length (use value for expected count)

    Numeric:
        - in-range: value in [min, max]
        - greater-than: alias for in-range with min=value (>= semantics)
        - less-than: alias for in-range with max=value (<= semantics)
        - between: alias for in-range (same behavior)

    Performance:
        - latency-budget: execution time under threshold
        - token-budget: token count under threshold
"""

from evals.framework.assertions.engine import AssertionEngine
from evals.framework.assertions.evaluators import EVALUATORS
from evals.framework.assertions.types import Assertion, AssertionResult, EvalContext

__all__ = [
    "Assertion",
    "AssertionResult",
    "AssertionEngine",
    "EvalContext",
    "EVALUATORS",
]
