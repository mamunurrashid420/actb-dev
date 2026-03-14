"""Pandera schemas for data validation across pipeline layers.

This module defines schemas for validating data at different layers of the
medallion architecture (bronze, silver, gold). Schemas use coerce=False since
bronze data already has correct types from parquet IO.
"""

import pandas as pd
import pandera.pandas as pa


class BronzeTimeseriesSchema(pa.DataFrameModel):
    """Base schema for bronze layer timeseries data.

    All bronze timeseries assets should include these columns with proper types.
    """

    date: pd.Timestamp = pa.Field(nullable=False)
    value: float = pa.Field(nullable=True)

    class Config:
        """Schema configuration."""

        strict = False  # Allow extra columns
        coerce = False  # Don't coerce types (already correct from parquet)


class FredTimeseriesSchema(BronzeTimeseriesSchema):
    """Schema for FRED timeseries data (bronze/fred/series)."""

    series_id: str = pa.Field(nullable=False)

    class Config:
        """Schema configuration."""

        strict = False
        coerce = False


class BlsTimeseriesSchema(BronzeTimeseriesSchema):
    """Schema for BLS timeseries data (bronze/bls/all_series)."""

    series_id: str = pa.Field(nullable=False)
    year: int = pa.Field(ge=1900, le=2100, nullable=False)
    period: str = pa.Field(nullable=False)

    class Config:
        """Schema configuration."""

        strict = False
        coerce = False


class WorldBankTimeseriesSchema(BronzeTimeseriesSchema):
    """Schema for World Bank timeseries data (bronze/world_bank/timeseries)."""

    country_code: str = pa.Field(
        str_length={"min_value": 2, "max_value": 3}, nullable=False
    )
    indicator_code: str = pa.Field(nullable=False)

    class Config:
        """Schema configuration."""

        strict = False
        coerce = False


class NoaaMonthlySchema(pa.DataFrameModel):
    """Schema for NOAA weather data (bronze/noaa/daily, monthly, annual).

    All NOAA datasets share the same structure: station_id, date, and many
    optional weather measurement columns. This schema validates all three
    temporal resolutions (daily, monthly, annual).

    Note: NOAA data comes with weather values as strings (object dtype) since
    some values may be 'None' or have quality flags.
    """

    station_id: str = pa.Field(nullable=False)
    date: pd.Timestamp = pa.Field(nullable=False)

    # Weather measurements stored as object (string) dtype in raw data
    # Conversion to numeric happens in silver layer
    # Not explicitly validating weather columns - they're optional and varied

    class Config:
        """Schema configuration."""

        strict = False  # Allow many other optional weather columns
        coerce = False


class NasaPowerSchema(pa.DataFrameModel):
    """Schema for NASA POWER weather data (bronze/nasa_power/daily and monthly).

    Contains date, location_id, coordinates, and optional weather measurement columns.
    Weather variables are optional since different temporal resolutions may include
    different parameters.
    """

    date: pd.Timestamp = pa.Field(nullable=False)
    location_id: str = pa.Field(nullable=False)
    latitude: float = pa.Field(nullable=False)
    longitude: float = pa.Field(nullable=False)

    # Weather measurements (T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, RH2M, TS, etc.)
    # are optional and not explicitly validated - they vary by temporal resolution

    class Config:
        """Schema configuration."""

        strict = False  # Allow many optional weather columns
        coerce = False


class SecForm10KSchema(pa.DataFrameModel):
    """Schema for SEC Form 10-K annual filing metadata (bronze/sec/form_10k)."""

    ticker: str = pa.Field(nullable=False)
    cik: str = pa.Field(nullable=False)
    company_name: str = pa.Field(nullable=False)
    fiscal_year: int = pa.Field(ge=1990, le=2100, nullable=False)
    filing_date: str = pa.Field(nullable=False)
    period_of_report: str = pa.Field(nullable=False)
    accession_number: str = pa.Field(nullable=False)
    filing_url: str = pa.Field(nullable=False)

    class Config:
        """Schema configuration."""

        strict = False
        coerce = False


