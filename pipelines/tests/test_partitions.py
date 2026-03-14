"""Tests for partition key parsers."""

from pipelines.partitions import parse_fiscal_year, parse_month, parse_quarter


class TestParseFiscalYear:
    """Tests for parse_fiscal_year function."""

    def test_parse_fiscal_year_2023(self):
        """Parse FY2023 → 2023."""
        assert parse_fiscal_year("FY2023") == 2023

    def test_parse_fiscal_year_2024(self):
        """Parse FY2024 → 2024."""
        assert parse_fiscal_year("FY2024") == 2024

    def test_parse_fiscal_year_2020(self):
        """Parse FY2020 → 2020."""
        assert parse_fiscal_year("FY2020") == 2020


class TestParseQuarter:
    """Tests for parse_quarter function."""

    def test_parse_quarter_q1(self):
        """Parse 2024-Q1 → (2024, 1)."""
        year, quarter = parse_quarter("2024-Q1")
        assert year == 2024
        assert quarter == 1

    def test_parse_quarter_q2(self):
        """Parse 2024-Q2 → (2024, 2)."""
        year, quarter = parse_quarter("2024-Q2")
        assert year == 2024
        assert quarter == 2

    def test_parse_quarter_q3(self):
        """Parse 2023-Q3 → (2023, 3)."""
        year, quarter = parse_quarter("2023-Q3")
        assert year == 2023
        assert quarter == 3

    def test_parse_quarter_q4(self):
        """Parse 2023-Q4 → (2023, 4)."""
        year, quarter = parse_quarter("2023-Q4")
        assert year == 2023
        assert quarter == 4


class TestParseMonth:
    """Tests for parse_month function."""

    def test_parse_month_january(self):
        """Parse 2024-01 → (2024, 1)."""
        year, month = parse_month("2024-01")
        assert year == 2024
        assert month == 1

    def test_parse_month_may(self):
        """Parse 2024-05 → (2024, 5)."""
        year, month = parse_month("2024-05")
        assert year == 2024
        assert month == 5

    def test_parse_month_december(self):
        """Parse 2023-12 → (2023, 12)."""
        year, month = parse_month("2023-12")
        assert year == 2023
        assert month == 12

    def test_parse_month_different_year(self):
        """Parse 2020-06 → (2020, 6)."""
        year, month = parse_month("2020-06")
        assert year == 2020
        assert month == 6
