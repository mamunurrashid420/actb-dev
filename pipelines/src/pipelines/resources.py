import datetime as dt
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

import dagster as dg
import fredapi
import httpx
import pandas as pd
import polars as pl
import requests
import stamina

from pipelines.resource_utils import is_cache_valid

DEFAULT_LOOKBACK_YEARS = 10

# USDA FAS API configuration
# API docs: https://api.fas.usda.gov/docs
USDA_FAS_BASE_URL = "https://api.fas.usda.gov"
USDA_PSD_BULK_URL = "https://apps.fas.usda.gov/psdonline/downloads/psd_alldata_csv.zip"

# BEA API configuration
# API docs: https://apps.bea.gov/api/
# Bulk downloads: https://apps.bea.gov/national/Release/TXT/
BEA_BASE_URL = "https://apps.bea.gov/api/data"

# NIPA flat file URLs (bulk download - replaces broken ZIP)
BEA_NIPA_DATA_URLS = {
    "A": "https://apps.bea.gov/national/Release/TXT/NipaDataA.txt",
    "Q": "https://apps.bea.gov/national/Release/TXT/NipaDataQ.txt",
    "M": "https://apps.bea.gov/national/Release/TXT/NipaDataM.txt",
}
BEA_NIPA_REGISTER_URL = "https://apps.bea.gov/national/Release/TXT/SeriesRegister.txt"

# Datasets to fetch via API (skip Regional - too granular)
BEA_API_DATASETS = [
    "NIPA",
    "GDPByIndustry",
    "UnderlyingGDPbyIndustry",
    "NIUnderlyingDetail",
    "FixedAssets",
    "InputOutput",
    "ITA",
    "IIP",
    "IntlServTrade",
    "IntlServSTA",
    "MNE",
]

# ECB Data Portal API configuration
ECB_DATA_API_URL = "https://data-api.ecb.europa.eu/service"


class FredApiResource(dg.ConfigurableResource):
    """Resource for interacting with the Federal Reserve Economic Data (FRED) API.

    Attributes:
        api_key: FRED API key for authentication
        rate_limit_delay: Delay between API calls in seconds (default 0.5s = 120 req/min)
    """

    api_key: str
    rate_limit_delay: float = 0.5  # 500ms = safe margin under 120 req/min limit

    def get_series(self, series_id: str) -> pd.Series:
        """Fetch a data series from FRED."""
        time.sleep(self.rate_limit_delay)
        client = fredapi.Fred(api_key=self.api_key)
        return client.get_series(series_id)

    def search_series(
        self,
        text: str = "economic",
        limit: int = 1000,
        order_by: str = "popularity",
        sort_order: str = "desc",
    ) -> pd.DataFrame:
        """Search for FRED series with popularity ordering.

        Args:
            text: Search text to match against series metadata
            limit: Maximum number of results (max 1000)
            order_by: Sort field ('popularity', 'search_rank', 'series_id', etc.)
            sort_order: Sort direction ('asc' or 'desc')

        Returns:
            DataFrame with series metadata including id, title, popularity, frequency
        """
        client = fredapi.Fred(api_key=self.api_key)
        return client.search(
            text=text,
            limit=limit,
            order_by=order_by,
            sort_order=sort_order,
        )


class WorldBankApiResource(dg.ConfigurableResource):
    """Resource for interacting with the World Bank API.

    No API key required - World Bank API is public.
    """

    def get_indicator(
        self, indicator_code: str, countries: list[str], date_range: str = "1960:2024"
    ) -> pd.DataFrame:
        """Fetch indicator data for multiple countries from World Bank API."""
        # Join countries with semicolon for batch request
        country_str = ";".join(countries)

        # Build API request
        url = f"https://api.worldbank.org/v2/country/{country_str}/indicator/{indicator_code}"
        params = {"format": "json", "date": date_range, "per_page": 10000}

        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()

        data = response.json()

        # World Bank returns [pagination_info, data_array]
        if len(data) < 2 or not data[1]:
            return pd.DataFrame(
                columns=["country_code", "country_name", "date", "value"]
            )

        # Parse data array into DataFrame
        records = []
        for item in data[1]:
            # Skip null values
            if item.get("value") is None:
                continue

            records.append({
                # Use 3-letter ISO code to match partition keys
                "country_code": item.get("countryiso3code", item["country"]["id"]),
                "country_name": item["country"]["value"],
                "date": item["date"],
                "value": float(item["value"]),
            })

        # Ensure columns are defined even if records is empty
        return pd.DataFrame(
            records, columns=["country_code", "country_name", "date", "value"]
        )


class BlsApiResource(dg.ConfigurableResource):
    """Resource for interacting with the Bureau of Labor Statistics API.

    BLS provides monthly/quarterly US economic data including employment,
    wages, and prices. API key required for v2 access (500 queries/day).

    Attributes:
        api_key: BLS API key for v2 access
    """

    api_key: str

    def get_series(
        self, series_id: str, start_year: int = 2000, end_year: int = 2025
    ) -> pd.DataFrame:
        """Fetch data series from BLS API v2."""
        url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
        headers = {"Content-type": "application/json"}

        data = json.dumps({
            "seriesid": [series_id],
            "startyear": str(start_year),
            "endyear": str(end_year),
            "registrationkey": self.api_key,
        })

        response = requests.post(url, data=data, headers=headers, timeout=60)
        response.raise_for_status()

        json_data = response.json()

        # Check for successful response
        if json_data.get("status") != "REQUEST_SUCCEEDED":
            return pd.DataFrame(columns=["date", "value", "year", "period"])

        # Extract data from response
        series_data = json_data.get("Results", {}).get("series", [])
        if not series_data or not series_data[0].get("data"):
            return pd.DataFrame(columns=["date", "value", "year", "period"])

        # Parse data points
        records = []
        for item in series_data[0]["data"]:
            year = item["year"]
            period = item["period"]
            value = item.get("value")

            if value is None:
                continue

            # Convert period code to date
            # M01-M12 = monthly, Q01-Q04 = quarterly
            if period.startswith("M"):
                month = period[1:]
                date = pd.to_datetime(f"{year}-{month}", format="%Y-%m")
            elif period.startswith("Q"):
                quarter = period[1:]
                # Use first month of quarter
                month = str((int(quarter) - 1) * 3 + 1)
                date = pd.to_datetime(f"{year}-{month}", format="%Y-%m")
            else:
                continue

            records.append({
                "date": date,
                "value": float(value),
                "year": int(year),
                "period": period,
            })

        # Sort by date (BLS returns newest first)
        df = pd.DataFrame(records, columns=["date", "value", "year", "period"])
        df = df.sort_values("date").reset_index(drop=True)

        return df


