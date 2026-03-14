"""Built-in assertion evaluators.

Implements all assertion types using a decorated functions pattern
for extensibility and testability.

Assertion types:
- Presence: not-null, is-null
- Equality: equals, not-equals, one-of
- String: contains, not-contains, regex, starts-with, ends-with, matches (alias)
- Collection: any-contains, all-contain, count-range, includes, count
- Numeric: in-range, greater-than (alias), less-than (alias), between (alias)
- Performance: latency-budget, token-budget
"""

import re
from collections.abc import Callable
from typing import Any

from evals.framework.assertions.types import Assertion, EvalContext

# Registry of evaluators by assertion type
EVALUATORS: dict[str, Callable[[Any, Assertion, EvalContext], bool]] = {}


def evaluator(type_: str):
    """Decorator to register an evaluator function for an assertion type.

    Example:
        @evaluator("equals")
        def equals(actual, asn, ctx):
            return actual == asn.value
    """

    def register(fn: Callable[[Any, Assertion, EvalContext], bool]):
        EVALUATORS[type_] = fn
        return fn

    return register


# ─────────────────────────────────────────────────────────────────────────────
# Presence Assertions
# ─────────────────────────────────────────────────────────────────────────────


@evaluator("not-null")
def not_null(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Check that field exists and is not None."""
    return actual is not None


@evaluator("is-null")
def is_null(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Check that field is None or missing."""
    return actual is None


# ─────────────────────────────────────────────────────────────────────────────
# Equality Assertions
# ─────────────────────────────────────────────────────────────────────────────


@evaluator("equals")
def equals(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Check that field value equals expected value."""
    return actual == asn.value


@evaluator("not-equals")
def not_equals(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Check that field value differs from expected value."""
    return actual != asn.value


@evaluator("one-of")
def one_of(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Check that field value is in the allowed set."""
    if not isinstance(asn.value, list):
        return actual == asn.value
    return actual in asn.value


# ─────────────────────────────────────────────────────────────────────────────
# String Assertions
# ─────────────────────────────────────────────────────────────────────────────


@evaluator("contains")
def contains(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Check that string field contains substring (case-insensitive)."""
    if actual is None:
        return False
    actual_str = str(actual).lower()
    search_str = str(asn.value).lower()
    return search_str in actual_str


@evaluator("not-contains")
def not_contains(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Check that string field does not contain substring (case-insensitive)."""
    if actual is None:
        return True
    actual_str = str(actual).lower()
    search_str = str(asn.value).lower()
    return search_str not in actual_str


@evaluator("regex")
def regex(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Check that string field matches regular expression."""
    if actual is None:
        return False
    try:
        pattern = re.compile(str(asn.value))
        return pattern.search(str(actual)) is not None
    except re.error:
        return False


@evaluator("matches")
def matches(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Alias for regex: check that string field matches regular expression."""
    return regex(actual, asn, ctx)


@evaluator("starts-with")
def starts_with(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Check that string field starts with prefix (case-insensitive)."""
    if actual is None:
        return False
    return str(actual).lower().startswith(str(asn.value).lower())


@evaluator("ends-with")
def ends_with(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Check that string field ends with suffix (case-insensitive)."""
    if actual is None:
        return False
    return str(actual).lower().endswith(str(asn.value).lower())


# ─────────────────────────────────────────────────────────────────────────────
# Collection Assertions
# ─────────────────────────────────────────────────────────────────────────────


@evaluator("any-contains")
def any_contains(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Check that any array element contains the value (case-insensitive)."""
    if not actual:
        return False
    if not isinstance(actual, list):
        actual = [actual]
    search_str = str(asn.value).lower()
    return any(search_str in str(x).lower() for x in actual)


@evaluator("all-contain")
def all_contain(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Check that all array elements contain the value (case-insensitive)."""
    if not isinstance(actual, list):
        return False
    if len(actual) == 0:
        return True  # Vacuous truth
    search_str = str(asn.value).lower()
    return all(search_str in str(x).lower() for x in actual)


@evaluator("count-range")
def count_range(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Check that array length is within [min, max] range."""
    if not isinstance(actual, list):
        return False
    count = len(actual)
    min_ok = asn.min is None or count >= asn.min
    max_ok = asn.max is None or count <= asn.max
    return min_ok and max_ok


@evaluator("includes")
def includes(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Check that array includes a specific value (exact match)."""
    if not isinstance(actual, list):
        return False
    return asn.value in actual


@evaluator("count")
def count(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Check that array has exact length (use asn.value for expected count)."""
    if not isinstance(actual, list):
        return False
    return len(actual) == asn.value


# ─────────────────────────────────────────────────────────────────────────────
# Numeric Assertions
# ─────────────────────────────────────────────────────────────────────────────


@evaluator("in-range")
def in_range(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Check that numeric value is within [min, max] range."""
    if actual is None:
        return False
    try:
        value = float(actual)
    except (TypeError, ValueError):
        return False
    min_ok = asn.min is None or value >= asn.min
    max_ok = asn.max is None or value <= asn.max
    return min_ok and max_ok


@evaluator("greater-than")
def greater_than(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Alias for in-range: check that value is greater than threshold."""
    return in_range(actual, Assertion(type="in-range", min=asn.value), ctx)


@evaluator("less-than")
def less_than(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Alias for in-range: check that value is less than threshold."""
    return in_range(actual, Assertion(type="in-range", max=asn.value), ctx)


@evaluator("between")
def between(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Alias for in-range: check that value is between min and max."""
    return in_range(actual, asn, ctx)


# ─────────────────────────────────────────────────────────────────────────────
# Performance Assertions
# ─────────────────────────────────────────────────────────────────────────────


@evaluator("latency-budget")
def latency_budget(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Check that execution time is under the budget."""
    if asn.max_seconds is None:
        return True
    return ctx.duration_seconds <= asn.max_seconds


@evaluator("token-budget")
def token_budget(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Check that token count is under the budget."""
    if asn.max_tokens is None:
        return True
    return ctx.total_tokens <= asn.max_tokens
