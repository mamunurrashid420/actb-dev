"""Tests for multiple runs support (SingleRunResult, MultiRunResult)."""

from evals.framework.assertions.types import Assertion, AssertionResult
from evals.framework.experiment import MultiRunResult, SingleRunResult


def make_assertion_result(passed: bool = True) -> AssertionResult:
    """Create a test assertion result."""
    return AssertionResult(
        assertion=Assertion(type="equals", field="test", value="expected"),
        passed=passed,
        actual_value="expected" if passed else "actual",
        message=None if passed else "Values do not match",
    )


def make_single_run(
    run_index: int,
    passed: bool = True,
    duration_seconds: float = 1.0,
    tokens: int | None = None,
) -> SingleRunResult:
    """Create a test SingleRunResult."""
    return SingleRunResult(
        run_index=run_index,
        output={"result": "test_output"},
        assertions=[make_assertion_result(passed)],
        passed=passed,
        duration_seconds=duration_seconds,
        tokens=tokens,
    )


class TestSingleRunResult:
    """Tests for SingleRunResult dataclass."""

    def test_creation_with_required_fields(self):
        """SingleRunResult should be created with required fields."""
        result = SingleRunResult(
            run_index=0,
            output={"key": "value"},
            assertions=[make_assertion_result()],
            passed=True,
            duration_seconds=1.5,
        )

        assert result.run_index == 0
        assert result.output == {"key": "value"}
        assert len(result.assertions) == 1
        assert result.passed is True
        assert result.duration_seconds == 1.5
        assert result.tokens is None

    def test_creation_with_tokens(self):
        """SingleRunResult should accept optional tokens field."""
        result = SingleRunResult(
            run_index=0,
            output="output",
            assertions=[],
            passed=True,
            duration_seconds=1.0,
            tokens=150,
        )

        assert result.tokens == 150

    def test_failed_run_with_assertions(self):
        """SingleRunResult should capture failed assertion details."""
        failed_assertion = make_assertion_result(passed=False)
        result = SingleRunResult(
            run_index=2,
            output={"error": True},
            assertions=[failed_assertion],
            passed=False,
            duration_seconds=0.5,
        )

        assert result.passed is False
        assert result.assertions[0].passed is False
        assert result.assertions[0].message == "Values do not match"


class TestMultiRunResultPassRate:
    """Tests for MultiRunResult pass_rate calculation."""

    def test_pass_rate_zero_of_three(self):
        """Pass rate should be 0.0 when all runs fail."""
        result = MultiRunResult(
            case_name="test_case",
            runs=[
                make_single_run(0, passed=False),
                make_single_run(1, passed=False),
                make_single_run(2, passed=False),
            ],
        )

        assert result.pass_count == 0
        assert result.pass_rate == 0.0

    def test_pass_rate_two_of_three(self):
        """Pass rate should be 2/3 when two of three runs pass."""
        result = MultiRunResult(
            case_name="test_case",
            runs=[
                make_single_run(0, passed=True),
                make_single_run(1, passed=False),
                make_single_run(2, passed=True),
            ],
        )

        assert result.pass_count == 2
        assert abs(result.pass_rate - 2 / 3) < 0.001

    def test_pass_rate_three_of_three(self):
        """Pass rate should be 1.0 when all runs pass."""
        result = MultiRunResult(
            case_name="test_case",
            runs=[
                make_single_run(0, passed=True),
                make_single_run(1, passed=True),
                make_single_run(2, passed=True),
            ],
        )

        assert result.pass_count == 3
        assert result.pass_rate == 1.0

    def test_pass_rate_empty_runs(self):
        """Pass rate should be 0.0 when no runs exist."""
        result = MultiRunResult(case_name="test_case", runs=[])

        assert result.pass_count == 0
        assert result.pass_rate == 0.0


class TestMultiRunResultFailures:
    """Tests for failures property."""

    def test_failures_returns_only_failed_runs(self):
        """Failures should return only runs that failed."""
        result = MultiRunResult(
            case_name="test_case",
            runs=[
                make_single_run(0, passed=True),
                make_single_run(1, passed=False),
                make_single_run(2, passed=True),
                make_single_run(3, passed=False),
            ],
        )

        failures = result.failures
        assert len(failures) == 2
        assert failures[0].run_index == 1
        assert failures[1].run_index == 3
        assert all(not f.passed for f in failures)

    def test_failures_empty_when_all_pass(self):
        """Failures should be empty list when all runs pass."""
        result = MultiRunResult(
            case_name="test_case",
            runs=[
                make_single_run(0, passed=True),
                make_single_run(1, passed=True),
            ],
        )

        assert result.failures == []


