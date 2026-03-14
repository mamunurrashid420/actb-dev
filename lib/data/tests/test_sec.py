"""Tests for SEC financial data access module.

These are integration tests that require materialized SEC data.
Run from pipelines: cd pipelines && uv run pytest ../shared/tests/data/test_sec.py
"""

import pandas as pd
import polars as pl
import pytest

from shared.data import sec, themes


def _data_available() -> bool:
    """Check if SEC financials data is available."""
    try:
        sec.financials(ticker="AAPL", fiscal_year=2024, fiscal_period="FY", long=True)
        return True
    except FileNotFoundError:
        return False


# Skip all tests if data not available
pytestmark = pytest.mark.skipif(
    not _data_available(),
    reason="SEC financials data not available (run from pipelines directory)",
)


class TestFinancialsFunction:
    """Tests for data.sec.financials() function."""

    def test_returns_wide_format_by_default(self):
        """financials() returns wide format pandas DataFrame by default."""
        df = sec.financials(ticker="AAPL", theme="profitability", fiscal_year=2024)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        # Wide format has concepts as columns
        assert "NetIncomeLoss" in df.columns or "GrossProfit" in df.columns
        # Should not have 'concept' column in wide format
        assert "concept" not in df.columns

    def test_returns_long_format_when_requested(self):
        """financials(long=True) returns long format."""
        df = sec.financials(
            ticker="AAPL", fiscal_year=2024, fiscal_period="FY", long=True
        )
        assert isinstance(df, pd.DataFrame)
        assert "concept" in df.columns
        assert "value" in df.columns

    def test_returns_lazyframe_when_lazy(self):
        """financials() returns LazyFrame when lazy=True."""
        lf = sec.financials(ticker="AAPL", lazy=True)
        assert isinstance(lf, pl.LazyFrame)

    def test_filters_by_ticker(self):
        """financials() filters by ticker symbol."""
        df = sec.financials(ticker="AAPL", long=True)
        assert (df["ticker"] == "AAPL").all()

    def test_filters_by_multiple_tickers(self):
        """financials() accepts list of tickers."""
        df = sec.financials(ticker=["AAPL", "MSFT"], fiscal_year=2024, long=True)
        tickers = df["ticker"].unique().tolist()
        assert set(tickers) <= {"AAPL", "MSFT"}

    def test_filters_by_theme(self):
        """financials() filters by theme using concept mapping."""
        df = sec.financials(
            ticker="AAPL", theme="profitability", fiscal_year=2024, long=True
        )
        profitability_concepts = themes.get_concepts_for_theme("profitability")
        assert df["concept"].isin(profitability_concepts).all()

    def test_filters_by_multiple_themes(self):
        """financials() accepts list of themes."""
        df = sec.financials(
            ticker="AAPL",
            theme=["profitability", "revenue"],
            fiscal_year=2024,
            long=True,
        )
        all_concepts = set(themes.get_concepts_for_theme("profitability")) | set(
            themes.get_concepts_for_theme("revenue")
        )
        assert df["concept"].isin(all_concepts).all()

    def test_filters_by_concept(self):
        """financials() filters by specific XBRL concept."""
        df = sec.financials(concept="NetIncomeLoss", fiscal_year=2024, long=True)
        assert (df["concept"] == "NetIncomeLoss").all()

    def test_concept_overrides_theme(self):
        """When both concept and theme provided, concept takes precedence."""
        df = sec.financials(
            ticker="AAPL",
            theme="revenue",  # Would include RevenueFromContractWithCustomer...
            concept="NetIncomeLoss",  # Override with profitability concept
            fiscal_year=2024,
            long=True,
        )
        assert (df["concept"] == "NetIncomeLoss").all()

    def test_filters_by_fiscal_year(self):
        """financials() filters by fiscal year."""
        df = sec.financials(ticker="AAPL", fiscal_year=2024, long=True)
        assert (df["fiscal_year"] == 2024).all()

    def test_filters_by_fiscal_period(self):
        """financials() filters by fiscal period."""
        df = sec.financials(ticker="AAPL", fiscal_period="FY", long=True)
        assert (df["fiscal_period"] == "FY").all()

    def test_long_format_has_expected_columns(self):
        """financials(long=True) returns DataFrame with expected schema."""
        df = sec.financials(
            ticker="AAPL", fiscal_year=2024, fiscal_period="FY", long=True
        )
        expected_cols = {
            "ticker",
            "company_name",
            "cik",
            "concept",
            "label",
            "value",
            "unit",
            "fiscal_year",
            "fiscal_period",
            "form_type",
            "end_date",
            "filed_date",
        }
        assert set(df.columns) == expected_cols

    def test_wide_format_has_index_columns(self):
        """Wide format has ticker, company_name, cik, fiscal_year, fiscal_period."""
        df = sec.financials(ticker="AAPL", theme="profitability", fiscal_year=2024)
        for col in ["ticker", "company_name", "cik", "fiscal_year", "fiscal_period"]:
            assert col in df.columns