class BeaApiResource(dg.ConfigurableResource):
    """Resource for Bureau of Economic Analysis API and bulk downloads.

    BEA provides GDP, personal income, consumption, trade, and corporate profit data.
    API key required (free, instant signup at apps.bea.gov/api/signup).

    Rate limit: 100 requests/min, 100 MB/min (1-hour lockout if exceeded)

    Attributes:
        api_key: BEA API key for authentication
        rate_limit_delay: Delay between API calls in seconds (default 0.6s)
    """

    api_key: str
    rate_limit_delay: float = 0.6  # Conservative for 100 req/min limit

    def _make_api_request(self, params: dict) -> dict:
        """Make authenticated request to BEA API."""
        params["UserID"] = self.api_key
        params["ResultFormat"] = "JSON"

        time.sleep(self.rate_limit_delay)
        response = requests.get(BEA_BASE_URL, params=params, timeout=120)
        response.raise_for_status()

        data = response.json()

        # Check for BEA API errors
        if "BEAAPI" in data and "Error" in data["BEAAPI"]:
            error_msg = (
                data["BEAAPI"]["Error"]
                .get("ErrorDetail", {})
                .get("Description", "Unknown BEA API error")
            )
            raise ValueError(f"BEA API error: {error_msg}")

        return data

    def download_nipa_bulk(self) -> pl.LazyFrame:
        """Download complete NIPA bulk data from flat files (~83MB total).

        Source: https://apps.bea.gov/national/Release/TXT/
        - NipaDataA.txt (annual), NipaDataQ.txt (quarterly), NipaDataM.txt (monthly)
        - SeriesRegister.txt (metadata: SeriesCode → Label, Table mappings)

        Contains ALL NIPA series since 1929.

        Returns:
            LazyFrame with columns: series_code, period, value, frequency, plus metadata
        """
        import io

        all_frames = []

        # Download each frequency file (A=annual, Q=quarterly, M=monthly)
        for freq, url in BEA_NIPA_DATA_URLS.items():
            response = requests.get(url, timeout=120)
            response.raise_for_status()

            # Parse CSV file with Polars
            # BEA format: %SeriesCode,Period,Value (with quoted values containing commas)
            # Force all columns to string initially to avoid schema mismatch on concat
            df = pl.read_csv(
                io.StringIO(response.text),
                separator=",",
                infer_schema_length=0,  # Force all columns to String
            ).with_columns(pl.lit(freq).alias("frequency"))

            all_frames.append(df)

        if not all_frames:
            return pl.LazyFrame()

        # Concatenate all frequency data
        result = pl.concat(all_frames)

        # Download series register (metadata)
        register_response = requests.get(BEA_NIPA_REGISTER_URL, timeout=60)
        register_response.raise_for_status()

        register = pl.read_csv(
            io.StringIO(register_response.text),
            separator=",",
            infer_schema_length=0,  # Force all columns to String
        )

        # Standardize column names (lowercase, underscores, strip % prefix)
        result = result.rename({
            col: col.lower().replace(" ", "_").lstrip("%") for col in result.columns
        })
        register = register.rename({
            col: col.lower().replace(" ", "_").lstrip("%") for col in register.columns
        })

        # Merge data with metadata (register has seriescode → table, line, description)
        if "seriescode" in result.columns and "seriescode" in register.columns:
            result = result.join(register, on="seriescode", how="left")

        # Return as LazyFrame for efficient downstream processing
        return result.lazy()

    def get_table_data(
        self,
        table_name: str,
        frequency: str = "Q",
        year: str = "ALL",
        dataset: str = "NIPA",
    ) -> pl.DataFrame:
        """Fetch single table via BEA API.

        Args:
            table_name: BEA table name (e.g., 'T10105' for GDP components)
            frequency: Data frequency ('A' = annual, 'Q' = quarterly, 'M' = monthly)
            year: Year(s) to fetch ('ALL' for complete history, or specific year like '2024')
            dataset: BEA dataset name (e.g., 'NIPA', 'GDPByIndustry')

        Returns:
            Polars DataFrame with table data
        """
        params = {
            "method": "GetData",
            "DataSetName": dataset,
            "TableName": table_name,
            "Frequency": frequency,
            "Year": year,
        }

        data = self._make_api_request(params)

        # Parse BEA response structure
        if "BEAAPI" not in data or "Results" not in data["BEAAPI"]:
            return pl.DataFrame()

        results = data["BEAAPI"]["Results"]
        if "Data" not in results:
            return pl.DataFrame()

        df = pl.DataFrame(results["Data"])

        # Standardize column names (lowercase, underscores)
        df = df.rename({col: col.lower().replace(" ", "_") for col in df.columns})

        return df

    def get_current_year_data(self) -> pl.LazyFrame:
        """Fetch current year NIPA data via API for incremental updates.

        Fetches all NIPA tables for current year. Only fetches highest resolution:
        - Monthly if available, else quarterly, else annual

        Returns:
            LazyFrame with current year data from all tables
        """
        current_year = dt.datetime.now().year

        # Get list of all NIPA tables dynamically
        tables_df = self.get_table_list()
        if tables_df.height == 0:
            return pl.LazyFrame()

        # Extract table names
        table_col = "tablename" if "tablename" in tables_df.columns else "key"
        tables = tables_df[table_col].to_list()

        all_frames = []

        for table_name in tables:
            # Try monthly first (highest resolution), then quarterly, then annual
            for freq in ["M", "Q", "A"]:
                df = self.get_table_data(
                    table_name,
                    frequency=freq,
                    year=str(current_year),
                    dataset="NIPA",
                )
                if df.height > 0:
                    df = df.with_columns([
                        pl.lit(table_name).alias("table_name"),
                        pl.lit(freq).alias("frequency"),
                    ])
                    all_frames.append(df)
                    break  # Got data at this resolution, skip lower resolutions

        if not all_frames:
            return pl.LazyFrame()

        return pl.concat(all_frames).lazy()

    def get_parameter_list(self, dataset_name: str = "NIPA") -> pl.DataFrame:
        """Get list of available parameters for a dataset."""
        params = {
            "method": "GetParameterList",
            "DataSetName": dataset_name,
        }

        data = self._make_api_request(params)

        if "BEAAPI" not in data or "Results" not in data["BEAAPI"]:
            return pl.DataFrame()

        results = data["BEAAPI"]["Results"]
        if "Parameter" not in results:
            return pl.DataFrame()

        return pl.DataFrame(results["Parameter"])

    def get_table_list(self, dataset_name: str = "NIPA") -> pl.DataFrame:
        """Get list of all available tables for a dataset."""
        params = {
            "method": "GetParameterValues",
            "DataSetName": dataset_name,
            "ParameterName": "TableName",
        }

        data = self._make_api_request(params)

        if "BEAAPI" not in data or "Results" not in data["BEAAPI"]:
            return pl.DataFrame()

        results = data["BEAAPI"]["Results"]
        if "ParamValue" not in results:
            return pl.DataFrame()

        return pl.DataFrame(results["ParamValue"])


# SEC EDGAR retry configuration
SEC_NETWORK_EXCEPTIONS = (
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    httpx.PoolTimeout,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
)


class RetryableHTTPError(Exception):
    """Wrapper for HTTP errors that should be retried (429, 5xx)."""

    def __init__(self, original: httpx.HTTPStatusError):
        self.original = original
        super().__init__(str(original))