class SecForm10QSchema(pa.DataFrameModel):
    """Schema for SEC Form 10-Q quarterly filing metadata (bronze/sec/form_10q)."""

    ticker: str = pa.Field(nullable=False)
    cik: str = pa.Field(nullable=False)
    company_name: str = pa.Field(nullable=False)
    fiscal_year: int = pa.Field(ge=1990, le=2100, nullable=False)
    quarter: int = pa.Field(ge=1, le=4, nullable=False)
    filing_date: str = pa.Field(nullable=False)
    period_of_report: str = pa.Field(nullable=False)
    accession_number: str = pa.Field(nullable=False)
    filing_url: str = pa.Field(nullable=False)

    class Config:
        """Schema configuration."""

        strict = False
        coerce = False


class SecForm4Schema(pa.DataFrameModel):
    """Schema for SEC Form 4 insider trading filing metadata (bronze/sec/form_4)."""

    ticker: str = pa.Field(nullable=False)
    cik: str = pa.Field(nullable=False)
    company_name: str = pa.Field(nullable=False)
    year: int = pa.Field(ge=1990, le=2100, nullable=False)
    month: int = pa.Field(ge=1, le=12, nullable=False)
    filing_date: str = pa.Field(nullable=False)
    accession_number: str = pa.Field(nullable=False)
    filing_url: str = pa.Field(nullable=False)

    class Config:
        """Schema configuration."""

        strict = False
        coerce = False


class SecForm13FSchema(pa.DataFrameModel):
    """Schema for SEC Form 13-F institutional holdings filing metadata (bronze/sec/form_13f)."""

    cik: str = pa.Field(nullable=False)
    institution_name: str = pa.Field(nullable=False)
    fiscal_year: int = pa.Field(ge=1990, le=2100, nullable=False)
    quarter: int = pa.Field(ge=1, le=4, nullable=False)
    filing_date: str = pa.Field(nullable=False)
    period_of_report: str = pa.Field(nullable=False)
    accession_number: str = pa.Field(nullable=False)
    filing_url: str = pa.Field(nullable=False)

    class Config:
        """Schema configuration."""

        strict = False
        coerce = False


# =============================================================================
# GOLD LAYER SCHEMAS
# =============================================================================


class GoldAnnualReportSchema(pa.DataFrameModel):
    """Schema for gold annual report (gold/companies/financials/annual_report)."""

    ticker: str = pa.Field(nullable=False)
    fiscal_year: int = pa.Field(ge=1990, le=2100, nullable=False)
    available: bool = pa.Field(nullable=False)

    class Config:
        """Schema configuration."""

        strict = False
        coerce = False


class GoldQuarterlyReportSchema(pa.DataFrameModel):
    """Schema for gold quarterly report (gold/companies/financials/quarterly_report)."""

    ticker: str = pa.Field(nullable=False)
    fiscal_year: int = pa.Field(ge=1990, le=2100, nullable=False)
    quarter: int = pa.Field(ge=1, le=4, nullable=False)
    available: bool = pa.Field(nullable=False)

    class Config:
        """Schema configuration."""

        strict = False
        coerce = False


class GoldInsiderActivitySchema(pa.DataFrameModel):
    """Schema for gold insider activity (gold/companies/insider/insider_activity)."""

    ticker: str = pa.Field(nullable=False)
    year: int = pa.Field(ge=1990, le=2100, nullable=False)
    month: int = pa.Field(ge=1, le=12, nullable=False)
    available: bool = pa.Field(nullable=False)

    class Config:
        """Schema configuration."""

        strict = False
        coerce = False


class GoldPortfolioHoldingsSchema(pa.DataFrameModel):
    """Schema for gold portfolio holdings (gold/institutions/holdings/quarterly_positions)."""

    institution_cik: str = pa.Field(nullable=False)
    fiscal_year: int = pa.Field(ge=1990, le=2100, nullable=False)
    quarter: int = pa.Field(ge=1, le=4, nullable=False)
    available: bool = pa.Field(nullable=False)

    class Config:
        """Schema configuration."""

        strict = False
        coerce = False