class TestListTickers:
    """Tests for data.sec.list_tickers() function."""

    def test_returns_list(self):
        """list_tickers() returns a list of strings."""
        tickers = sec.list_tickers()
        assert isinstance(tickers, list)
        assert len(tickers) > 0
        assert all(isinstance(t, str) for t in tickers)

    def test_tickers_are_sorted(self):
        """list_tickers() returns sorted list."""
        tickers = sec.list_tickers()
        assert tickers == sorted(tickers)

    def test_includes_known_tickers(self):
        """list_tickers() includes expected companies."""
        tickers = sec.list_tickers()
        # Major companies should be present
        assert "AAPL" in tickers
        assert "MSFT" in tickers


class TestListConcepts:
    """Tests for data.sec.list_concepts() function."""

    def test_returns_all_concepts_without_theme(self):
        """list_concepts() without theme returns all concepts."""
        concepts = sec.list_concepts()
        assert isinstance(concepts, list)
        assert len(concepts) > 100  # Should have many concepts

    def test_returns_theme_concepts_with_theme(self):
        """list_concepts(theme) returns concepts for that theme."""
        concepts = sec.list_concepts("profitability")
        expected = themes.get_concepts_for_theme("profitability")
        assert set(concepts) == set(expected)

    def test_concepts_are_sorted(self):
        """list_concepts() returns sorted list."""
        concepts = sec.list_concepts("profitability")
        assert concepts == sorted(concepts)


class TestListUnits:
    """Tests for data.sec.list_units() function."""

    def test_returns_list(self):
        """list_units() returns a list of strings."""
        units = sec.list_units()
        assert isinstance(units, list)
        assert len(units) > 0
        assert all(isinstance(u, str) for u in units)

    def test_includes_usd(self):
        """list_units() includes USD."""
        units = sec.list_units()
        assert "USD" in units


# =============================================================================
# SEGMENTS TESTS
# =============================================================================


class TestSegmentsFunction:
    """Tests for data.sec.segments() function."""

    def test_returns_dataframe(self):
        """segments() returns pandas DataFrame."""
        df = sec.segments(ticker="AAPL", segment_type="business", fiscal_year=2024)
        assert isinstance(df, pd.DataFrame)

    def test_returns_lazyframe_when_lazy(self):
        """segments() returns LazyFrame when lazy=True."""
        lf = sec.segments(ticker="AAPL", lazy=True)
        assert isinstance(lf, pl.LazyFrame)

    def test_filters_by_ticker(self):
        """segments() filters by ticker symbol."""
        df = sec.segments(ticker="AAPL")
        assert len(df) > 0
        assert (df["ticker"] == "AAPL").all()

    def test_filters_by_multiple_tickers(self):
        """segments() accepts list of tickers."""
        df = sec.segments(ticker=["AAPL", "MSFT"], fiscal_year=2024)
        tickers = df["ticker"].unique().tolist()
        assert set(tickers) <= {"AAPL", "MSFT"}

    def test_filters_by_segment_type(self):
        """segments() filters by segment type."""
        df = sec.segments(ticker="AAPL", segment_type="business")
        assert len(df) > 0
        assert (df["segment_type"] == "business").all()

    def test_filters_by_segment_name(self):
        """segments() filters by segment name."""
        # First get a valid segment name
        all_segments = sec.list_segments("AAPL", segment_type="geographic")
        if len(all_segments) > 0:
            segment_name = all_segments[0]
            df = sec.segments(ticker="AAPL", segment_name=segment_name)
            assert len(df) > 0
            assert (df["segment_name"] == segment_name).all()

    def test_filters_by_fiscal_year(self):
        """segments() filters by fiscal year."""
        df = sec.segments(ticker="AAPL", fiscal_year=2024)
        assert len(df) > 0
        assert (df["fiscal_year"] == 2024).all()

    def test_filters_by_fiscal_period(self):
        """segments() filters by fiscal period."""
        df = sec.segments(ticker="AAPL", fiscal_period="FY")
        if len(df) > 0:
            assert (df["fiscal_period"] == "FY").all()

    def test_combined_filters(self):
        """segments() supports combined filters."""
        df = sec.segments(
            ticker="AAPL",
            segment_type="geographic",
            fiscal_year=2024,
        )
        if len(df) > 0:
            assert (df["ticker"] == "AAPL").all()
            assert (df["segment_type"] == "geographic").all()
            assert (df["fiscal_year"] == 2024).all()

    def test_has_expected_columns(self):
        """segments() returns DataFrame with expected schema."""
        df = sec.segments(ticker="AAPL", segment_type="business", fiscal_year=2024)
        expected_cols = {
            "ticker",
            "company_name",
            "cik",
            "concept",
            "label",
            "value",
            "unit",
            "fiscal_year",
            "fiscal_period",
            "form_type",
            "segment_type",
            "segment_name",
        }
        # Allow for additional columns but require expected ones
        assert expected_cols <= set(df.columns)