class SecEdgarResource(dg.ConfigurableResource):
    """Resource for interacting with SEC EDGAR bulk data.

    Downloads bulk data files directly from SEC servers using httpx.
    No API key required, but must set identity per SEC requirements.

    Attributes:
        identity: Contact info for SEC (e.g., "Name email@domain.com")
        timeout: HTTP timeout in seconds for SEC requests (default 120s)
    """

    identity: str
    timeout: float = 120.0
    rate_limit_delay: float = 0.1  # Delay between API calls in seconds (100ms)

    @stamina.retry(
        on=(*SEC_NETWORK_EXCEPTIONS, RetryableHTTPError),
        attempts=5,
        wait_initial=10.0,
        wait_max=120.0,
        wait_jitter=5.0,
    )
    def fetch_company_tickers(self) -> pd.DataFrame:
        """Fetch SEC's complete CIK↔ticker mapping from company_tickers.json.

        Source: https://www.sec.gov/files/company_tickers.json

        The SEC returns JSON with format:
        {
          "0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."},
          "1": {"cik_str": "789019", "ticker": "MSFT", "title": "Microsoft Corporation"},
          ...
        }

        Returns:
            DataFrame with columns: cik (zero-padded to 10 chars), ticker, company_name

        Raises:
            RetryableHTTPError: If HTTP 429 or 5xx error occurs (will retry)
        """
        url = "https://www.sec.gov/files/company_tickers.json"

        time.sleep(self.rate_limit_delay)
        try:
            response = httpx.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Convert to DataFrame
            records = []
            for item in data.values():
                # Zero-pad CIK to 10 characters (SEC standard)
                cik = str(item["cik_str"]).zfill(10)
                ticker = item["ticker"]
                company_name = item["title"]

                records.append({
                    "cik": cik,
                    "ticker": ticker,
                    "company_name": company_name,
                })

            return pd.DataFrame(records, columns=["cik", "ticker", "company_name"])

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 500, 502, 503, 504):
                raise RetryableHTTPError(e) from e
            raise

    @stamina.retry(
        on=(*SEC_NETWORK_EXCEPTIONS, RetryableHTTPError),
        attempts=5,
        wait_initial=10.0,
        wait_max=120.0,
        wait_jitter=5.0,
    )
    def download_fsds_quarter(self, quarter: str) -> "Path":
        """Download SEC Financial Statement Data Sets quarterly zip file.

        FSDS provides structured financial data including segment information.
        Files are cached locally to avoid redundant downloads.

        Args:
            quarter: Quarter string in SEC format like '2024q3'

        Returns:
            Path to downloaded/cached zip file

        Raises:
            RetryableHTTPError: If HTTP 429 or 5xx error occurs (will retry)
        """
        from pathlib import Path

        url = f"https://www.sec.gov/files/dera/data/financial-statement-data-sets/{quarter}.zip"
        cache_dir = Path.home() / ".cache" / "sec_edgar" / "fsds"
        cache_dir.mkdir(parents=True, exist_ok=True)

        zip_path = cache_dir / f"{quarter}.zip"

        # Return cached file if exists
        if zip_path.exists():
            return zip_path

        time.sleep(self.rate_limit_delay)
        try:
            # Download with proper User-Agent per SEC requirements
            response = httpx.get(
                url,
                timeout=self.timeout,
                headers={"User-Agent": self.identity},
            )
            response.raise_for_status()
            zip_path.write_bytes(response.content)
            return zip_path

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 500, 502, 503, 504):
                raise RetryableHTTPError(e) from e
            raise

    @stamina.retry(
        on=(*SEC_NETWORK_EXCEPTIONS, RetryableHTTPError),
        attempts=5,
        wait_initial=10.0,
        wait_max=120.0,
        wait_jitter=5.0,
    )
    def download_company_facts_zip(self, cache_dir: "Path | None" = None) -> "Path":
        """Download SEC companyfacts.zip bulk data file.

        Contains XBRL financial facts for all public companies (~3GB).
        Files are cached locally with 24-hour TTL (SEC updates daily).

        Args:
            cache_dir: Optional cache directory. Defaults to ~/.cache/sec_edgar/

        Returns:
            Path to downloaded/cached zip file (NOT extracted)

        Raises:
            RetryableHTTPError: If HTTP 429 or 5xx error occurs (will retry)
        """
        from pathlib import Path

        url = "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"
        cache_dir = cache_dir or Path.home() / ".cache" / "sec_edgar"
        cache_dir.mkdir(parents=True, exist_ok=True)

        zip_path = cache_dir / "companyfacts.zip"

        # Check cache freshness (24-hour TTL - SEC updates daily)
        if zip_path.exists():
            age_seconds = time.time() - zip_path.stat().st_mtime
            if age_seconds < 86400:  # 24 hours
                return zip_path

        time.sleep(self.rate_limit_delay)
        try:
            # Download with proper User-Agent per SEC requirements
            response = httpx.get(
                url,
                timeout=self.timeout,
                headers={"User-Agent": self.identity},
            )
            response.raise_for_status()
            zip_path.write_bytes(response.content)
            return zip_path

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 500, 502, 503, 504):
                raise RetryableHTTPError(e) from e
            raise

    @stamina.retry(
        on=(*SEC_NETWORK_EXCEPTIONS, RetryableHTTPError),
        attempts=5,
        wait_initial=10.0,
        wait_max=120.0,
        wait_jitter=5.0,
    )
    def download_submissions_zip(self, cache_dir: "Path | None" = None) -> "Path":
        """Download SEC submissions.zip bulk data file.

        Contains filing metadata for all public companies (~1GB).
        Files are cached locally with 24-hour TTL (SEC updates daily).

        Args:
            cache_dir: Optional cache directory. Defaults to ~/.cache/sec_edgar/

        Returns:
            Path to downloaded/cached zip file (NOT extracted)

        Raises:
            RetryableHTTPError: If HTTP 429 or 5xx error occurs (will retry)
        """
        from pathlib import Path

        url = "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip"
        cache_dir = cache_dir or Path.home() / ".cache" / "sec_edgar"
        cache_dir.mkdir(parents=True, exist_ok=True)

        zip_path = cache_dir / "submissions.zip"

        # Check cache freshness (24-hour TTL - SEC updates daily)
        if zip_path.exists():
            age_seconds = time.time() - zip_path.stat().st_mtime
            if age_seconds < 86400:  # 24 hours
                return zip_path

        time.sleep(self.rate_limit_delay)
        try:
            # Download with proper User-Agent per SEC requirements
            response = httpx.get(
                url,
                timeout=self.timeout,
                headers={"User-Agent": self.identity},
            )
            response.raise_for_status()
            zip_path.write_bytes(response.content)
            return zip_path

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 500, 502, 503, 504):
                raise RetryableHTTPError(e) from e
            raise

    def _quarter_to_form_13f_filename(self, quarter: str) -> str:
        """Convert partition key (e.g., '2024-Q3') to Form 13F Data Set filename.

        DERA publishes Form 13F data quarterly with filenames based on the 3-month
        filing window. The naming convention maps quarters to date ranges:
        - Q1 (Dec-Feb filings) -> 01dec{year-1}-28feb{year}_form13f.zip
        - Q2 (Mar-May filings) -> 01mar{year}-31may{year}_form13f.zip
        - Q3 (Jun-Aug filings) -> 01jun{year}-31aug{year}_form13f.zip
        - Q4 (Sep-Nov filings) -> 01sep{year}-30nov{year}_form13f.zip

        Note: Q1 spans Dec of previous year through Feb of current year.
        """
        import calendar

        year, q = int(quarter[:4]), int(quarter[-1])

        # Map quarter to month ranges
        quarter_months = {
            1: ("dec", "feb"),  # Q1: Dec-Feb
            2: ("mar", "may"),  # Q2: Mar-May
            3: ("jun", "aug"),  # Q3: Jun-Aug
            4: ("sep", "nov"),  # Q4: Sep-Nov
        }

        start_month, end_month = quarter_months[q]

        # Calculate start year (Q1 starts in previous December)
        start_year = year - 1 if q == 1 else year

        # Calculate end day (last day of end month)
        end_month_num = {"feb": 2, "may": 5, "aug": 8, "nov": 11}[end_month]
        _, end_day = calendar.monthrange(year, end_month_num)

        return f"01{start_month}{start_year}-{end_day}{end_month}{year}_form13f.zip"

    @stamina.retry(
        on=(*SEC_NETWORK_EXCEPTIONS, RetryableHTTPError),
        attempts=5,
        wait_initial=10.0,
        wait_max=120.0,
        wait_jitter=5.0,
    )
    def download_form_13f_dataset(
        self, quarter: str, cache_dir: "Path | None" = None
    ) -> "Path":
        """Download SEC Form 13F Data Set ZIP for a specific quarter.

        DERA (Division of Economic and Risk Analysis) publishes quarterly Form 13F
        Data Sets containing structured holdings data for all institutional managers.
        Data is published ~45 days after quarter end.

        Args:
            quarter: Quarter string like '2024-Q2'
            cache_dir: Optional cache directory. Defaults to ~/.cache/sec_edgar/form_13f

        Returns:
            Path to downloaded/cached zip file

        Raises:
            RetryableHTTPError: If HTTP 429 or 5xx error occurs (will retry)
        """
        from pathlib import Path

        filename = self._quarter_to_form_13f_filename(quarter)
        url = f"https://www.sec.gov/files/structureddata/data/form-13f-data-sets/{filename}"

        cache_dir = cache_dir or Path.home() / ".cache" / "sec_edgar" / "form_13f"
        cache_dir.mkdir(parents=True, exist_ok=True)

        zip_path = cache_dir / filename

        # Return cached file if exists (no TTL - quarterly data is immutable)
        if zip_path.exists():
            return zip_path

        time.sleep(self.rate_limit_delay)
        try:
            response = httpx.get(
                url,
                timeout=self.timeout,
                headers={"User-Agent": self.identity},
            )
            response.raise_for_status()
            zip_path.write_bytes(response.content)
            return zip_path

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 500, 502, 503, 504):
                raise RetryableHTTPError(e) from e
            raise

    def check_form_13f_dataset_available(self, quarter: str) -> tuple[bool, str | None]:
        """Check if a Form 13F Data Set is available via HTTP HEAD.

        Used by sensors to detect when DERA publishes new quarterly data.

        Args:
            quarter: Quarter string like '2024-Q2'

        Returns:
            Tuple of (is_available, last_modified_str)
            - is_available: True if the file exists
            - last_modified_str: Last-Modified header value if available
        """
        filename = self._quarter_to_form_13f_filename(quarter)
        url = f"https://www.sec.gov/files/structureddata/data/form-13f-data-sets/{filename}"

        try:
            time.sleep(self.rate_limit_delay)
            response = httpx.head(
                url,
                timeout=30.0,
                headers={"User-Agent": self.identity},
            )
            response.raise_for_status()
            last_modified = response.headers.get("Last-Modified")
            return (True, last_modified)
        except httpx.HTTPStatusError:
            return (False, None)
        except httpx.TimeoutException:
            return (False, None)


