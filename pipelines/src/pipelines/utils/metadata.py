"""Utilities for constructing Dagster asset metadata."""

from typing import Any

import pandas as pd


def get_date_range_metadata(df: pd.DataFrame) -> dict[str, str | None]:
    """Extract date range metadata from DataFrame."""
    if "date" not in df.columns or len(df) == 0:
        return {"date_range_start": None, "date_range_end": None}
    return {
        "date_range_start": str(df["date"].min()),
        "date_range_end": str(df["date"].max()),
    }


class MetadataBuilder:
    """Fluent builder for Dagster output metadata.

    Example:
        metadata = (MetadataBuilder()
            .with_record_count(df)
            .with_date_range(df)
            .with_series_id('JTS00000000JOL')
            .build())
    """

    def __init__(self):
        self._metadata: dict[str, Any] = {}

    def with_record_count(self, data: pd.DataFrame | list | dict) -> "MetadataBuilder":
        """Add num_records from DataFrame, list, or dict."""
        if isinstance(data, pd.DataFrame | list):
            self._metadata["num_records"] = len(data)
        elif isinstance(data, dict):
            if "summary" in data:
                self._metadata["num_records"] = len(data["summary"])
            else:
                self._metadata["num_records"] = len(data)
        return self

    def with_date_range(
        self, df: pd.DataFrame, date_col: str = "date"
    ) -> "MetadataBuilder":
        """Add date_range_start and date_range_end from DataFrame."""
        if len(df) > 0 and date_col in df.columns:
            min_date = df[date_col].min()
            max_date = df[date_col].max()

            # Handle both datetime and string dates
            self._metadata["date_range_start"] = str(
                min_date.date() if hasattr(min_date, "date") else min_date
            )
            self._metadata["date_range_end"] = str(
                max_date.date() if hasattr(max_date, "date") else max_date
            )
        else:
            self._metadata["date_range_start"] = None
            self._metadata["date_range_end"] = None
        return self

    def with_series_id(self, series_id: str) -> "MetadataBuilder":
        """Add series_id."""
        self._metadata["series_id"] = series_id
        return self

    def with_indicator_code(self, indicator_code: str) -> "MetadataBuilder":
        """Add indicator_code."""
        self._metadata["indicator_code"] = indicator_code
        return self

    def with_country(
        self, country: str, country_code: str | None = None
    ) -> "MetadataBuilder":
        """Add country and optional country_code."""
        self._metadata["country"] = country
        if country_code:
            self._metadata["country_code"] = country_code
        return self

    def with_ticker(self, ticker: str) -> "MetadataBuilder":
        """Add ticker."""
        self._metadata["ticker"] = ticker
        return self

    def with_form_type(self, form_type: str) -> "MetadataBuilder":
        """Add form_type."""
        self._metadata["form_type"] = form_type
        return self

    def with_custom(self, **kwargs) -> "MetadataBuilder":
        """Add custom fields."""
        self._metadata.update(kwargs)
        return self

    def build(self) -> dict[str, Any]:
        """Return metadata dict."""
        return self._metadata


class QuestionGenerator:
    """Generate LLM question templates for assets."""

    @staticmethod
    def for_indicator(indicator: str, entity: str) -> list[str]:
        """Generate questions for economic indicator."""
        indicator_lower = indicator.lower()
        return [
            f"What is {entity}'s {indicator_lower}?",
            f"Show me {indicator_lower} for {entity}",
            f"{entity} {indicator_lower}",
            f"How is {entity}'s {indicator_lower} trending?",
        ]

    @staticmethod
    def for_sec_filing(ticker: str, filing_type: str, context: str) -> list[str]:
        """Generate questions for SEC filings."""
        return [
            f"What are {ticker}'s {context}?",
            f"Show me {ticker} {filing_type} filing",
            f"{ticker} {context}",
        ]

    @staticmethod
    def for_comparison(metric: str, entities: str = "countries") -> list[str]:
        """Generate questions for cross-entity comparisons."""
        metric_lower = metric.lower()
        return [
            f"Compare {metric_lower} across {entities}",
            f"Which {entities} have the highest {metric_lower}?",
            f"{metric} comparison",
            f"{metric} by {entities.rstrip('s')}",
        ]