class TestListSegments:
    """Tests for data.sec.list_segments() function."""

    def test_returns_list(self):
        """list_segments() returns a list of strings."""
        segments = sec.list_segments("AAPL")
        assert isinstance(segments, list)
        assert len(segments) > 0
        assert all(isinstance(s, str) for s in segments)

    def test_segments_are_sorted(self):
        """list_segments() returns sorted list."""
        segments = sec.list_segments("AAPL")
        assert segments == sorted(segments)

    def test_filters_by_segment_type(self):
        """list_segments() filters by segment type."""
        all_segments = sec.list_segments("AAPL")
        business_segments = sec.list_segments("AAPL", segment_type="business")
        # Business segments should be subset of all segments
        assert set(business_segments) <= set(all_segments)

    def test_different_companies_have_different_segments(self):
        """Different companies have different segment names."""
        aapl_segments = sec.list_segments("AAPL")
        msft_segments = sec.list_segments("MSFT")
        # Not necessarily completely different, but should exist
        assert len(aapl_segments) > 0
        assert len(msft_segments) > 0


# =============================================================================
# COMPANIES TESTS
# =============================================================================


class TestCompaniesFunction:
    """Tests for data.sec.companies() function."""

    def test_returns_dataframe(self):
        """companies() returns pandas DataFrame."""
        df = sec.companies(ticker="AAPL")
        assert isinstance(df, pd.DataFrame)

    def test_returns_lazyframe_when_lazy(self):
        """companies() returns LazyFrame when lazy=True."""
        lf = sec.companies(ticker="AAPL", lazy=True)
        assert isinstance(lf, pl.LazyFrame)

    def test_filters_by_ticker(self):
        """companies() filters by ticker symbol."""
        df = sec.companies(ticker="AAPL")
        assert len(df) == 1
        assert df.iloc[0]["ticker"] == "AAPL"

    def test_filters_by_multiple_tickers(self):
        """companies() accepts list of tickers."""
        df = sec.companies(ticker=["AAPL", "MSFT"])
        tickers = df["ticker"].tolist()
        assert set(tickers) == {"AAPL", "MSFT"}

    def test_filters_by_filer_category(self):
        """companies() filters by filer category."""
        df = sec.companies(filer_category="Large Accelerated Filer")
        assert len(df) > 0
        assert (df["filer_category"] == "Large Accelerated Filer").all()

    def test_filters_by_state(self):
        """companies() filters by state."""
        df = sec.companies(state="CA")
        assert len(df) > 0
        assert (df["state_business"] == "CA").all()

    def test_filters_by_country(self):
        """companies() filters by country."""
        df = sec.companies(country="US")
        assert len(df) > 0
        assert (df["country_business"] == "US").all()

    def test_combined_filters(self):
        """companies() supports combined filters."""
        df = sec.companies(
            filer_category="Large Accelerated Filer",
            state="CA",
        )
        if len(df) > 0:
            assert (df["filer_category"] == "Large Accelerated Filer").all()
            assert (df["state_business"] == "CA").all()

    def test_has_expected_columns(self):
        """companies() returns DataFrame with expected schema."""
        df = sec.companies(ticker="AAPL")
        expected_cols = {
            "ticker",
            "company_name",
            "cik",
            "sic_code",
            "filer_category",
            "is_wksi",
            "country_business",
            "state_business",
            "country_incorporation",
            "fiscal_year_end_month",
        }
        # Allow for additional columns but require expected ones
        assert expected_cols <= set(df.columns)


class TestListFilerCategories:
    """Tests for data.sec.list_filer_categories() function."""

    def test_returns_list(self):
        """list_filer_categories() returns a list of strings."""
        categories = sec.list_filer_categories()
        assert isinstance(categories, list)
        assert len(categories) > 0
        assert all(isinstance(c, str) for c in categories)

    def test_categories_are_sorted(self):
        """list_filer_categories() returns sorted list."""
        categories = sec.list_filer_categories()
        assert categories == sorted(categories)

    def test_includes_known_categories(self):
        """list_filer_categories() includes expected categories."""
        categories = sec.list_filer_categories()
        # These are standard SEC filer categories
        assert "Large Accelerated Filer" in categories
        assert "Accelerated Filer" in categories