class NoaaApiResource(dg.ConfigurableResource):
    """Resource for interacting with the NOAA Climate Data Online (CDO) API.

    NOAA provides access to historical weather and climate data from 100,000+
    stations globally. API token required (free registration at ncdc.noaa.gov).

    Attributes:
        api_token: NOAA CDO API token for authentication
    """

    api_token: str

    def _make_request(
        self,
        dataset: str,
        station_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Make request to NOAA API v1 (new access data service).

        Args:
            dataset: Dataset name ('daily-summaries', 'global-summary-of-the-month', etc.)
            station_id: NOAA station identifier (e.g., 'USW00094728')
            start_date: Start date in ISO format (YYYY-MM-DD), default: 10 years ago
            end_date: End date in ISO format (YYYY-MM-DD), default: today

        Returns:
            DataFrame with weather data
        """
        # Default date range: last 10 years
        if end_date is None:
            end_date = dt.datetime.now().strftime("%Y-%m-%d")
        if start_date is None:
            start_date = (
                dt.datetime.now() - dt.timedelta(days=365 * DEFAULT_LOOKBACK_YEARS)
            ).strftime("%Y-%m-%d")

        url = "https://www.ncei.noaa.gov/access/services/data/v1"
        params = {
            "dataset": dataset,
            "stations": station_id,
            "startDate": start_date,
            "endDate": end_date,
            "format": "json",
            "units": "metric",
        }
        headers = {"token": self.api_token}

        response = requests.get(url, params=params, headers=headers, timeout=120)
        response.raise_for_status()

        # Parse JSON response
        data = response.json()

        if not data:
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Standardize date column
        if "DATE" in df.columns:
            df["date"] = pd.to_datetime(df["DATE"])
            df = df.drop(columns=["DATE"])

        return df

    def get_daily_data(
        self,
        station_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Fetch daily weather data (GHCN-Daily)."""
        return self._make_request("daily-summaries", station_id, start_date, end_date)

    def get_monthly_data(
        self,
        station_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Fetch monthly summary data (GSOM)."""
        return self._make_request(
            "global-summary-of-the-month", station_id, start_date, end_date
        )

    def get_annual_data(
        self,
        station_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Fetch annual summary data (GSOY)."""
        return self._make_request(
            "global-summary-of-the-year", station_id, start_date, end_date
        )


class NasaPowerApiResource(dg.ConfigurableResource):
    """Resource for NASA POWER agricultural weather API.

    NASA POWER (Prediction Of Worldwide Energy Resources) provides global
    solar and meteorological data for agriculture, renewable energy, and
    sustainable development applications.

    Features:
    - Global coverage since 1981
    - 50km spatial resolution
    - Agriculture-specific variables (soil temperature, solar radiation)
    - Free public access, no authentication required

    Attributes:
        None - NASA POWER API is public and requires no authentication
    """

    # Date format mappings for NASA POWER API requests and responses
    DATE_REQUEST_FORMATS: ClassVar[dict[str, str]] = {
        "monthly": "%Y",
        "daily": "%Y%m%d",
        "annual": "%Y%m%d",
    }
    DATE_PARSE_FORMATS: ClassVar[dict[str, str]] = {
        "monthly": "%Y%m",
        "daily": "%Y%m%d",
        "annual": "%Y%m%d",
    }

    def _make_request(
        self,
        temporal: str,
        latitude: float,
        longitude: float,
        start_date: str | None = None,
        end_date: str | None = None,
        parameters: list[str] | None = None,
    ) -> pd.DataFrame:
        """Make request to NASA POWER API.

        Args:
            temporal: Temporal resolution ('daily', 'monthly', 'annual')
            latitude: Latitude coordinate (-90 to 90)
            longitude: Longitude coordinate (-180 to 180)
            start_date: Start date in YYYYMMDD format, default: 10 years ago
            end_date: End date in YYYYMMDD format, default: today
            parameters: List of NASA POWER parameter codes

        Returns:
            DataFrame with weather data
        """
        # Default date range: last 10 years
        # Monthly API requires YYYY format, daily requires YYYYMMDD
        date_format = self.DATE_REQUEST_FORMATS.get(temporal, "%Y%m%d")
        if end_date is None:
            end_date = dt.datetime.now().strftime(date_format)
        if start_date is None:
            start_date = (
                dt.datetime.now() - dt.timedelta(days=365 * DEFAULT_LOOKBACK_YEARS)
            ).strftime(date_format)

        # Default agricultural parameters
        if parameters is None:
            parameters = [
                "T2M",  # Temperature at 2 meters
                "T2M_MAX",  # Maximum temperature
                "T2M_MIN",  # Minimum temperature
                "PRECTOTCORR",  # Corrected precipitation
                "RH2M",  # Relative humidity at 2 meters
                "TS",  # Earth skin temperature (soil)
                "ALLSKY_SFC_SW_DWN",  # Solar radiation
            ]

        url = f"https://power.larc.nasa.gov/api/temporal/{temporal}/point"
        params = {
            "parameters": ",".join(parameters),
            "community": "AG",  # Agriculture community
            "longitude": longitude,
            "latitude": latitude,
            "start": start_date,
            "end": end_date,
            "format": "JSON",
        }

        response = requests.get(url, params=params, timeout=120)
        response.raise_for_status()

        # Parse JSON response
        data = response.json()

        # NASA POWER returns nested structure: {parameters: {PARAM: {YYYYMMDD: value}}}
        if "properties" not in data or "parameter" not in data["properties"]:
            return pd.DataFrame()

        parameter_data = data["properties"]["parameter"]

        # Convert to DataFrame with date column
        records = []
        for param_code, time_series in parameter_data.items():
            for date_str, value in time_series.items():
                # Skip annual summary entries (month 13) in monthly data
                if temporal == "monthly" and date_str.endswith("13"):
                    continue
                # Find or create record for this date
                date_record = next((r for r in records if r["date"] == date_str), None)
                if date_record is None:
                    date_record = {"date": date_str}
                    records.append(date_record)
                date_record[param_code] = value

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)

        # Convert date column to datetime (format depends on temporal resolution)
        # Monthly response uses YYYYMM format, daily uses YYYYMMDD
        date_format = self.DATE_PARSE_FORMATS.get(temporal, "%Y%m%d")
        df["date"] = pd.to_datetime(df["date"], format=date_format)

        # Add location coordinates
        df = df.assign(latitude=latitude, longitude=longitude)

        return df

    def get_daily_data(
        self,
        latitude: float,
        longitude: float,
        start_date: str | None = None,
        end_date: str | None = None,
        parameters: list[str] | None = None,
    ) -> pd.DataFrame:
        """Fetch daily agricultural weather data."""
        return self._make_request(
            "daily", latitude, longitude, start_date, end_date, parameters
        )

    def get_monthly_data(
        self,
        latitude: float,
        longitude: float,
        start_date: str | None = None,
        end_date: str | None = None,
        parameters: list[str] | None = None,
    ) -> pd.DataFrame:
        """Fetch monthly agricultural weather data."""
        return self._make_request(
            "monthly", latitude, longitude, start_date, end_date, parameters
        )


class UsdaFasResource(dg.ConfigurableResource):
    """Resource for USDA Foreign Agricultural Service PSD API.

    Provides access to Production, Supply, and Distribution data for
    agricultural commodities worldwide. API key required from api.data.gov.

    Rate limit: 1,000 requests/hour (api.data.gov default)

    Attributes:
        api_key: API key from api.data.gov
        rate_limit_delay: Delay between requests in seconds (default 3.5s)
    """

    api_key: str
    rate_limit_delay: float = 3.5  # 3.55s sleep + ~0.5s latency < 1,000 req/hr

    def _make_api_request(self, endpoint: str, params: dict | None = None) -> dict:
        """Make authenticated request to USDA FAS API."""
        url = f"{USDA_FAS_BASE_URL}{endpoint}"
        headers = {"X-Api-Key": self.api_key}

        time.sleep(self.rate_limit_delay)
        response = requests.get(url, headers=headers, params=params, timeout=120)
        response.raise_for_status()

        return response.json()

    def get_commodities(self) -> pl.LazyFrame:
        """Fetch commodity registry from USDA FAS API."""
        data = self._make_api_request("/api/psd/commodities")

        if not data:
            return pl.LazyFrame(
                schema={"commodity_code": pl.Utf8, "commodity_name": pl.Utf8}
            )

        records = [
            {
                "commodity_code": item.get("commodityCode"),
                "commodity_name": item.get("commodityName"),
            }
            for item in data
        ]

        return pl.LazyFrame(records)

    def get_countries(self) -> pl.LazyFrame:
        """Fetch country registry from USDA FAS API."""
        data = self._make_api_request("/api/psd/countries")

        if not data:
            return pl.LazyFrame(
                schema={"country_code": pl.Utf8, "country_name": pl.Utf8}
            )

        records = [
            {
                "country_code": item.get("countryCode"),
                "country_name": item.get("countryName"),
            }
            for item in data
        ]

        return pl.LazyFrame(records)

    def download_bulk_csv(self) -> pl.LazyFrame:
        """Download complete PSD bulk data as CSV from PSD Online."""
        import io
        import zipfile

        response = requests.get(USDA_PSD_BULK_URL, timeout=300)
        response.raise_for_status()

        # Extract CSV from zip file
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            csv_files = [f for f in zf.namelist() if f.endswith(".csv")]
            if not csv_files:
                raise ValueError("No CSV file found in PSD bulk download")

            # Find the main data file - prefer psd_alldata, fall back to largest
            psd_alldata_files = [f for f in csv_files if "psd_alldata" in f.lower()]

            if psd_alldata_files:
                target_file = psd_alldata_files[0]
            else:
                target_file = max(csv_files, key=lambda f: zf.getinfo(f).file_size)

            with zf.open(target_file) as csv_file:
                df = pl.read_csv(csv_file, infer_schema_length=10000)

        # Standardize column names (lowercase, underscores)
        rename_map = {col: col.lower().replace(" ", "_") for col in df.columns}

        return df.rename(rename_map).lazy()

    def get_psd_by_commodity_year(
        self, commodity_code: str, market_year: int
    ) -> pl.LazyFrame:
        """Fetch PSD data for a single commodity and market year via API."""
        endpoint = f"/api/psd/commodity/{commodity_code}/country/all/year/{market_year}"
        data = self._make_api_request(endpoint)

        if not data:
            return pl.LazyFrame()

        # Convert to LazyFrame with standardized column names
        # API returns camelCase (e.g., commodityCode)
        # We need snake_case (e.g., commodity_code)
        df = pl.DataFrame(data)
        rename_map = {
            "commodityCode": "commodity_code",
            "countryCode": "country_code",
            "marketYear": "market_year",
            "calendarYear": "calendar_year",
            "attributeId": "attribute_id",
            "unitId": "unit_id",
        }
        # Only rename columns that exist
        existing_renames = {k: v for k, v in rename_map.items() if k in df.columns}

        return df.rename(existing_renames).lazy()

    # =========================================================================
    # ESR (Export Sales Reports) API Methods
    # =========================================================================

    def get_esr_regions(self) -> pl.LazyFrame:
        """Fetch ESR region registry."""
        data = self._make_api_request("/api/esr/regions")
        if not data:
            return pl.LazyFrame(schema={"region_code": pl.Utf8, "region_name": pl.Utf8})
        records = [
            {
                "region_code": str(item.get("regionCode", "")),
                "region_name": item.get("regionName"),
            }
            for item in data
        ]
        return pl.LazyFrame(records)

    def get_esr_countries(self) -> pl.LazyFrame:
        """Fetch ESR country registry with region codes."""
        data = self._make_api_request("/api/esr/countries")
        if not data:
            return pl.LazyFrame(
                schema={
                    "country_code": pl.Utf8,
                    "country_name": pl.Utf8,
                    "region_code": pl.Utf8,
                }
            )
        records = [
            {
                "country_code": str(item.get("countryCode", "")),
                "country_name": item.get("countryName"),
                "region_code": str(item.get("regionCode", "")),
            }
            for item in data
        ]
        return pl.LazyFrame(records)

    def get_esr_commodities(self) -> pl.LazyFrame:
        """Fetch ESR commodity registry."""
        data = self._make_api_request("/api/esr/commodities")
        if not data:
            return pl.LazyFrame(
                schema={"commodity_code": pl.Utf8, "commodity_name": pl.Utf8}
            )
        records = [
            {
                "commodity_code": str(item.get("commodityCode", "")),
                "commodity_name": item.get("commodityName"),
            }
            for item in data
        ]
        return pl.LazyFrame(records)

    def get_esr_units_of_measure(self) -> pl.LazyFrame:
        """Fetch ESR units of measure registry."""
        data = self._make_api_request("/api/esr/unitsOfMeasure")
        if not data:
            return pl.LazyFrame(schema={"unit_id": pl.Utf8, "unit_name": pl.Utf8})
        records = [
            {
                "unit_id": str(item.get("unitId", "")),
                "unit_name": item.get("unitName"),
            }
            for item in data
        ]
        return pl.LazyFrame(records)

    def get_esr_data_release_dates(self) -> pl.LazyFrame:
        """Fetch ESR data release dates for change detection.

        Returns commodity-level release dates to identify which data has changed.
        """
        data = self._make_api_request("/api/esr/datareleasedates")
        if not data:
            return pl.LazyFrame(
                schema={
                    "commodity_code": pl.Utf8,
                    "market_year": pl.Int64,
                    "release_date": pl.Utf8,
                }
            )
        records = [
            {
                "commodity_code": str(item.get("commodityCode", "")),
                "market_year": item.get("marketYear"),
                "release_date": item.get("releaseDate"),
            }
            for item in data
        ]
        return pl.LazyFrame(records)

    def get_esr_exports(self, commodity_code: str, market_year: int) -> pl.LazyFrame:
        """Fetch ESR export data for a commodity and market year.

        Args:
            commodity_code: ESR commodity code (e.g., '104' for Wheat-White)
            market_year: Market year (e.g., 2024)

        Returns:
            LazyFrame with US export records to all countries
        """
        endpoint = (
            f"/api/esr/exports/commodityCode/{commodity_code}"
            f"/allCountries/marketYear/{market_year}"
        )
        data = self._make_api_request(endpoint)
        if not data:
            return pl.LazyFrame()

        df = pl.DataFrame(data)
        # Standardize column names from camelCase to snake_case
        rename_map = {
            "commodityCode": "commodity_code",
            "countryCode": "country_code",
            "weekEndingDate": "week_ending_date",
            "marketYear": "market_year",
            "weeklyExports": "weekly_exports",
            "accumulatedExports": "accumulated_exports",
            "outstandingSales": "outstanding_sales",
            "grossSales": "gross_sales",
            "buyAdjust": "buy_adjust",
            "totalCommitment": "total_commitment",
            "unitId": "unit_id",
        }
        existing_renames = {k: v for k, v in rename_map.items() if k in df.columns}
        return df.rename(existing_renames).lazy()

    # =========================================================================
    # GATS (Global Agricultural Trade System) API Methods
    # =========================================================================

    def get_gats_regions(self) -> pl.LazyFrame:
        """Fetch GATS region registry."""
        data = self._make_api_request("/api/gats/regions")
        if not data:
            return pl.LazyFrame(schema={"region_code": pl.Utf8, "region_name": pl.Utf8})
        records = [
            {
                "region_code": str(item.get("regionCode", "")),
                "region_name": item.get("regionName"),
            }
            for item in data
        ]
        return pl.LazyFrame(records)

    def get_gats_countries(self) -> pl.LazyFrame:
        """Fetch GATS country registry with region codes."""
        data = self._make_api_request("/api/gats/countries")
        if not data:
            return pl.LazyFrame(
                schema={
                    "country_code": pl.Utf8,
                    "country_name": pl.Utf8,
                    "region_code": pl.Utf8,
                }
            )
        records = [
            {
                "country_code": str(item.get("countryCode", "")),
                "country_name": item.get("countryName"),
                "region_code": str(item.get("regionCode", "")),
            }
            for item in data
        ]
        return pl.LazyFrame(records)

    def get_gats_commodities(self) -> pl.LazyFrame:
        """Fetch GATS commodity registry (HS10 level)."""
        data = self._make_api_request("/api/gats/commodities")
        if not data:
            return pl.LazyFrame(
                schema={
                    "commodity_code": pl.Utf8,
                    "commodity_name": pl.Utf8,
                    "hs_code": pl.Utf8,
                }
            )
        records = [
            {
                "commodity_code": str(item.get("commodityCode", "")),
                "commodity_name": item.get("commodityName"),
                "hs_code": str(item.get("hsCode", "")),
            }
            for item in data
        ]
        return pl.LazyFrame(records)

    def get_gats_hs6_commodities(self) -> pl.LazyFrame:
        """Fetch GATS HS6-level commodity registry (for UN Trade correlation)."""
        data = self._make_api_request("/api/gats/HS6Commodities")
        if not data:
            return pl.LazyFrame(
                schema={
                    "hs6_code": pl.Utf8,
                    "commodity_name": pl.Utf8,
                }
            )
        records = [
            {
                "hs6_code": str(item.get("hs6Code", item.get("commodityCode", ""))),
                "commodity_name": item.get("commodityName"),
            }
            for item in data
        ]
        return pl.LazyFrame(records)

    def get_gats_units_of_measure(self) -> pl.LazyFrame:
        """Fetch GATS units of measure registry."""
        data = self._make_api_request("/api/gats/unitsOfMeasure")
        if not data:
            return pl.LazyFrame(schema={"unit_id": pl.Utf8, "unit_name": pl.Utf8})
        records = [
            {
                "unit_id": str(item.get("unitId", "")),
                "unit_name": item.get("unitName"),
            }
            for item in data
        ]
        return pl.LazyFrame(records)

    def get_gats_customs_districts(self) -> pl.LazyFrame:
        """Fetch GATS US Customs Districts for entry/exit points."""
        data = self._make_api_request("/api/gats/customsDistricts")
        if not data:
            return pl.LazyFrame(
                schema={"district_code": pl.Utf8, "district_name": pl.Utf8}
            )
        records = [
            {
                "district_code": str(item.get("districtCode", "")),
                "district_name": item.get("districtName"),
            }
            for item in data
        ]
        return pl.LazyFrame(records)

    # -------------------------------------------------------------------------
    # GATS Census Data (monthly, by partner)
    # -------------------------------------------------------------------------

    def _standardize_gats_census_columns(self, df: pl.DataFrame) -> pl.LazyFrame:
        """Standardize GATS Census column names from camelCase to snake_case.

        Note: The API returns 'country_code' for the trade partner, which we
        rename to 'partner_code' for semantic clarity in trade data context.
        """
        rename_map = {
            "partnerCode": "partner_code",
            "countryCode": "partner_code",  # API uses countryCode for partner
            "country_code": "partner_code",  # Sometimes already snake_case
            "commodityCode": "commodity_code",
            "hsCode": "hs_code",
            "hS10Code": "hs10_code",
            "censusUOMId1": "census_uom_id_1",
            "censusUOMId2": "census_uom_id_2",
            "fasConvertedUOMId": "fas_converted_uom_id",
            "fasNonConvertedUOMId": "fas_non_converted_uom_id",
            "quantity1": "quantity_1",
            "quantity2": "quantity_2",
            "year": "year",
            "month": "month",
            "value": "value",
            "quantity": "quantity",
            "unitId": "unit_id",
            "districtCode": "district_code",
        }
        existing_renames = {k: v for k, v in rename_map.items() if k in df.columns}
        return df.rename(existing_renames).lazy()

    def get_gats_census_imports(
        self, partner_code: str, year: int, month: int
    ) -> pl.LazyFrame:
        """Fetch GATS Census US import data for a partner, year, and month.

        Args:
            partner_code: Trading partner country code
            year: Calendar year
            month: Month number (1-12)

        Returns:
            LazyFrame with US import records from the partner
        """
        endpoint = f"/api/gats/censusImports/partnerCode/{partner_code}/year/{year}/month/{month}"
        data = self._make_api_request(endpoint)
        if not data:
            return pl.LazyFrame()
        df = pl.DataFrame(data)
        return self._standardize_gats_census_columns(df)

    def get_gats_census_exports(
        self, partner_code: str, year: int, month: int
    ) -> pl.LazyFrame:
        """Fetch GATS Census US export data for a partner, year, and month."""
        endpoint = f"/api/gats/censusExports/partnerCode/{partner_code}/year/{year}/month/{month}"
        data = self._make_api_request(endpoint)
        if not data:
            return pl.LazyFrame()
        df = pl.DataFrame(data)
        return self._standardize_gats_census_columns(df)

    def get_gats_census_reexports(
        self, partner_code: str, year: int, month: int
    ) -> pl.LazyFrame:
        """Fetch GATS Census US re-export data for a partner, year, and month."""
        endpoint = f"/api/gats/censusReExports/partnerCode/{partner_code}/year/{year}/month/{month}"
        data = self._make_api_request(endpoint)
        if not data:
            return pl.LazyFrame()
        df = pl.DataFrame(data)
        return self._standardize_gats_census_columns(df)

    # -------------------------------------------------------------------------
    # GATS UN Trade Data (annual, by reporter)
    # -------------------------------------------------------------------------

    def _standardize_gats_untrade_columns(self, df: pl.DataFrame) -> pl.LazyFrame:
        """Standardize GATS UN Trade column names from camelCase to snake_case."""
        rename_map = {
            "reporterCode": "reporter_code",
            "partnerCode": "partner_code",
            "countryCode": "country_code",
            "commodityCode": "commodity_code",
            "hs6Code": "hs6_code",
            "year": "year",
            "value": "value",
            "quantity": "quantity",
            "unitId": "unit_id",
        }
        existing_renames = {k: v for k, v in rename_map.items() if k in df.columns}
        return df.rename(existing_renames).lazy()

    def get_gats_untrade_imports(self, reporter_code: str, year: int) -> pl.LazyFrame:
        """Fetch GATS UN Trade import data for a reporter country and year.

        Args:
            reporter_code: Reporting country code (one of 140+ countries)
            year: Calendar year

        Returns:
            LazyFrame with import records for the reporter
        """
        endpoint = f"/api/gats/UNTradeImports/reporterCode/{reporter_code}/year/{year}"
        data = self._make_api_request(endpoint)
        if not data:
            return pl.LazyFrame()
        df = pl.DataFrame(data)
        return self._standardize_gats_untrade_columns(df)

    def get_gats_untrade_exports(self, reporter_code: str, year: int) -> pl.LazyFrame:
        """Fetch GATS UN Trade export data for a reporter country and year."""
        endpoint = f"/api/gats/UNTradeExports/reporterCode/{reporter_code}/year/{year}"
        data = self._make_api_request(endpoint)
        if not data:
            return pl.LazyFrame()
        df = pl.DataFrame(data)
        return self._standardize_gats_untrade_columns(df)

    def get_gats_untrade_reexports(self, reporter_code: str, year: int) -> pl.LazyFrame:
        """Fetch GATS UN Trade re-export data for a reporter country and year."""
        endpoint = (
            f"/api/gats/UNTradeReExports/reporterCode/{reporter_code}/year/{year}"
        )
        data = self._make_api_request(endpoint)
        if not data:
            return pl.LazyFrame()
        df = pl.DataFrame(data)
        return self._standardize_gats_untrade_columns(df)

    # -------------------------------------------------------------------------
    # GATS Data Release Dates (for sensors)
    # -------------------------------------------------------------------------

    def get_gats_census_imports_release_dates(self) -> pl.LazyFrame:
        """Fetch GATS Census imports release dates for change detection."""
        data = self._make_api_request("/api/gats/census/data/imports/dataReleaseDates")
        if not data:
            return pl.LazyFrame(
                schema={"partner_code": pl.Utf8, "release_date": pl.Utf8}
            )
        records = [
            {
                "partner_code": str(
                    item.get("partnerCode", item.get("countryCode", ""))
                ),
                "release_date": item.get("releaseDate"),
            }
            for item in data
        ]
        return pl.LazyFrame(records)

    def get_gats_census_exports_release_dates(self) -> pl.LazyFrame:
        """Fetch GATS Census exports release dates for change detection."""
        data = self._make_api_request("/api/gats/census/data/exports/dataReleaseDates")
        if not data:
            return pl.LazyFrame(
                schema={"partner_code": pl.Utf8, "release_date": pl.Utf8}
            )
        records = [
            {
                "partner_code": str(
                    item.get("partnerCode", item.get("countryCode", ""))
                ),
                "release_date": item.get("releaseDate"),
            }
            for item in data
        ]
        return pl.LazyFrame(records)

    def get_gats_census_reexports_release_dates(self) -> pl.LazyFrame:
        """Fetch GATS Census re-exports release dates for change detection."""
        data = self._make_api_request(
            "/api/gats/census/data/reexports/dataReleaseDates"
        )
        if not data:
            return pl.LazyFrame(
                schema={"partner_code": pl.Utf8, "release_date": pl.Utf8}
            )
        records = [
            {
                "partner_code": str(
                    item.get("partnerCode", item.get("countryCode", ""))
                ),
                "release_date": item.get("releaseDate"),
            }
            for item in data
        ]
        return pl.LazyFrame(records)

    def get_gats_untrade_imports_release_dates(self) -> pl.LazyFrame:
        """Fetch GATS UN Trade imports release dates for change detection."""
        data = self._make_api_request("/api/gats/UNTrade/data/imports/dataReleaseDates")
        if not data:
            return pl.LazyFrame(
                schema={"reporter_code": pl.Utf8, "release_date": pl.Utf8}
            )
        records = [
            {
                "reporter_code": str(
                    item.get("reporterCode", item.get("countryCode", ""))
                ),
                "release_date": item.get("releaseDate"),
            }
            for item in data
        ]
        return pl.LazyFrame(records)

    def get_gats_untrade_exports_release_dates(self) -> pl.LazyFrame:
        """Fetch GATS UN Trade exports release dates for change detection."""
        data = self._make_api_request("/api/gats/UNTrade/data/exports/dataReleaseDates")
        if not data:
            return pl.LazyFrame(
                schema={"reporter_code": pl.Utf8, "release_date": pl.Utf8}
            )
        records = [
            {
                "reporter_code": str(
                    item.get("reporterCode", item.get("countryCode", ""))
                ),
                "release_date": item.get("releaseDate"),
            }
            for item in data
        ]
        return pl.LazyFrame(records)


class EcbDataResource(dg.ConfigurableResource):
    """Resource for ECB Data Portal SDMX API.

    Provides access to ECB exchange rate data via the SDMX 2.1 REST API.
    No authentication required (public API).

    Attributes:
        rate_limit_delay: Delay between requests in seconds (default 0.1s)
    """

    rate_limit_delay: float = 0.1

    def _make_request(
        self,
        dataflow: str,
        key: str = "",
        start_period: str | None = None,
        end_period: str | None = None,
    ) -> pd.DataFrame:
        """Make request to ECB SDMX API."""
        url = f"{ECB_DATA_API_URL}/data/{dataflow}/{key}"
        params = {"format": "csvdata"}

        if start_period:
            params["startPeriod"] = start_period
        if end_period:
            params["endPeriod"] = end_period

        time.sleep(self.rate_limit_delay)
        response = requests.get(url, params=params, timeout=120)
        response.raise_for_status()

        # Parse CSV response
        import io

        df = pd.read_csv(io.StringIO(response.text))

        return df

    def get_exchange_rates(
        self,
        frequency: str = "D",
        currencies: list[str] | None = None,
        start_period: str | None = None,
        end_period: str | None = None,
    ) -> pd.DataFrame:
        """Fetch EUR exchange rates from ECB.

        Args:
            frequency: Data frequency ('D' = daily, 'M' = monthly)
            currencies: List of currency codes (e.g., ['USD', 'GBP'])
                       If None, fetches all available currencies
            start_period: Start date (YYYY-MM-DD format)
            end_period: End date (YYYY-MM-DD format)

        Returns:
            DataFrame with columns: date, currency, rate
        """
        # Build SDMX key: {frequency}.{currency}.EUR.SP00.A
        # Use wildcard for currency if not specified
        currency_key = "+".join(currencies) if currencies else ""

        key = f"{frequency}.{currency_key}.EUR.SP00.A"

        df = self._make_request("EXR", key, start_period, end_period)

        if df.empty:
            return pd.DataFrame(columns=["date", "currency", "rate"])

        # ECB CSV format has columns like: KEY, FREQ, CURRENCY, CURRENCY_DENOM, etc.
        # The actual rate is in OBS_VALUE and date in TIME_PERIOD
        result = []

        for _, row in df.iterrows():
            try:
                result.append({
                    "date": pd.to_datetime(row.get("TIME_PERIOD")),
                    "currency": row.get("CURRENCY"),
                    "rate": (
                        float(row.get("OBS_VALUE")) if row.get("OBS_VALUE") else None
                    ),
                })
            except (ValueError, TypeError):
                continue

        return pd.DataFrame(result)

    def get_data(
        self,
        dataflow: str,
        key: str = "",
        start_period: str | None = None,
        end_period: str | None = None,
    ) -> pd.DataFrame:
        """Generic SDMX data fetch."""
        return self._make_request(dataflow, key, start_period, end_period)


class PatentsViewResource(dg.ConfigurableResource):
    """Resource for downloading PatentsView bulk data.

    PatentsView provides free, research-ready bulk downloads of USPTO patent data
    with disambiguated assignee/inventor information. Data is released quarterly
    under CC BY 4.0 license.

    Attributes:
        base_url: PatentsView S3 download URL base
        cache_dir: Local cache directory for downloaded zips
        timeout: HTTP timeout in seconds for downloads
        cache_ttl_hours: Cache TTL in hours (default 24 hours, like SEC)
    """

    base_url: str = "https://s3.amazonaws.com/data.patentsview.org/download/"
    cache_dir: str = "_data/cache/patentsview"
    timeout: float = 600.0  # Large files need time
    cache_ttl_hours: int = 24

    # Tables available for download
    TABLES: ClassVar[list[str]] = [
        "g_patent",
        "g_assignee_disambiguated",
        "g_patent_abstract",
        "g_cpc_current",
        "g_cpc_title",
        "g_inventor_disambiguated",
        "g_us_patent_citation",
    ]

    def _get_cache_path(self, table_name: str) -> Path:
        """Get cache path for a table's zip file."""
        cache_dir = Path(self.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"{table_name}.tsv.zip"

    def download_table(
        self,
        table_name: str,
        force: bool = False,
        progress_callback: Callable[[str], None] | None = None,
    ) -> Path:
        """Download a PatentsView table (TSV in ZIP) to cache.

        Args:
            table_name: Name of table (e.g., 'g_patent', 'g_assignee_disambiguated')
            force: Force re-download even if cache is valid
            progress_callback: Optional callback(msg: str) for progress updates

        Returns:
            Path to cached zip file
        """
        cache_path = self._get_cache_path(table_name)

        # Check cache
        if not force and is_cache_valid(cache_path, self.cache_ttl_hours):
            if progress_callback:
                progress_callback(f"Using cached {table_name} ({cache_path})")
            return cache_path

        # Build URL and download
        url = f"{self.base_url}{table_name}.tsv.zip"

        # Stream download with progress
        with requests.get(url, stream=True, timeout=self.timeout) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            total_mb = total_size / (1024 * 1024)

            if progress_callback:
                progress_callback(
                    f"Starting download: {table_name} ({total_mb:.1f} MB)"
                )

            # Write to temp file first, then move to cache
            temp_path = cache_path.with_suffix(".tmp")
            downloaded = 0
            last_logged_pct = 0
            start_time = time.time()

            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=65536):  # 64KB chunks
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Log progress every 10%
                        if total_size > 0 and progress_callback:
                            pct = int((downloaded / total_size) * 100)
                            if pct >= last_logged_pct + 10:
                                elapsed = time.time() - start_time
                                speed_mbps = (
                                    (downloaded / (1024 * 1024)) / elapsed
                                    if elapsed > 0
                                    else 0
                                )
                                remaining_mb = (total_size - downloaded) / (1024 * 1024)
                                eta_sec = (
                                    remaining_mb / speed_mbps if speed_mbps > 0 else 0
                                )
                                progress_callback(
                                    f"{table_name}: {pct}% ({downloaded / (1024 * 1024):.1f}/{total_mb:.1f} MB) "
                                    f"@ {speed_mbps:.1f} MB/s, ETA: {eta_sec:.0f}s"
                                )
                                last_logged_pct = pct

            # Move temp to final location
            temp_path.rename(cache_path)

            if progress_callback:
                elapsed = time.time() - start_time
                speed_mbps = total_mb / elapsed if elapsed > 0 else 0
                progress_callback(
                    f"{table_name}: Complete ({total_mb:.1f} MB in {elapsed:.1f}s @ {speed_mbps:.1f} MB/s)"
                )

        return cache_path

    def list_tables(self) -> list[str]:
        """List all available tables for download."""
        return self.TABLES.copy()


# =============================================================================
# BLS BULK DOWNLOAD RESOURCE
# =============================================================================

# BLS FTP base URL
BLS_FTP_BASE_URL = "https://download.bls.gov/pub/time.series"

# Dataset directory mappings
BLS_DATASETS = {
    "cpi": "cu",  # CPI-U (Consumer Price Index - All Urban Consumers)
    "labor_force": "ln",  # Labor Force Statistics
    "employment": "ce",  # Current Employment Statistics
    "jolts": "jt",  # Job Openings and Labor Turnover Survey
}

# Files to download for each dataset
BLS_DATASET_FILES = {
    "cpi": [
        "cu.data.0.Current",  # Recent data (faster to parse)
        "cu.data.1.AllItems",  # Full history
        "cu.series",  # Series metadata
        "cu.area",  # Area dimension
        "cu.item",  # Item dimension
        "cu.period",  # Period codes
        "cu.periodicity",  # Periodicity codes
        "cu.seasonal",  # Seasonal adjustment codes
        "cu.base",  # Base period codes
    ],
    "labor_force": [
        "ln.data.1.AllData",  # All data
        "ln.series",  # Series metadata
        "ln.area",  # Area dimension
        "ln.lfst",  # Labor force status
        "ln.ages",  # Age groups
        "ln.sexs",  # Sex codes
        "ln.race",  # Race codes
        "ln.orig",  # Hispanic origin
        "ln.pcts",  # Percent/level codes
        "ln.seasonal",  # Seasonal adjustment
    ],
    "employment": [
        "ce.data.0.AllCESSeries",  # All data
        "ce.series",  # Series metadata
        "ce.supersector",  # Supersector dimension
        "ce.industry",  # Industry dimension
        "ce.datatype",  # Data type codes
        "ce.seasonal",  # Seasonal adjustment
    ],
    "jolts": [
        "jt.data.1.AllItems",  # All data
        "jt.series",  # Series metadata
        "jt.area",  # Area dimension
        "jt.industry",  # Industry dimension
        "jt.state",  # State dimension
        "jt.sizeclass",  # Size class
        "jt.dataelement",  # Data element (JO, HI, QU, etc.)
        "jt.ratelevel",  # Rate vs level
        "jt.seasonal",  # Seasonal adjustment
    ],
}


class BlsBulkResource(dg.ConfigurableResource):
    """Resource for downloading BLS bulk flat files from FTP.

    BLS requires User-Agent header with contact info per their policy.
    Uses local cache with configurable TTL to avoid redundant downloads.

    Attributes:
        user_agent: Contact info for BLS (e.g., "YourName your@email.com")
        cache_dir: Local cache directory (default: ~/.cache/bls)
        cache_ttl_hours: Cache TTL in hours (default: 24)
        rate_limit_delay: Delay between requests in seconds (default: 1.0)
        timeout: HTTP timeout in seconds (default: 300)
    """

    user_agent: str
    cache_dir: str = "~/.cache/bls"
    cache_ttl_hours: int = 24
    rate_limit_delay: float = 1.0
    timeout: float = 300.0

    def _get_cache_dir(self, dataset: str) -> Path:
        """Get cache directory for a dataset."""
        cache_root = Path(self.cache_dir).expanduser()
        dataset_dir = cache_root / BLS_DATASETS.get(dataset, dataset)
        dataset_dir.mkdir(parents=True, exist_ok=True)
        return dataset_dir

    def _get_headers(self) -> dict:
        """Get HTTP headers for BLS requests."""
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/plain, */*",
        }

    def get_remote_last_modified(
        self, dataset: str, filename: str
    ) -> dt.datetime | None:
        """Check Last-Modified header for a BLS file (for sensor use).

        Args:
            dataset: Dataset name (cpi, labor_force, employment, jolts)
            filename: Specific file to check (e.g., 'cu.data.0.Current')

        Returns:
            Last-Modified datetime if available, None otherwise
        """
        directory = BLS_DATASETS.get(dataset, dataset)
        url = f"{BLS_FTP_BASE_URL}/{directory}/{filename}"

        try:
            response = requests.head(url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()

            last_modified_str = response.headers.get("Last-Modified")
            if last_modified_str:
                # Parse RFC 2822 format: "Wed, 10 Sep 2025 12:00:00 GMT"
                return dt.datetime.strptime(
                    last_modified_str, "%a, %d %b %Y %H:%M:%S %Z"
                )
        except (requests.RequestException, ValueError):
            pass

        return None

    def download_file(
        self,
        dataset: str,
        filename: str,
        force: bool = False,
    ) -> Path:
        """Download a single BLS file to cache.

        Args:
            dataset: Dataset name (cpi, labor_force, employment, jolts)
            filename: File to download (e.g., 'cu.data.0.Current')
            force: Force re-download even if cache is valid

        Returns:
            Path to cached file
        """
        directory = BLS_DATASETS.get(dataset, dataset)
        cache_dir = self._get_cache_dir(dataset)
        cache_path = cache_dir / filename

        # Check cache
        if not force and is_cache_valid(cache_path, self.cache_ttl_hours):
            return cache_path

        # Download
        url = f"{BLS_FTP_BASE_URL}/{directory}/{filename}"
        time.sleep(self.rate_limit_delay)

        response = requests.get(
            url,
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()

        # Write to cache
        cache_path.write_bytes(response.content)
        return cache_path

    def download_dataset(
        self,
        dataset: str,
        force: bool = False,
        progress_callback: Callable[[str], None] | None = None,
    ) -> dict[str, Path]:
        """Download all files for a BLS dataset to cache.

        Args:
            dataset: Dataset name (cpi, labor_force, employment, jolts)
            force: Force re-download even if cache is valid
            progress_callback: Optional callback for progress updates

        Returns:
            Dict mapping filename to cached path
        """
        files = BLS_DATASET_FILES.get(dataset, [])
        if not files:
            raise ValueError(f"Unknown BLS dataset: {dataset}")

        results = {}
        for i, filename in enumerate(files, 1):
            if progress_callback:
                progress_callback(f"Downloading {filename} ({i}/{len(files)})...")

            try:
                path = self.download_file(dataset, filename, force=force)
                results[filename] = path
            except requests.HTTPError as e:
                if progress_callback:
                    progress_callback(f"Warning: Failed to download {filename}: {e}")
                # Continue with other files

        return results

    def list_datasets(self) -> list[str]:
        """List available BLS datasets."""
        return list(BLS_DATASETS.keys())

    def list_dataset_files(self, dataset: str) -> list[str]:
        """List files for a specific dataset."""
        return BLS_DATASET_FILES.get(dataset, [])
