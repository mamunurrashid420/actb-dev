# Data Inventory

*Generated: 2026-01-22 18:59*

## 🥇 Gold Layer (Published/Semantic)

Ready-to-use data with semantic partitions (country codes, tickers).

| Asset | Source | Partitions | Description |
|-------|--------|------------|-------------|
| `gold/agriculture/weather/daily` | agriculture_indicators | brazil_minas_gerais, brazil_sao_paulo, ... (8 total) | Daily agricultural weather conditions for coffee-growing ... |
| `gold/agriculture/weather/monthly` | agriculture_indicators | brazil_minas_gerais, brazil_sao_paulo, ... (8 total) | Monthly agricultural weather aggregates for coffee-growin... |
| `gold/climate/precipitation/total` | climate_indicators | New_York, Los_Angeles, ... (10 total) | Precipitation totals from NOAA daily weather data |
| `gold/climate/temperature/average` | climate_indicators | New_York, Los_Angeles, ... (10 total) | Average temperature from NOAA daily weather data |
| `gold/companies/financials/annual_reports` | sec_filings | - | LLM-ready annual reports combining all years, filtered by... |
| `gold/companies/financials/quarterly_reports` | sec_filings | - | LLM-ready quarterly reports combining all quarters, filte... |
| `gold/companies/insider/insider_activity` | sec_filings | - | LLM-ready insider activity combining all months, filtered... |
| `gold/economic/fiscal/government_debt` | fiscal_indicators | USA, DEU, ... (14 total) | Government debt as % of GDP |
| `gold/economic/growth/gdp` | country_indicators | USA, CHN, ... (20 total) | GDP from FRED (USA) or World Bank (other countries) |
| `gold/economic/labor_market/job_openings` | country_indicators | USA, CHN, ... (20 total) | JOLTS job openings (US only) |
| `gold/economic/labor_market/unemployment` | country_indicators | USA, CHN, ... (20 total) | Unemployment rate from FRED (USA) or World Bank (other co... |
| `gold/economic/monetary/interest_rate` | monetary_indicators | USA, CHN, ... (13 total) | Interest rate from FRED (USA) or World Bank (other countr... |
| `gold/economic/prices/inflation` | country_indicators | USA, CHN, ... (20 total) | Inflation rate (CPI) from FRED (USA) or World Bank (other... |
| `gold/economic/trade/balance` | country_indicators | USA, CHN, ... (20 total) | Trade balance (current account balance as % of GDP) |
| `gold/institutions/portfolio/holdings` | sec_filings | - | LLM-ready institutional holdings combining all quarters, ... |
| `gold/sec/company_profiles` | sec_filings | - | Company profiles with ticker enrichment and human-readabl... |
| `gold/sec/financials` | sec_filings | - | SEC financial data with ticker/label enrichment. Enriches... |
| `gold/sec/segments` | sec_filings | - | Segment financials with ticker enrichment and normalized ... |

## 🥈 Silver Layer (Reference/Transformed)

Crosswalks, registries, and validated/transformed data.

| Asset | Source | Partitions | Description |
|-------|--------|------------|-------------|
| `silver/bea/nipa_data` | bea | - | Merged NIPA data (historical + current year) |
| `silver/reference/indicator_id_crosswalk` | reference | - | Master mapping from source series IDs to indicator slugs |
| `silver/reference/nasa_power_location_registry` | nasa_power | - | Mapping of agricultural location IDs to coordinates and m... |
| `silver/reference/nasa_power_variable_crosswalk` | nasa_power | - | Mapping of semantic variable names to NASA POWER paramete... |
| `silver/reference/noaa_locations` | noaa | - | Mapping of countries/cities to primary NOAA stations |
| `silver/reference/noaa_stations` | noaa | - | Mapping of NOAA station IDs to locations and metadata |
| `silver/reference/noaa_variables` | noaa | - | Mapping of semantic variable names to NOAA data type codes |
| `silver/sec/company_facts` | sec_edgar | - | StreamingParquetSource wrapping the batch iterator. IO ma... |
| `silver/sec/company_registry` | sec_filings | - | Filter SEC registry to config-enabled tickers. Filters th... |
| `silver/sec/form_10k_financials` | sec_filings | - | Extract 10-K financials from bulk company facts for ALL c... |
| `silver/sec/form_10k_sections` | sec_filings | 2020, 2021, ... (6 total) | Clean and normalize 10-K narrative sections. |
| `silver/sec/form_10q_financials` | sec_filings | - | Extract 10-Q financials from bulk company facts for ALL c... |
| `silver/sec/form_10q_sections` | sec_filings | 2020-Q1, 2020-Q2, ... (24 total) | Clean and normalize 10-Q narrative sections. |
| `silver/sec/form_13f_holdings` | sec_filings | 2020-Q1, 2020-Q2, ... (24 total) | Merge bulk and API 13-F sources, clean, and enrich with p... |
| `silver/sec/form_4_transactions` | sec_filings | 2020-01, 2020-02, ... (72 total) | Clean and validate Form 4 transaction data. |
| `silver/sec/fsds_company_metadata` | sec_edgar | 2009-Q1, 2009-Q2, ... (68 total) | FSDS company metadata (SIC, filer status, WKSI) |
| `silver/sec/fsds_financials` | sec_edgar | 2009-Q1, 2009-Q2, ... (68 total) | FSDS consolidated financials with statement classification |
| `silver/sec/fsds_footnotes` | sec_edgar | 2009-Q1, 2009-Q2, ... (68 total) | FSDS value footnotes for LLM context |
| `silver/sec/fsds_segments` | sec_edgar | 2009-Q1, 2009-Q2, ... (68 total) | FSDS segment financials with parsed axis/member columns |
| `silver/sec/fsds_subsidiaries` | sec_edgar | 2009-Q1, 2009-Q2, ... (68 total) | FSDS co-registrant/subsidiary financials |
| `silver/sec/institution_registry` | sec_filings | - | Filter SEC registry to config-enabled institutions. Filte... |
| `silver/sec/xbrl_taxonomy` | fasb | - | Parse XBRL taxonomy XML to structured parquet. Parses the... |
| `silver/usda/esr_data` | usda_fas | - | Aggregated export data with computed metrics |
| `silver/usda/gats_census_data` | usda_fas | - | Aggregated Census trade data (imports, exports, re-exports) |

## 🥉 Bronze Layer (Raw)

Raw data from external APIs with source-native partitions.

| Asset | Source | Partitions | Description |
|-------|--------|------------|-------------|
| `bronze/bea/nipa_bulk` | bea | - | Complete NIPA bulk data from flat files |
| `bronze/bea/nipa_current` | bea | - | Current year NIPA data via API |
| `bronze/bls/all_series` | bureau_of_labor_statistics | - | All BLS timeseries data in a single asset (API-based) |
| `bronze/bls/cpi` | bureau_of_labor_statistics | - | Consumer Price Index (CPI-U) - denormalized time series |
| `bronze/bls/cpi_download` | bureau_of_labor_statistics | - | Download checkpoint for BLS Consumer Price Index (CPI-U) |
| `bronze/bls/employment` | bureau_of_labor_statistics | - | Current Employment Statistics (CES) - denormalized time s... |
| `bronze/bls/employment_download` | bureau_of_labor_statistics | - | Download checkpoint for BLS Current Employment Statistics |
| `bronze/bls/jolts` | bureau_of_labor_statistics | - | Job Openings and Labor Turnover Survey (JOLTS) - denormal... |
| `bronze/bls/jolts_download` | bureau_of_labor_statistics | - | Download checkpoint for BLS Job Openings and Labor Turnov... |
| `bronze/bls/labor_force` | bureau_of_labor_statistics | - | Labor Force Statistics - denormalized time series |
| `bronze/bls/labor_force_download` | bureau_of_labor_statistics | - | Download checkpoint for BLS Labor Force Statistics |
| `bronze/ecb/exchange_rates` | ecb | - | Fetch all EUR exchange rates from ECB. Source: ECB SDMX A... |
| `bronze/fred/series` | federal_reserve | - | FRED timeseries data for top N series by popularity |
| `bronze/fred/series_registry` | federal_reserve | - | FRED series metadata ordered by popularity |
| `bronze/nasa_power/daily` | nasa_power | brazil_minas_gerais, brazil_sao_paulo, ... (8 total) | Daily agricultural weather from NASA POWER API |
| `bronze/nasa_power/monthly` | nasa_power | brazil_minas_gerais, brazil_sao_paulo, ... (8 total) | Monthly agricultural weather from NASA POWER API |
| `bronze/noaa/annual` | noaa | dynamic:noaa_stations | Annual weather summaries from NOAA GSOY dataset |
| `bronze/noaa/daily` | noaa | dynamic:noaa_stations | Daily weather observations from NOAA GHCN-Daily dataset |
| `bronze/noaa/monthly` | noaa | dynamic:noaa_stations | Monthly weather summaries from NOAA GSOM dataset |
| `bronze/patents/abstracts` | patentsview | - | Parse g_patent_abstract table (9.3M rows) from downloaded... |
| `bronze/patents/abstracts_download` | patentsview | - | Download g_patent_abstract.tsv.zip (~1.6 GB) and return m... |
| `bronze/patents/assignees` | patentsview | - | Parse g_assignee_disambiguated table (8.6M rows) from dow... |
| `bronze/patents/assignees_download` | patentsview | - | Download g_assignee_disambiguated.tsv.zip (~342 MB) and r... |
| `bronze/patents/citations` | patentsview | - | Parse g_us_patent_citation table (151M rows) with streami... |
| `bronze/patents/citations_download` | patentsview | - | Download g_us_patent_citation.tsv.zip (~2.1 GB) and retur... |
| `bronze/patents/cpc_current` | patentsview | - | Parse g_cpc_current table (57.9M rows) with streaming sha... |
| `bronze/patents/cpc_current_download` | patentsview | - | Download g_cpc_current.tsv.zip (~472 MB) and return metad... |
| `bronze/patents/cpc_titles` | patentsview | - | Parse g_cpc_title table (269K rows) from downloaded zip. |
| `bronze/patents/cpc_titles_download` | patentsview | - | Download g_cpc_title.tsv.zip (~6 MB) and return metadata. |
| `bronze/patents/inventors` | patentsview | - | Parse g_inventor_disambiguated table (23.7M rows) from do... |
| `bronze/patents/inventors_download` | patentsview | - | Download g_inventor_disambiguated.tsv.zip (~666 MB) and r... |
| `bronze/patents/patents` | patentsview | - | Parse g_patent table (9.3M rows) from downloaded zip. |
| `bronze/patents/patents_download` | patentsview | - | Download g_patent.tsv.zip (~219 MB) and return metadata. |
| `bronze/sec/company_facts_download` | sec_edgar | - | DataFrame with zip metadata (path, file count, download t... |
| `bronze/sec/form_10k_text` | sec_edgar | 2020, 2021, ... (6 total) | Fetch 10-K narrative text for ALL enabled companies in a ... |
| `bronze/sec/form_10q_text` | sec_edgar | 2020-Q1, 2020-Q2, ... (24 total) | Fetch 10-Q narrative text for ALL enabled companies in a ... |
| `bronze/sec/form_13f` | sec_edgar | 2020-Q1, 2020-Q2, ... (24 total) | Fetch 13-F holdings for ALL enabled institutions in a giv... |
| `bronze/sec/form_13f_bulk` | sec_dera | 2020-Q1, 2020-Q2, ... (24 total) | Fetch 13-F holdings from DERA bulk dataset for a quarter.... |
| `bronze/sec/form_4` | sec_edgar | 2020-01, 2020-02, ... (72 total) | Fetch Form 4 insider transactions for ALL enabled compani... |
| `bronze/sec/fsds` | sec_edgar | 2009-Q1, 2009-Q2, ... (68 total) | SEC Financial Statement Data Sets with segment data |
| `bronze/sec/sec_filer_registry` | sec_edgar | - | DataFrame with columns: cik, ticker, company_name |
| `bronze/sec/submissions` | sec_edgar | - | DataFrame with columns: - cik: Zero-padded CIK (10 chars)... |
| `bronze/sec/submissions_download` | sec_edgar | - | DataFrame with zip metadata (path, file count, download t... |
| `bronze/sec/xbrl_taxonomy_raw` | fasb | - | Download raw FASB XBRL taxonomy XML files. Downloads two ... |
| `bronze/usda/commodities` | usda | - | Extract USDA commodity registry from bulk data. Source: D... |
| `bronze/usda/countries` | usda | - | Extract USDA country registry from bulk data. Source: Der... |
| `bronze/usda/esr_commodities` | usda_fas | - | ESR commodity reference data |
| `bronze/usda/esr_countries` | usda_fas | - | ESR country reference data with region codes |
| `bronze/usda/esr_exports` | usda_fas | 1990, 1991, ... (36 total) | Weekly US export sales data by market year |
| `bronze/usda/esr_regions` | usda_fas | - | ESR region reference data |
| `bronze/usda/esr_units` | usda_fas | - | ESR units of measure reference data |
| `bronze/usda/gats_census_exports` | usda_fas | 2024-12, 2025-01, ... (12 total) | US Census export data by month |
| `bronze/usda/gats_census_imports` | usda_fas | 2024-12, 2025-01, ... (12 total) | US Census import data by month |
| `bronze/usda/gats_census_reexports` | usda_fas | 2024-12, 2025-01, ... (12 total) | US Census re-export data by month |
| `bronze/usda/gats_commodities` | usda_fas | - | GATS commodity reference data (HS10 level) |
| `bronze/usda/gats_countries` | usda_fas | - | GATS country reference data |
| `bronze/usda/gats_customs_districts` | usda_fas | - | GATS US Customs Districts for entry/exit points |
| `bronze/usda/gats_hs6_commodities` | usda_fas | - | GATS HS6-level commodity registry |
| `bronze/usda/gats_regions` | usda_fas | - | GATS region reference data |
| `bronze/usda/gats_units` | usda_fas | - | GATS units of measure reference data |
| `bronze/usda/gats_untrade_exports` | usda_fas | - | UN Trade export data for major trading countries |
| `bronze/usda/gats_untrade_imports` | usda_fas | - | UN Trade import data for major trading countries |
| `bronze/usda/gats_untrade_reexports` | usda_fas | - | UN Trade re-export data for major trading countries |
| `bronze/usda/psd_bulk` | usda | - | Download complete PSD bulk data (all years except current... |
| `bronze/usda/psd_current` | usda | - | Fetch recent PSD data via API (rolling window). Source: U... |
| `bronze/world_bank/timeseries` | world_bank | USA, CHN, ... (20 total) | World Bank timeseries data partitioned by country (all in... |
| `silver/ecb/exchange_rates` | ecb | - | Enrich exchange rates with computed metrics. Computed met... |
| `silver/usda/psd_data` | usda | - | Merge bulk + current PSD data, compute derived metrics. M... |