class TestMultiRunResultFirstFailure:
    """Tests for first_failure property."""

    def test_first_failure_returns_none_when_all_pass(self):
        """First failure should return None when all runs pass."""
        result = MultiRunResult(
            case_name="test_case",
            runs=[
                make_single_run(0, passed=True),
                make_single_run(1, passed=True),
                make_single_run(2, passed=True),
            ],
        )

        assert result.first_failure is None

    def test_first_failure_returns_first_failed_run(self):
        """First failure should return the first failed run."""
        result = MultiRunResult(
            case_name="test_case",
            runs=[
                make_single_run(0, passed=True),
                make_single_run(1, passed=False),
                make_single_run(2, passed=False),
            ],
        )

        first_failure = result.first_failure
        assert first_failure is not None
        assert first_failure.run_index == 1
        assert first_failure.passed is False


class TestMultiRunResultDurationStats:
    """Tests for avg_duration and stddev_duration calculations."""

    def test_avg_duration_calculation(self):
        """Average duration should be calculated correctly."""
        result = MultiRunResult(
            case_name="test_case",
            runs=[
                make_single_run(0, duration_seconds=1.0),
                make_single_run(1, duration_seconds=2.0),
                make_single_run(2, duration_seconds=3.0),
            ],
        )

        assert result.avg_duration == 2.0

    def test_avg_duration_single_run(self):
        """Average duration should work with single run."""
        result = MultiRunResult(
            case_name="test_case",
            runs=[make_single_run(0, duration_seconds=5.0)],
        )

        assert result.avg_duration == 5.0

    def test_avg_duration_empty_runs(self):
        """Average duration should be 0.0 when no runs exist."""
        result = MultiRunResult(case_name="test_case", runs=[])

        assert result.avg_duration == 0.0

    def test_stddev_duration_calculation(self):
        """Standard deviation should be calculated correctly."""
        result = MultiRunResult(
            case_name="test_case",
            runs=[
                make_single_run(0, duration_seconds=1.0),
                make_single_run(1, duration_seconds=2.0),
                make_single_run(2, duration_seconds=3.0),
            ],
        )

        # stddev of [1, 2, 3] is 1.0
        assert abs(result.stddev_duration - 1.0) < 0.001

    def test_stddev_duration_none_with_single_run(self):
        """Standard deviation should be None with fewer than 2 runs."""
        result = MultiRunResult(
            case_name="test_case",
            runs=[make_single_run(0, duration_seconds=1.0)],
        )

        assert result.stddev_duration is None

    def test_stddev_duration_none_with_empty_runs(self):
        """Standard deviation should be None when no runs exist."""
        result = MultiRunResult(case_name="test_case", runs=[])

        assert result.stddev_duration is None

    def test_stddev_duration_two_runs(self):
        """Standard deviation should work with exactly 2 runs."""
        result = MultiRunResult(
            case_name="test_case",
            runs=[
                make_single_run(0, duration_seconds=1.0),
                make_single_run(1, duration_seconds=3.0),
            ],
        )

        # stddev of [1, 3] with sample formula: sqrt(((1-2)^2 + (3-2)^2) / 1) = sqrt(2)
        import math

        expected_stddev = math.sqrt(2)
        assert abs(result.stddev_duration - expected_stddev) < 0.001


class TestSingleRunDefault:
    """Tests for runs=1 default behavior."""

    def test_single_run_in_multi_run_result(self):
        """MultiRunResult should work correctly with a single run (default case)."""
        result = MultiRunResult(
            case_name="test_case",
            runs=[make_single_run(0, passed=True, duration_seconds=1.5)],
        )

        assert len(result.runs) == 1
        assert result.pass_rate == 1.0
        assert result.pass_count == 1
        assert result.failures == []
        assert result.first_failure is None
        assert result.avg_duration == 1.5
        assert result.stddev_duration is None  # Can't compute stddev with 1 sample

    def test_single_run_failure(self):
        """Single run failure should be tracked correctly."""
        result = MultiRunResult(
            case_name="test_case",
            runs=[make_single_run(0, passed=False, duration_seconds=0.8)],
        )

        assert len(result.runs) == 1
        assert result.pass_rate == 0.0
        assert result.pass_count == 0
        assert len(result.failures) == 1
        assert result.first_failure is not None
        assert result.first_failure.run_index == 0
