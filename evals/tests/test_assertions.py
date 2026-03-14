"""Tests for the assertion-based evaluation system.

TDD tests for Phase 1 of the evaluation framework evolution.
Tests all 15 assertion types defined in the plan.
"""

import pytest

from evals.framework.assertions.engine import AssertionEngine
from evals.framework.assertions.evaluators import EVALUATORS
from evals.framework.assertions.types import Assertion, AssertionResult, EvalContext

# ─────────────────────────────────────────────────────────────────────────────
# Test Fixtures and Helpers
# ─────────────────────────────────────────────────────────────────────────────


def make_assertion(**kwargs) -> Assertion:
    """Helper to create Assertion instances."""
    return Assertion(**kwargs)


def make_context(**kwargs) -> EvalContext:
    """Helper to create EvalContext instances."""
    return EvalContext(**kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Assertion Model Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAssertionModel:
    """Tests for the Assertion Pydantic model."""

    def test_minimal_assertion(self):
        """Should create assertion with just type."""
        asn = Assertion(type="not-null", field="name")
        assert asn.type == "not-null"
        assert asn.field == "name"

    def test_assertion_with_value(self):
        """Should create assertion with value."""
        asn = Assertion(type="equals", field="status", value="active")
        assert asn.value == "active"

    def test_assertion_with_range(self):
        """Should create assertion with min/max."""
        asn = Assertion(type="in-range", field="score", min=0, max=100)
        assert asn.min == 0
        assert asn.max == 100

    def test_assertion_with_threshold(self):
        """Should create assertion with max_seconds."""
        asn = Assertion(type="latency-budget", max_seconds=2.5)
        assert asn.max_seconds == 2.5

    def test_assertion_with_token_limit(self):
        """Should create assertion with max_tokens."""
        asn = Assertion(type="token-budget", max_tokens=1000)
        assert asn.max_tokens == 1000


class TestAssertionResult:
    """Tests for the AssertionResult dataclass."""

    def test_passed_result(self):
        """Should create passed result."""
        result = AssertionResult(
            assertion=Assertion(type="not-null", field="name"),
            passed=True,
            actual_value="John",
        )
        assert result.passed is True
        assert result.actual_value == "John"

    def test_failed_result_with_message(self):
        """Should create failed result with message."""
        result = AssertionResult(
            assertion=Assertion(type="equals", field="status", value="active"),
            passed=False,
            actual_value="inactive",
            message="Expected 'active', got 'inactive'",
        )
        assert result.passed is False
        assert "Expected" in result.message


# ─────────────────────────────────────────────────────────────────────────────
# AssertionEngine Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAssertionEngine:
    """Tests for the AssertionEngine class."""

    def test_evaluate_single_assertion(self):
        """Should evaluate a single assertion."""
        engine = AssertionEngine()
        output = {"name": "John", "age": 30}
        asn = Assertion(type="not-null", field="name")
        ctx = make_context()

        result = engine.evaluate(output, asn, ctx)
        assert result.passed is True

    def test_evaluate_multiple_assertions(self):
        """Should evaluate multiple assertions."""
        engine = AssertionEngine()
        output = {"name": "John", "status": "active"}
        assertions = [
            Assertion(type="not-null", field="name"),
            Assertion(type="equals", field="status", value="active"),
        ]
        ctx = make_context()

        results = engine.evaluate_all(output, assertions, ctx)
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_extract_simple_field(self):
        """Should extract simple field with JSONPath."""
        engine = AssertionEngine()
        output = {"name": "John", "age": 30}

        value = engine.extract_field(output, "name")
        assert value == "John"

    def test_extract_nested_field(self):
        """Should extract nested field with JSONPath."""
        engine = AssertionEngine()
        output = {"user": {"name": "John", "profile": {"city": "NYC"}}}

        value = engine.extract_field(output, "user.profile.city")
        assert value == "NYC"

    def test_extract_array_element(self):
        """Should extract array element with JSONPath."""
        engine = AssertionEngine()
        output = {"items": ["a", "b", "c"]}

        value = engine.extract_field(output, "items[0]")
        assert value == "a"

    def test_extract_all_array_elements(self):
        """Should extract all array elements with wildcard."""
        engine = AssertionEngine()
        output = {"assets": [{"path": "a"}, {"path": "b"}, {"path": "c"}]}

        values = engine.extract_field(output, "assets[*].path")
        assert values == ["a", "b", "c"]

    def test_extract_missing_field_returns_none(self):
        """Should return None for missing field."""
        engine = AssertionEngine()
        output = {"name": "John"}

        value = engine.extract_field(output, "missing")
        assert value is None

    def test_unknown_assertion_type_raises(self):
        """Should raise error for unknown assertion type."""
        engine = AssertionEngine()
        output = {"name": "John"}
        asn = Assertion(type="unknown-type", field="name")
        ctx = make_context()

        with pytest.raises(ValueError, match="Unknown assertion type"):
            engine.evaluate(output, asn, ctx)


# ─────────────────────────────────────────────────────────────────────────────
# Presence Assertions
# ─────────────────────────────────────────────────────────────────────────────


class TestNotNullAssertion:
    """Tests for not-null assertion type."""

    def test_passes_when_field_exists(self):
        """Should pass when field exists and is not None."""
        engine = AssertionEngine()
        output = {"name": "John"}
        asn = Assertion(type="not-null", field="name")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_when_field_is_none(self):
        """Should fail when field is None."""
        engine = AssertionEngine()
        output = {"name": None}
        asn = Assertion(type="not-null", field="name")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_fails_when_field_missing(self):
        """Should fail when field is missing."""
        engine = AssertionEngine()
        output = {"other": "value"}
        asn = Assertion(type="not-null", field="name")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_passes_with_empty_string(self):
        """Should pass when field is empty string (not None)."""
        engine = AssertionEngine()
        output = {"name": ""}
        asn = Assertion(type="not-null", field="name")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_passes_with_zero(self):
        """Should pass when field is 0 (not None)."""
        engine = AssertionEngine()
        output = {"count": 0}
        asn = Assertion(type="not-null", field="count")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True


class TestIsNullAssertion:
    """Tests for is-null assertion type."""

    def test_passes_when_field_is_none(self):
        """Should pass when field is None."""
        engine = AssertionEngine()
        output = {"name": None}
        asn = Assertion(type="is-null", field="name")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_when_field_has_value(self):
        """Should fail when field has value."""
        engine = AssertionEngine()
        output = {"name": "John"}
        asn = Assertion(type="is-null", field="name")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_passes_when_field_missing(self):
        """Should pass when field is missing (treated as None)."""
        engine = AssertionEngine()
        output = {"other": "value"}
        asn = Assertion(type="is-null", field="name")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True


# ─────────────────────────────────────────────────────────────────────────────
# Equality Assertions
# ─────────────────────────────────────────────────────────────────────────────


class TestEqualsAssertion:
    """Tests for equals assertion type."""

    def test_passes_when_values_equal(self):
        """Should pass when values are equal."""
        engine = AssertionEngine()
        output = {"status": "active"}
        asn = Assertion(type="equals", field="status", value="active")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_when_values_differ(self):
        """Should fail when values differ."""
        engine = AssertionEngine()
        output = {"status": "inactive"}
        asn = Assertion(type="equals", field="status", value="active")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_numeric_equality(self):
        """Should handle numeric equality."""
        engine = AssertionEngine()
        output = {"count": 42}
        asn = Assertion(type="equals", field="count", value=42)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_boolean_equality(self):
        """Should handle boolean equality."""
        engine = AssertionEngine()
        output = {"enabled": True}
        asn = Assertion(type="equals", field="enabled", value=True)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_list_equality(self):
        """Should handle list equality."""
        engine = AssertionEngine()
        output = {"tags": ["a", "b", "c"]}
        asn = Assertion(type="equals", field="tags", value=["a", "b", "c"])

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_dict_equality(self):
        """Should handle dict equality."""
        engine = AssertionEngine()
        output = {"config": {"key": "value"}}
        asn = Assertion(type="equals", field="config", value={"key": "value"})

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True


class TestNotEqualsAssertion:
    """Tests for not-equals assertion type."""

    def test_passes_when_values_differ(self):
        """Should pass when values differ."""
        engine = AssertionEngine()
        output = {"status": "active"}
        asn = Assertion(type="not-equals", field="status", value="inactive")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_when_values_equal(self):
        """Should fail when values are equal."""
        engine = AssertionEngine()
        output = {"status": "active"}
        asn = Assertion(type="not-equals", field="status", value="active")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False


class TestOneOfAssertion:
    """Tests for one-of assertion type."""

    def test_passes_when_value_in_set(self):
        """Should pass when value is in allowed set."""
        engine = AssertionEngine()
        output = {"status": "active"}
        asn = Assertion(
            type="one-of", field="status", value=["active", "pending", "done"]
        )

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_when_value_not_in_set(self):
        """Should fail when value is not in allowed set."""
        engine = AssertionEngine()
        output = {"status": "unknown"}
        asn = Assertion(
            type="one-of", field="status", value=["active", "pending", "done"]
        )

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_works_with_numeric_values(self):
        """Should work with numeric values."""
        engine = AssertionEngine()
        output = {"priority": 2}
        asn = Assertion(type="one-of", field="priority", value=[1, 2, 3])

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True


# ─────────────────────────────────────────────────────────────────────────────
# String Assertions
# ─────────────────────────────────────────────────────────────────────────────


class TestContainsAssertion:
    """Tests for contains assertion type."""

    def test_passes_when_substring_present(self):
        """Should pass when substring is present."""
        engine = AssertionEngine()
        output = {"message": "Hello, World!"}
        asn = Assertion(type="contains", field="message", value="World")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_when_substring_missing(self):
        """Should fail when substring is missing."""
        engine = AssertionEngine()
        output = {"message": "Hello, World!"}
        asn = Assertion(type="contains", field="message", value="Goodbye")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_case_insensitive(self):
        """Should be case insensitive."""
        engine = AssertionEngine()
        output = {"message": "Hello, World!"}
        asn = Assertion(type="contains", field="message", value="WORLD")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_on_non_string(self):
        """Should fail when field is not a string."""
        engine = AssertionEngine()
        output = {"count": 42}
        asn = Assertion(type="contains", field="count", value="4")

        result = engine.evaluate(output, asn, make_context())
        # Should convert to string and check
        assert result.passed is True


class TestNotContainsAssertion:
    """Tests for not-contains assertion type."""

    def test_passes_when_substring_missing(self):
        """Should pass when substring is missing."""
        engine = AssertionEngine()
        output = {"message": "Hello, World!"}
        asn = Assertion(type="not-contains", field="message", value="Goodbye")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_when_substring_present(self):
        """Should fail when substring is present."""
        engine = AssertionEngine()
        output = {"message": "Hello, World!"}
        asn = Assertion(type="not-contains", field="message", value="World")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_case_insensitive(self):
        """Should be case insensitive."""
        engine = AssertionEngine()
        output = {"message": "Hello, World!"}
        asn = Assertion(type="not-contains", field="message", value="WORLD")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False


class TestRegexAssertion:
    """Tests for regex assertion type."""

    def test_passes_when_pattern_matches(self):
        """Should pass when pattern matches."""
        engine = AssertionEngine()
        output = {"email": "user@example.com"}
        asn = Assertion(type="regex", field="email", value=r"^\w+@\w+\.\w+$")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_when_pattern_not_matched(self):
        """Should fail when pattern does not match."""
        engine = AssertionEngine()
        output = {"email": "invalid-email"}
        asn = Assertion(type="regex", field="email", value=r"^\w+@\w+\.\w+$")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_partial_match(self):
        """Should find partial matches (use ^ and $ for full match)."""
        engine = AssertionEngine()
        output = {"text": "The quick brown fox"}
        asn = Assertion(type="regex", field="text", value=r"quick")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_handles_special_characters(self):
        """Should handle special regex characters."""
        engine = AssertionEngine()
        output = {"version": "1.2.3"}
        asn = Assertion(type="regex", field="version", value=r"\d+\.\d+\.\d+")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True


class TestMatchesAssertion:
    """Tests for matches assertion type (alias for regex)."""

    def test_passes_when_pattern_matches(self):
        """Should pass when pattern matches (delegates to regex)."""
        engine = AssertionEngine()
        output = {"email": "user@example.com"}
        asn = Assertion(type="matches", field="email", value=r"^\w+@\w+\.\w+$")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_when_pattern_not_matched(self):
        """Should fail when pattern does not match."""
        engine = AssertionEngine()
        output = {"email": "invalid-email"}
        asn = Assertion(type="matches", field="email", value=r"^\w+@\w+\.\w+$")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_partial_match(self):
        """Should find partial matches."""
        engine = AssertionEngine()
        output = {"text": "Hello World"}
        asn = Assertion(type="matches", field="text", value=r"World")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True


class TestStartsWithAssertion:
    """Tests for starts-with assertion type."""

    def test_passes_when_string_starts_with_prefix(self):
        """Should pass when string starts with prefix."""
        engine = AssertionEngine()
        output = {"path": "/api/users"}
        asn = Assertion(type="starts-with", field="path", value="/api")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_when_string_does_not_start_with_prefix(self):
        """Should fail when string does not start with prefix."""
        engine = AssertionEngine()
        output = {"path": "/web/users"}
        asn = Assertion(type="starts-with", field="path", value="/api")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_case_insensitive(self):
        """Should be case insensitive."""
        engine = AssertionEngine()
        output = {"greeting": "Hello World"}
        asn = Assertion(type="starts-with", field="greeting", value="HELLO")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_on_none(self):
        """Should fail when field is None."""
        engine = AssertionEngine()
        output = {"path": None}
        asn = Assertion(type="starts-with", field="path", value="/api")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_converts_to_string(self):
        """Should convert non-string values to string."""
        engine = AssertionEngine()
        output = {"code": 12345}
        asn = Assertion(type="starts-with", field="code", value="123")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True


class TestEndsWithAssertion:
    """Tests for ends-with assertion type."""

    def test_passes_when_string_ends_with_suffix(self):
        """Should pass when string ends with suffix."""
        engine = AssertionEngine()
        output = {"filename": "report.pdf"}
        asn = Assertion(type="ends-with", field="filename", value=".pdf")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_when_string_does_not_end_with_suffix(self):
        """Should fail when string does not end with suffix."""
        engine = AssertionEngine()
        output = {"filename": "report.doc"}
        asn = Assertion(type="ends-with", field="filename", value=".pdf")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_case_insensitive(self):
        """Should be case insensitive."""
        engine = AssertionEngine()
        output = {"filename": "Report.PDF"}
        asn = Assertion(type="ends-with", field="filename", value=".pdf")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_on_none(self):
        """Should fail when field is None."""
        engine = AssertionEngine()
        output = {"filename": None}
        asn = Assertion(type="ends-with", field="filename", value=".pdf")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_converts_to_string(self):
        """Should convert non-string values to string."""
        engine = AssertionEngine()
        output = {"code": 12345}
        asn = Assertion(type="ends-with", field="code", value="45")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True


# ─────────────────────────────────────────────────────────────────────────────
# Collection Assertions
# ─────────────────────────────────────────────────────────────────────────────


class TestAnyContainsAssertion:
    """Tests for any-contains assertion type."""

    def test_passes_when_any_element_contains(self):
        """Should pass when any array element contains value."""
        engine = AssertionEngine()
        output = {"tags": ["python", "javascript", "rust"]}
        asn = Assertion(type="any-contains", field="tags", value="java")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True  # "javascript" contains "java"

    def test_fails_when_no_element_contains(self):
        """Should fail when no array element contains value."""
        engine = AssertionEngine()
        output = {"tags": ["python", "rust", "go"]}
        asn = Assertion(type="any-contains", field="tags", value="java")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_case_insensitive(self):
        """Should be case insensitive."""
        engine = AssertionEngine()
        output = {"tags": ["Python", "Rust"]}
        asn = Assertion(type="any-contains", field="tags", value="PYTHON")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_on_empty_array(self):
        """Should fail on empty array."""
        engine = AssertionEngine()
        output = {"tags": []}
        asn = Assertion(type="any-contains", field="tags", value="python")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_with_nested_paths(self):
        """Should work with JSONPath extracting array."""
        engine = AssertionEngine()
        output = {"assets": [{"path": "fred/gdp"}, {"path": "bls/unemployment"}]}
        asn = Assertion(type="any-contains", field="assets[*].path", value="gdp")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True


class TestAllContainAssertion:
    """Tests for all-contain assertion type."""

    def test_passes_when_all_elements_contain(self):
        """Should pass when all array elements contain value."""
        engine = AssertionEngine()
        output = {"paths": ["/api/users", "/api/posts", "/api/comments"]}
        asn = Assertion(type="all-contain", field="paths", value="/api/")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_when_some_elements_missing(self):
        """Should fail when some elements don't contain value."""
        engine = AssertionEngine()
        output = {"paths": ["/api/users", "/web/posts", "/api/comments"]}
        asn = Assertion(type="all-contain", field="paths", value="/api/")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_passes_on_empty_array(self):
        """Should pass on empty array (vacuous truth)."""
        engine = AssertionEngine()
        output = {"paths": []}
        asn = Assertion(type="all-contain", field="paths", value="/api/")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_case_insensitive(self):
        """Should be case insensitive."""
        engine = AssertionEngine()
        output = {"tags": ["API", "api", "Api"]}
        asn = Assertion(type="all-contain", field="tags", value="api")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True


class TestCountRangeAssertion:
    """Tests for count-range assertion type."""

    def test_passes_when_count_in_range(self):
        """Should pass when array length is in range."""
        engine = AssertionEngine()
        output = {"items": ["a", "b", "c"]}
        asn = Assertion(type="count-range", field="items", min=2, max=5)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_when_count_below_min(self):
        """Should fail when array length is below min."""
        engine = AssertionEngine()
        output = {"items": ["a"]}
        asn = Assertion(type="count-range", field="items", min=2, max=5)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_fails_when_count_above_max(self):
        """Should fail when array length is above max."""
        engine = AssertionEngine()
        output = {"items": ["a", "b", "c", "d", "e", "f"]}
        asn = Assertion(type="count-range", field="items", min=2, max=5)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_exact_count(self):
        """Should pass when count equals min and max (exact count)."""
        engine = AssertionEngine()
        output = {"items": ["a", "b", "c"]}
        asn = Assertion(type="count-range", field="items", min=3, max=3)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_min_only(self):
        """Should work with only min specified."""
        engine = AssertionEngine()
        output = {"items": ["a", "b", "c", "d", "e"]}
        asn = Assertion(type="count-range", field="items", min=2)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_max_only(self):
        """Should work with only max specified."""
        engine = AssertionEngine()
        output = {"items": ["a", "b"]}
        asn = Assertion(type="count-range", field="items", max=5)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True


class TestIncludesAssertion:
    """Tests for includes assertion type."""

    def test_passes_when_array_includes_value(self):
        """Should pass when array includes specific value."""
        engine = AssertionEngine()
        output = {"tags": ["python", "javascript", "rust"]}
        asn = Assertion(type="includes", field="tags", value="python")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_when_array_missing_value(self):
        """Should fail when array does not include value."""
        engine = AssertionEngine()
        output = {"tags": ["python", "javascript", "rust"]}
        asn = Assertion(type="includes", field="tags", value="java")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_works_with_numeric_values(self):
        """Should work with numeric values."""
        engine = AssertionEngine()
        output = {"ids": [1, 2, 3, 4, 5]}
        asn = Assertion(type="includes", field="ids", value=3)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_exact_match_required(self):
        """Should require exact match (not substring)."""
        engine = AssertionEngine()
        output = {"tags": ["javascript"]}
        asn = Assertion(type="includes", field="tags", value="java")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False  # "java" != "javascript"


class TestCountAssertion:
    """Tests for count assertion type."""

    def test_passes_when_count_matches(self):
        """Should pass when array length equals expected count."""
        engine = AssertionEngine()
        output = {"items": ["a", "b", "c"]}
        asn = Assertion(type="count", field="items", value=3)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_when_count_differs(self):
        """Should fail when array length differs from expected count."""
        engine = AssertionEngine()
        output = {"items": ["a", "b"]}
        asn = Assertion(type="count", field="items", value=3)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_zero_count(self):
        """Should pass when checking for zero items."""
        engine = AssertionEngine()
        output = {"items": []}
        asn = Assertion(type="count", field="items", value=0)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_on_non_list(self):
        """Should fail when field is not a list."""
        engine = AssertionEngine()
        output = {"items": "not-a-list"}
        asn = Assertion(type="count", field="items", value=3)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_with_nested_paths(self):
        """Should work with JSONPath extracting array."""
        engine = AssertionEngine()
        output = {"data": {"items": [1, 2, 3, 4, 5]}}
        asn = Assertion(type="count", field="data.items", value=5)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True


# ─────────────────────────────────────────────────────────────────────────────
# Numeric Assertions
# ─────────────────────────────────────────────────────────────────────────────


class TestInRangeAssertion:
    """Tests for in-range assertion type."""

    def test_passes_when_value_in_range(self):
        """Should pass when value is in range."""
        engine = AssertionEngine()
        output = {"score": 75}
        asn = Assertion(type="in-range", field="score", min=0, max=100)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_passes_at_boundaries(self):
        """Should pass when value equals min or max."""
        engine = AssertionEngine()
        output = {"score": 0}
        asn = Assertion(type="in-range", field="score", min=0, max=100)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

        output = {"score": 100}
        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_when_below_min(self):
        """Should fail when value is below min."""
        engine = AssertionEngine()
        output = {"score": -5}
        asn = Assertion(type="in-range", field="score", min=0, max=100)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_fails_when_above_max(self):
        """Should fail when value is above max."""
        engine = AssertionEngine()
        output = {"score": 105}
        asn = Assertion(type="in-range", field="score", min=0, max=100)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_works_with_floats(self):
        """Should work with float values."""
        engine = AssertionEngine()
        output = {"ratio": 0.75}
        asn = Assertion(type="in-range", field="ratio", min=0.0, max=1.0)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_min_only(self):
        """Should work with only min specified."""
        engine = AssertionEngine()
        output = {"score": 50}
        asn = Assertion(type="in-range", field="score", min=0)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_max_only(self):
        """Should work with only max specified."""
        engine = AssertionEngine()
        output = {"score": 50}
        asn = Assertion(type="in-range", field="score", max=100)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True


class TestGreaterThanAssertion:
    """Tests for greater-than assertion type (alias for in-range with min)."""

    def test_passes_when_value_greater(self):
        """Should pass when value is greater than threshold."""
        engine = AssertionEngine()
        output = {"score": 75}
        asn = Assertion(type="greater-than", field="score", value=50)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_passes_when_value_equals(self):
        """Should pass when value equals threshold (>= semantics)."""
        engine = AssertionEngine()
        output = {"score": 50}
        asn = Assertion(type="greater-than", field="score", value=50)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_when_value_less(self):
        """Should fail when value is less than threshold."""
        engine = AssertionEngine()
        output = {"score": 25}
        asn = Assertion(type="greater-than", field="score", value=50)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_works_with_floats(self):
        """Should work with float values."""
        engine = AssertionEngine()
        output = {"ratio": 0.75}
        asn = Assertion(type="greater-than", field="ratio", value=0.5)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True


class TestLessThanAssertion:
    """Tests for less-than assertion type (alias for in-range with max)."""

    def test_passes_when_value_less(self):
        """Should pass when value is less than threshold."""
        engine = AssertionEngine()
        output = {"score": 25}
        asn = Assertion(type="less-than", field="score", value=50)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_passes_when_value_equals(self):
        """Should pass when value equals threshold (<= semantics)."""
        engine = AssertionEngine()
        output = {"score": 50}
        asn = Assertion(type="less-than", field="score", value=50)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_when_value_greater(self):
        """Should fail when value is greater than threshold."""
        engine = AssertionEngine()
        output = {"score": 75}
        asn = Assertion(type="less-than", field="score", value=50)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_works_with_floats(self):
        """Should work with float values."""
        engine = AssertionEngine()
        output = {"ratio": 0.25}
        asn = Assertion(type="less-than", field="ratio", value=0.5)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True


class TestBetweenAssertion:
    """Tests for between assertion type (alias for in-range)."""

    def test_passes_when_value_in_range(self):
        """Should pass when value is between min and max."""
        engine = AssertionEngine()
        output = {"score": 75}
        asn = Assertion(type="between", field="score", min=0, max=100)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_passes_at_boundaries(self):
        """Should pass when value equals min or max."""
        engine = AssertionEngine()
        output = {"score": 0}
        asn = Assertion(type="between", field="score", min=0, max=100)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

        output = {"score": 100}
        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_fails_when_outside_range(self):
        """Should fail when value is outside range."""
        engine = AssertionEngine()
        output = {"score": -5}
        asn = Assertion(type="between", field="score", min=0, max=100)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_works_with_floats(self):
        """Should work with float values."""
        engine = AssertionEngine()
        output = {"ratio": 0.75}
        asn = Assertion(type="between", field="ratio", min=0.0, max=1.0)

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True


# ─────────────────────────────────────────────────────────────────────────────
# Performance Assertions
# ─────────────────────────────────────────────────────────────────────────────


class TestLatencyBudgetAssertion:
    """Tests for latency-budget assertion type."""

    def test_passes_when_under_budget(self):
        """Should pass when execution time is under budget."""
        engine = AssertionEngine()
        output = {}
        asn = Assertion(type="latency-budget", max_seconds=5.0)
        ctx = make_context(duration_seconds=2.5)

        result = engine.evaluate(output, asn, ctx)
        assert result.passed is True

    def test_fails_when_over_budget(self):
        """Should fail when execution time exceeds budget."""
        engine = AssertionEngine()
        output = {}
        asn = Assertion(type="latency-budget", max_seconds=2.0)
        ctx = make_context(duration_seconds=3.5)

        result = engine.evaluate(output, asn, ctx)
        assert result.passed is False

    def test_passes_at_exactly_budget(self):
        """Should pass when execution time equals budget."""
        engine = AssertionEngine()
        output = {}
        asn = Assertion(type="latency-budget", max_seconds=2.0)
        ctx = make_context(duration_seconds=2.0)

        result = engine.evaluate(output, asn, ctx)
        assert result.passed is True

    def test_actual_value_shows_duration(self):
        """Should report actual duration in result."""
        engine = AssertionEngine()
        output = {}
        asn = Assertion(type="latency-budget", max_seconds=5.0)
        ctx = make_context(duration_seconds=2.5)

        result = engine.evaluate(output, asn, ctx)
        assert result.actual_value == 2.5


class TestTokenBudgetAssertion:
    """Tests for token-budget assertion type."""

    def test_passes_when_under_budget(self):
        """Should pass when token count is under budget."""
        engine = AssertionEngine()
        output = {}
        asn = Assertion(type="token-budget", max_tokens=1000)
        ctx = make_context(total_tokens=500)

        result = engine.evaluate(output, asn, ctx)
        assert result.passed is True

    def test_fails_when_over_budget(self):
        """Should fail when token count exceeds budget."""
        engine = AssertionEngine()
        output = {}
        asn = Assertion(type="token-budget", max_tokens=1000)
        ctx = make_context(total_tokens=1500)

        result = engine.evaluate(output, asn, ctx)
        assert result.passed is False

    def test_passes_at_exactly_budget(self):
        """Should pass when token count equals budget."""
        engine = AssertionEngine()
        output = {}
        asn = Assertion(type="token-budget", max_tokens=1000)
        ctx = make_context(total_tokens=1000)

        result = engine.evaluate(output, asn, ctx)
        assert result.passed is True

    def test_uses_total_tokens_from_context(self):
        """Should use total_tokens from context."""
        engine = AssertionEngine()
        output = {}
        asn = Assertion(type="token-budget", max_tokens=1000)
        ctx = make_context(input_tokens=300, output_tokens=400, total_tokens=700)

        result = engine.evaluate(output, asn, ctx)
        assert result.passed is True
        assert result.actual_value == 700


# ─────────────────────────────────────────────────────────────────────────────
# Evaluator Registry Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestEvaluatorRegistry:
    """Tests for the evaluator registry."""

    def test_all_evaluators_registered(self):
        """All evaluators should be registered."""
        expected_types = [
            # Presence
            "not-null",
            "is-null",
            # Equality
            "equals",
            "not-equals",
            "one-of",
            # String
            "contains",
            "not-contains",
            "regex",
            "matches",  # alias for regex
            "starts-with",
            "ends-with",
            # Collection
            "any-contains",
            "all-contain",
            "count-range",
            "includes",
            "count",
            # Numeric
            "in-range",
            "greater-than",  # alias for in-range
            "less-than",  # alias for in-range
            "between",  # alias for in-range
            # Performance
            "latency-budget",
            "token-budget",
        ]
        for type_ in expected_types:
            assert type_ in EVALUATORS, f"Missing evaluator for type: {type_}"

    def test_evaluator_count(self):
        """Should have exactly 25 evaluators registered (22 original + 3 workflow)."""
        assert len(EVALUATORS) == 25


# ─────────────────────────────────────────────────────────────────────────────
# Edge Cases and Error Handling
# ─────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_pydantic_model_output(self):
        """Should handle Pydantic model output (via model_dump)."""
        from pydantic import BaseModel

        class Output(BaseModel):
            task: str
            mode: str

        engine = AssertionEngine()
        output = Output(task="consult", mode="chat")
        asn = Assertion(type="equals", field="task", value="consult")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_nested_pydantic_model(self):
        """Should handle nested Pydantic models."""
        from pydantic import BaseModel

        class Inner(BaseModel):
            value: str

        class Output(BaseModel):
            inner: Inner

        engine = AssertionEngine()
        output = Output(inner=Inner(value="test"))
        asn = Assertion(type="equals", field="inner.value", value="test")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is True

    def test_none_output_handled(self):
        """Should handle None output gracefully."""
        engine = AssertionEngine()
        asn = Assertion(type="not-null", field="name")

        result = engine.evaluate(None, asn, make_context())
        assert result.passed is False

    def test_empty_dict_output(self):
        """Should handle empty dict output."""
        engine = AssertionEngine()
        output = {}
        asn = Assertion(type="not-null", field="name")

        result = engine.evaluate(output, asn, make_context())
        assert result.passed is False

    def test_assertion_without_field_for_performance(self):
        """Performance assertions should work without field."""
        engine = AssertionEngine()
        output = {"any": "data"}
        asn = Assertion(type="latency-budget", max_seconds=5.0)
        ctx = make_context(duration_seconds=2.0)

        result = engine.evaluate(output, asn, ctx)
        assert result.passed is True
