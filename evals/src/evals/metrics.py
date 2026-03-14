"""Evaluation metrics and helper functions."""

from dataclasses import dataclass


def success_rate(report) -> float:
    """Calculate success rate from an EvaluationReport.

    Args:
        report: EvaluationReport from pydantic_evals

    Returns:
        Float between 0.0 and 1.0 representing success rate
    """
    total = len(report.cases)
    failed = len(report.failures)
    return (total - failed) / total if total > 0 else 0.0


@dataclass
class ClassificationMetrics:
    """Container for classification metrics per dimension."""

    dimension: str
    report: dict  # sklearn classification_report output_dict
    y_true: list[str]
    y_pred: list[str]

    def macro_f1(self) -> float:
        """Get macro-averaged F1 score."""
        return self.report.get("macro avg", {}).get("f1-score", 0.0)

    def print_report(self):
        """Print human-readable classification report."""
        from sklearn.metrics import classification_report

        print(f"\n=== {self.dimension.upper()} Classification Report ===")
        print(classification_report(self.y_true, self.y_pred))


def classification_metrics_from_report(
    raw_cases: list, report, dimension: str
) -> ClassificationMetrics:
    """Compute sklearn classification metrics from pydantic-evals report.

    Args:
        raw_cases: List of raw test case objects with expected_output
        report: EvaluationReport from pydantic_evals
        dimension: Attribute name to compare ('task', 'mode', 'job')

    Returns:
        ClassificationMetrics with sklearn report and raw data

    Raises:
        ValueError: If no successful cases to evaluate
    """
    from sklearn.metrics import classification_report

    # Build lookup from case name to expected output
    expected_by_name = {
        c.name: getattr(c.expected_output, dimension) for c in raw_cases
    }

    # Extract predictions only for cases with successful output
    y_true = []
    y_pred = []
    for case_result in report.cases:
        if case_result.output is not None:
            case_name = case_result.name
            if case_name in expected_by_name:
                y_true.append(expected_by_name[case_name])
                y_pred.append(getattr(case_result.output, dimension))

    if not y_true:
        raise ValueError(
            f"No successful cases to evaluate for dimension '{dimension}'. "
            f"Total cases: {len(report.cases)}, Failures: {len(report.failures)}"
        )

    sklearn_report = classification_report(
        y_true, y_pred, output_dict=True, zero_division=0
    )

    return ClassificationMetrics(
        dimension=dimension,
        report=sklearn_report,
        y_true=y_true,
        y_pred=y_pred,
    )
