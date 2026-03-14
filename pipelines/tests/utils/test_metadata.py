"""Tests for metadata utilities."""

import pandas as pd

from pipelines.utils.metadata import MetadataBuilder, QuestionGenerator


class TestMetadataBuilder:
    """Tests for MetadataBuilder class."""

    def test_with_record_count_dataframe(self):
        """Test record count from DataFrame."""
        df = pd.DataFrame({"a": [1, 2, 3]})
        metadata = MetadataBuilder().with_record_count(df).build()
        assert metadata["num_records"] == 3

    def test_with_record_count_list(self):
        """Test record count from list."""
        data = [1, 2, 3, 4]
        metadata = MetadataBuilder().with_record_count(data).build()
        assert metadata["num_records"] == 4

    def test_with_record_count_dict(self):
        """Test record count from dict with summary."""
        data = {"summary": [1, 2, 3]}
        metadata = MetadataBuilder().with_record_count(data).build()
        assert metadata["num_records"] == 3

    def test_with_date_range_datetime(self):
        """Test date range extraction with datetime."""
        df = pd.DataFrame({"date": pd.to_datetime(["2023-01-01", "2023-12-31"])})
        metadata = MetadataBuilder().with_date_range(df).build()
        assert metadata["date_range_start"] == "2023-01-01"
        assert metadata["date_range_end"] == "2023-12-31"

    def test_with_date_range_empty(self):
        """Test date range with empty DataFrame."""
        df = pd.DataFrame({"date": []})
        metadata = MetadataBuilder().with_date_range(df).build()
        assert metadata["date_range_start"] is None
        assert metadata["date_range_end"] is None

    def test_with_series_id(self):
        """Test adding series ID."""
        metadata = MetadataBuilder().with_series_id("TEST123").build()
        assert metadata["series_id"] == "TEST123"

    def test_with_indicator_code(self):
        """Test adding indicator code."""
        metadata = MetadataBuilder().with_indicator_code("GDP").build()
        assert metadata["indicator_code"] == "GDP"

    def test_with_country(self):
        """Test adding country metadata."""
        metadata = MetadataBuilder().with_country("United States", "US").build()
        assert metadata["country"] == "United States"
        assert metadata["country_code"] == "US"

    def test_with_ticker(self):
        """Test adding ticker."""
        metadata = MetadataBuilder().with_ticker("AAPL").build()
        assert metadata["ticker"] == "AAPL"

    def test_with_form_type(self):
        """Test adding form type."""
        metadata = MetadataBuilder().with_form_type("10-K").build()
        assert metadata["form_type"] == "10-K"

    def test_with_custom(self):
        """Test adding custom fields."""
        metadata = MetadataBuilder().with_custom(foo="bar", baz=123).build()
        assert metadata["foo"] == "bar"
        assert metadata["baz"] == 123

    def test_chaining(self):
        """Test method chaining."""
        df = pd.DataFrame({"date": pd.to_datetime(["2023-01-01"]), "value": [100]})
        metadata = (
            MetadataBuilder()
            .with_record_count(df)
            .with_date_range(df)
            .with_ticker("AAPL")
            .with_custom(test=True)
            .build()
        )

        assert metadata["num_records"] == 1
        assert metadata["date_range_start"] == "2023-01-01"
        assert metadata["ticker"] == "AAPL"
        assert metadata["test"] is True


class TestQuestionGenerator:
    """Tests for QuestionGenerator class."""

    def test_for_indicator(self):
        """Test indicator question generation."""
        questions = QuestionGenerator.for_indicator("GDP", "United States")
        assert len(questions) == 4
        assert "What is United States's gdp?" in questions
        assert "Show me gdp for United States" in questions

    def test_for_sec_filing(self):
        """Test SEC filing question generation."""
        questions = QuestionGenerator.for_sec_filing(
            "AAPL", "10-K", "annual financials"
        )
        assert len(questions) == 3
        assert "What are AAPL's annual financials?" in questions
        assert "Show me AAPL 10-K filing" in questions

    def test_for_comparison(self):
        """Test comparison question generation."""
        questions = QuestionGenerator.for_comparison("GDP", "countries")
        assert len(questions) == 4
        assert "Compare gdp across countries" in questions
        assert "Which countries have the highest gdp?" in questions
