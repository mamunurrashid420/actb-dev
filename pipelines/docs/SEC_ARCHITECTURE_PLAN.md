# Plan: SEC Data Architecture - Bulk Downloads + Time-Based Partitions

## Overview

Refactor SEC assets to use **bulk downloads** for financial data and filing metadata, with time-based partitions for narrative text and transaction data. This minimizes API requests while providing complete SEC coverage.

## Key Design Decisions

1. **Bulk downloads for structured data** (MAJOR OPTIMIZATION):
   - `companyfacts.zip` (~3 GB) → All XBRL financials for all companies (pre-parsed JSON)
   - `submissions.zip` (~1 GB) → All filing metadata (index of what filings exist)
   - Only fetch individual files for: narrative text (HTML) and Form 4/13-F (XML)
2. **Registry for CIK↔ticker mapping and filtering**:
   - Bronze: `sec_filer_registry` from `company_tickers.json` (complete mapping)
   - Silver: `company_registry` filtered to config-enabled tickers
   - Gold layer joins with registry to add ticker column
3. **Time-based partitions**:
   - 10-K text: **Yearly** (2020, 2021, 2022, ...) - ~50 filings/year for enabled companies
   - 10-Q text: **Quarterly** (2020-Q1, 2020-Q2, ...) - ~150 filings/year for enabled companies
   - Form 4: **Monthly** (2020-01, 2020-02, ...) - high volume ~100K/year
   - 13-F: **Quarterly** (2020-Q1, 2020-Q2, ...)
4. **Bronze uses CIK** (source-native ID), not ticker
5. **Bronze stores parsed data** - metadata + financials + narrative text (NOT raw HTML)
6. **Gold layer unpartitioned**: Single DataFrame indexed by (ticker, time), filtered by registry
7. **Historical depth configurable**: Start year in config (default: 2020)
8. **Parallel development**: Separate files per form type enable multi-agent implementation

## API Request Optimization

| Data Type | Source | Requests |
|-----------|--------|----------|
| All XBRL financials | companyfacts.zip | 1 bulk download |
| Filing metadata | submissions.zip | 1 bulk download |
| CIK↔ticker mapping | company_tickers.json | 1 request |
| 10-K/10-Q narrative text | Individual HTML | ~200/year (enabled companies) |
| Form 4 transactions | Individual XML | ~8,000+/month (all) |
| 13-F holdings | Individual XML | ~1,000/quarter (enabled institutions) |

The bulk files are updated daily by SEC and contain:
- **companyfacts.zip**: Pre-parsed XBRL data in JSON format (no py-xbrl needed!)
- **submissions.zip**: Complete filing index and metadata for all companies

## Parsing Tools

| Form | Financials | Narrative Text | Transactions |
|------|------------|----------------|--------------|
| 10-K | **company_facts** (pre-parsed) | **sec-parser** (semantic tree) | N/A |
| 10-Q | **company_facts** (pre-parsed) | **sec-parser** | N/A |
| Form 4 | N/A | N/A | **lxml** (simple XML) |
| 13-F | N/A | N/A | **lxml** (simple XML) |

## Architecture

```
BRONZE LAYER (bulk downloads + time-partitioned)
├── bronze/sec/sec_filer_registry        ← company_tickers.json (CIK↔ticker mapping)
├── bronze/sec/company_facts             ← companyfacts.zip (~3 GB, unpartitioned)
│   └── All XBRL financials for all companies (revenue, net_income, assets, etc.)
├── bronze/sec/submissions               ← submissions.zip (~1 GB, unpartitioned)
│   └── All filing metadata: accession_number, form_type, filing_date, etc.
├── bronze/sec/form_10k_text[year]       ← Individual HTML fetches, yearly partitions
│   └── Columns: cik, accession_number, sections (JSON: risk_factors, mda, business)
├── bronze/sec/form_10q_text[quarter]    ← Individual HTML fetches, quarterly partitions
│   └── Similar structure with quarterly sections
├── bronze/sec/form_4[month]             ← Individual XML fetches, monthly partitions
│   └── Columns: cik, insider_cik, insider_name, transaction_date, shares, price, ...
└── bronze/sec/form_13f[quarter]         ← Individual XML fetches, quarterly partitions
    └── Columns: institution_cik, cusip, issuer_name, shares, value, ...

SILVER LAYER (transformed, enriched)
├── silver/sec/company_registry          ← Filtered to config-enabled tickers (from sec_filer_registry)
├── silver/sec/institution_registry      ← Filtered to config-enabled institutions
├── silver/sec/form_10k_financials       ← Validated, calculated ratios (from company_facts)
├── silver/sec/form_10k_sections         ← Cleaned narrative text (from form_10k_text)
├── silver/sec/form_10q_financials
├── silver/sec/form_4_transactions       ← Aggregated insider activity
└── silver/sec/form_13f_holdings         ← Position changes, portfolio analysis

GOLD LAYER (unpartitioned, filtered by registry)
├── gold/companies/annual_reports        ← All 10-K data for enabled companies (joined with ticker)
├── gold/companies/quarterly_reports     ← All 10-Q data for enabled companies
├── gold/companies/insider_activity      ← All Form 4 data for enabled companies
└── gold/institutions/holdings           ← All 13-F data for enabled institutions
```

## Data Flow

```
SEC EDGAR Bulk Files + API
        ↓
bronze/sec/sec_filer_registry  ← company_tickers.json (CIK↔ticker mapping)
bronze/sec/company_facts       ← companyfacts.zip (all XBRL financials, pre-parsed)
bronze/sec/submissions         ← submissions.zip (filing index/metadata)
        ↓
        ↓ (Filter and transform)
        ↓
silver/sec/company_registry     ← Filtered to config-enabled tickers
silver/sec/form_10k_financials  ← Extract 10-K financials, validate, calculate ratios
silver/sec/form_10q_financials  ← Extract 10-Q financials

SEC EDGAR API (individual fetches, using submissions for accession_numbers)
        ↓
bronze/sec/form_10k_text[2024]  ← HTML for enabled companies
bronze/sec/form_4[2024-01]      ← XML for Form 4 transactions
bronze/sec/form_13f[2024-Q1]    ← XML for 13-F holdings
        ↓
    sec-parser / lxml parsing
        ↓
silver/sec/form_10k_sections    ← Cleaned narrative text by section
silver/sec/form_4_transactions  ← Aggregated insider activity
silver/sec/form_13f_holdings    ← Position changes

silver/* assets + company_registry
        ↓
        ↓ (Join with registry to add ticker, filter to enabled companies)
        ↓
gold/companies/annual_reports   ← Join financials + sections + registry
        ↓
Query: df.query("ticker == 'AAPL'")
```

---

## Implementation Phases

### Phase 0: File Restructuring (FIRST - enables parallel work)

**Goal**: Split `sec.py` into multiple files for parallel development.

```
pipelines/src/pipelines/assets/
├── sec.py                    ← DELETE (after migration)
└── sec/                      ← NEW directory
    ├── __init__.py           ← Export all assets
    ├── common.py             ← Shared utilities, schemas, constants
    ├── registry.py           ← sec_filer_registry (bronze), company/institution_registry (silver)
    ├── bulk_downloads.py     ← company_facts, submissions (bronze bulk downloads)
    ├── form_10k.py           ← 10-K text + financials (silver/gold)
    ├── form_10q.py           ← 10-Q text + financials (silver/gold)
    ├── form_4.py             ← Form 4 bronze, silver, gold assets
    └── form_13f.py           ← 13-F bronze, silver, gold assets
```

**Steps:**
1. Create `assets/sec/` directory
2. Create `common.py` with shared utilities
3. Create `registry.py` with registry assets
4. Create `bulk_downloads.py` with company_facts and submissions assets
5. Move/rewrite each form type to its own file
6. Update `definitions.py` imports
7. Delete old `sec.py`

**Parallel Development Strategy:**
Once Phase 0 is complete, form files can be developed in parallel using multiple agents:
- Agent 1: `bulk_downloads.py` + `form_10k.py`
- Agent 2: `form_10q.py`
- Agent 3: `form_4.py`
- Agent 4: `form_13f.py`

---

### Phase 1: Registry Assets + SecApiResource

**1.1 Add SecApiResource for SEC API access**
- File: `pipelines/src/pipelines/resources.py`
- **Bulk download methods** (daily updates, cached locally):
  - `download_company_facts()` → Extract companyfacts.zip (~3 GB)
  - `download_submissions()` → Extract submissions.zip (~1 GB)
- **Individual fetch methods** (rate-limited):
  - `fetch_company_tickers()` → DataFrame from `company_tickers.json`
  - `fetch_filing_content(cik, accession_number, filename)` → Raw HTML/XML for parsing
- Rate limiting: 10 req/sec (SEC requirement)
- User-Agent header required

**Bulk file URLs:**
- `https://www.sec.gov/Archives/edgar/daily-index/bulkdata/companyfacts.zip`
- `https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip`

**1.2 Create registry.py** (`assets/sec/registry.py`)

```python
# BRONZE: Fetch SEC's complete registry
@dg.asset(key_prefix=['bronze', 'sec'], name='sec_filer_registry')
def sec_filer_registry(sec_api: SecApiResource) -> pd.DataFrame:
    """Fetch SEC's complete CIK↔ticker mapping."""
    # https://www.sec.gov/files/company_tickers.json
    return sec_api.fetch_company_tickers()

# SILVER: Filter to companies we care about
@dg.asset(key_prefix=['silver', 'sec'], name='company_registry')
def company_registry(bronze_sec_sec_filer_registry: pd.DataFrame) -> pd.DataFrame:
    """Filter SEC registry to config-enabled tickers."""
    enabled = get_enabled_tickers()  # From config
    return bronze_sec_sec_filer_registry.query("ticker in @enabled")

# SILVER: Filter to institutions we care about
@dg.asset(key_prefix=['silver', 'sec'], name='institution_registry')
def institution_registry(bronze_sec_sec_filer_registry: pd.DataFrame) -> pd.DataFrame:
    """Filter SEC registry to config-enabled institutions."""
    enabled = get_enabled_institutions()  # From config
    return bronze_sec_sec_filer_registry.query("cik in @enabled")
```

**1.3 Create bulk_downloads.py** (`assets/sec/bulk_downloads.py`)

```python
# BRONZE: Download and extract companyfacts.zip
@dg.asset(key_prefix=['bronze', 'sec'], name='company_facts')
def company_facts(sec_api: SecApiResource) -> pd.DataFrame:
    """Download SEC's bulk company facts (all XBRL financials).

    Source: companyfacts.zip (~3 GB, updated daily)
    Contains pre-parsed XBRL data in JSON format for all companies.
    """
    facts_dir = sec_api.download_company_facts()  # Returns extracted directory
    return parse_company_facts(facts_dir)  # Convert to DataFrame

# BRONZE: Download and extract submissions.zip
@dg.asset(key_prefix=['bronze', 'sec'], name='submissions')
def submissions(sec_api: SecApiResource) -> pd.DataFrame:
    """Download SEC's bulk submissions metadata.

    Source: submissions.zip (~1 GB, updated daily)
    Contains filing index for all companies (accession numbers, dates, form types).
    """
    submissions_dir = sec_api.download_submissions()  # Returns extracted directory
    return parse_submissions(submissions_dir)  # Convert to DataFrame
```

---

### Phase 2: Partition Infrastructure

**2.1 Add time-based partition definitions**
- File: `pipelines/src/pipelines/partitions.py`

```python
# Form-specific partitions
sec_yearly_partitions = StaticPartitionsDefinition(
    generate_years(start=2020)  # ['2020', '2021', '2022', '2023', '2024']
)

sec_quarterly_partitions = StaticPartitionsDefinition(
    generate_quarters(start_year=2020)  # ['2020-Q1', ..., '2024-Q4']
)

sec_monthly_partitions = StaticPartitionsDefinition(
    generate_months(start_year=2020)  # ['2020-01', ..., '2024-12']
)
```

**2.2 Update config schema**
- File: `pipelines/config/sec_filings.yaml`

```yaml
start_year: 2020
enabled_tickers: [AAPL, MSFT, SBUX, MCD]
enabled_institutions: [0001067983, 0001364742]  # Berkshire, Bridgewater
```

---

### Phase 3: Bronze Layer (Narrative Text + Transaction Data)

**Note:** Financial data comes from bulk downloads (company_facts, Phase 1).
This phase covers time-partitioned assets that require individual API fetches.

**3.1 Form 10-K Text Bronze** (`assets/sec/form_10k.py`)
- Partition: **Yearly** (2020, 2021, ...)
- Depends on: `bronze/sec/submissions` (for accession numbers)
- Fetches: Individual HTML files for enabled companies only
- Parses: sec-parser (narrative sections)
- Stores: Parsed sections JSON (NOT raw HTML)

```python
@dg.asset(
    key_prefix=['bronze', 'sec'],
    name='form_10k_text',
    partitions_def=sec_yearly_partitions,
)
def bronze_form_10k_text(
    context,
    sec_api: SecApiResource,
    bronze_sec_submissions: pd.DataFrame,
    silver_sec_company_registry: pd.DataFrame,
) -> pd.DataFrame:
    year = context.partition_key  # "2024"

    # Filter submissions to 10-Ks for enabled companies in this year
    enabled_ciks = set(silver_sec_company_registry['cik'])
    filings = (
        bronze_sec_submissions
        .query("form_type == '10-K' and filing_year == @year")
        .query("cik in @enabled_ciks")
    )

    # Fetch and parse only the narrative sections (not financials)
    results = []
    for filing in filings.itertuples():
        html = sec_api.fetch_filing_content(
            cik=filing.cik,
            accession_number=filing.accession_number,
            filename=filing.primary_document,
        )

        # Parse narrative sections (sec-parser)
        sections = parse_narrative_sections(html)

        results.append({
            'cik': filing.cik,
            'accession_number': filing.accession_number,
            'filing_date': filing.filing_date,
            # Parsed sections (JSON blob)
            'sections': json.dumps({
                'business': sections.get('item_1'),
                'risk_factors': sections.get('item_1a'),
                'mda': sections.get('item_7'),
            })
        })

    return pd.DataFrame(results)
```

**3.2 Form 10-Q Text Bronze** (`assets/sec/form_10q.py`)
- Partition: **Quarterly** (2020-Q1, 2020-Q2, ...)
- Similar structure to 10-K text

**3.3 Form 4 Bronze** (`assets/sec/form_4.py`)
- Partition: **Monthly** (2020-01, 2020-02, ...)
- Depends on: `bronze/sec/submissions` (for accession numbers)
- Fetches: Individual XML files
- Parses: lxml (simple XML structure)
- High volume: ~8,000+ filings/month

```python
@dg.asset(
    key_prefix=['bronze', 'sec'],
    name='form_4',
    partitions_def=sec_monthly_partitions,
)
def bronze_form_4(
    context,
    sec_api: SecApiResource,
    bronze_sec_submissions: pd.DataFrame,
) -> pd.DataFrame:
    month = context.partition_key  # "2024-11"

    # Filter submissions to Form 4s in this month
    filings = (
        bronze_sec_submissions
        .query("form_type == '4' and filing_month == @month")
    )

    results = []
    for filing in filings.itertuples():
        xml = sec_api.fetch_filing_content(
            cik=filing.cik,
            accession_number=filing.accession_number,
            filename=filing.primary_document,
        )
        transactions = parse_form4_xml(xml)  # lxml parsing
        results.extend(transactions)

    return pd.DataFrame(results)
```

**3.4 Form 13-F Bronze** (`assets/sec/form_13f.py`)
- Partition: **Quarterly** (2020-Q1, 2020-Q2, ...)
- Depends on: `bronze/sec/submissions`, `silver/sec/institution_registry`
- Fetches: Individual XML files for enabled institutions only
- Parses: lxml (XML information table)

**3.5 Incremental logic for current period**
```python
def is_current_period(partition_key, granularity):
    """Check if this is the current (mutable) period."""
    # Historical periods are immutable - fetch once
    # Current period may have new filings - check for updates
    ...

# In bronze asset:
if is_current_period(partition_key, 'monthly'):
    existing = try_load_existing(context)
    if existing is not None:
        new_filings = filter_new_filings(bronze_sec_submissions, existing)
        # Only fetch HTML/XML for truly new filings
        ...
```

---

### Phase 4: Silver Layer (Transformation)

**4.1 Financial validation and enrichment** (`assets/sec/form_10k.py`)
- Source: `bronze/sec/company_facts` (pre-parsed XBRL from bulk download)
- Filter to 10-K data, validate schema (Pandera)
- Calculate derived metrics (ratios, YoY growth)
- Handle missing/null values

```python
@dg.asset(key_prefix=['silver', 'sec'], name='form_10k_financials')
def form_10k_financials(
    bronze_sec_company_facts: pd.DataFrame,
    silver_sec_company_registry: pd.DataFrame,
) -> pd.DataFrame:
    """Extract and validate 10-K financials from bulk company facts."""
    enabled_ciks = set(silver_sec_company_registry['cik'])
    return (
        bronze_sec_company_facts
        .query("form_type == '10-K' and cik in @enabled_ciks")
        .pipe(validate_financial_schema)
        .pipe(calculate_financial_ratios)
    )
```

**4.2 Section text cleaning** (`assets/sec/form_10k.py`)
- Source: `bronze/sec/form_10k_text` (partitioned by year)
- Clean extracted narrative text
- Normalize whitespace, remove artifacts
- Prepare for downstream chunking (FUTURE)

**4.3 Transaction aggregation (Form 4)** (`assets/sec/form_4.py`)
- Source: `bronze/sec/form_4` (partitioned by month)
- Aggregate by insider, company, time period
- Calculate net buys/sells

**4.4 Holdings analysis (13-F)** (`assets/sec/form_13f.py`)
- Source: `bronze/sec/form_13f` (partitioned by quarter)
- Calculate position changes quarter-over-quarter
- Portfolio concentration metrics

---

### Phase 5: Gold Layer (Unpartitioned)

**5.1 Pattern for gold assets**
```python
@dg.asset(
    key_prefix=['gold', 'companies', 'financials'],
    name='annual_reports',
    ins={
        'all_10k': dg.AssetIn(
            key=['silver', 'sec', 'form_10k_financials'],
            partition_mapping=dg.AllPartitionsMapping(),
        ),
        'company_registry': dg.AssetIn(key=['silver', 'sec', 'company_registry']),
    },
)
def annual_reports(
    all_10k: dict[str, pd.DataFrame],
    company_registry: pd.DataFrame,
) -> pd.DataFrame:
    """Combine all years, filter to enabled companies."""
    combined = pd.concat(all_10k.values(), ignore_index=True)

    return (
        combined
        .merge(company_registry[['cik', 'ticker']], on='cik', how='inner')
        .sort_values(['ticker', 'fiscal_year'])
    )
```

---

### Phase 6: Asset Checks (Simplified)

**6.1 Time-based checks (replace company completeness)**
```python
@dg.asset_check(asset=['bronze', 'sec', 'form_10k'])
def check_bronze_form_10k(context) -> dg.AssetCheckResult:
    """Check that expected years have data."""
    expected = generate_years(SEC_START_YEAR, current_year())
    missing = [y for y in expected if not partition_exists(context, y)]

    return dg.AssetCheckResult(
        passed=len(missing) == 0,
        metadata={'missing_years': missing}
    )
```

**6.2 Gold layer checks**
```python
@dg.asset_check(asset=['gold', 'companies', 'financials', 'annual_reports'])
def check_gold_annual_reports(context) -> dg.AssetCheckResult:
    """Check that enabled companies have data."""
    df = load_asset(context)
    registry = load_asset(context, 'company_registry')

    missing = set(registry['ticker']) - set(df['ticker'])
    return dg.AssetCheckResult(
        passed=len(missing) == 0,
        metadata={'missing_tickers': list(missing)}
    )
```

---

### Phase 7: Jobs and Schedules

**7.1 Jobs**
```python
# Current period refresh (incremental)
sec_form4_daily_refresh    # Form 4 current month
sec_10k_weekly_refresh     # 10-K current year
sec_10q_weekly_refresh     # 10-Q current quarter
sec_13f_weekly_refresh     # 13-F current quarter

# Gold layer refresh
sec_gold_refresh           # All gold assets

# Backfill (historical)
sec_full_backfill          # All forms, all periods
```

**7.2 Schedules**
```python
daily_form4_refresh        # 6am daily → Form 4 current month + gold
weekly_sec_refresh         # Mon 2am → 10-K, 10-Q, 13-F current periods + gold
```

---

### Phase 8: Tests

- `tests/test_assets/test_sec/test_form_10k.py`
- `tests/test_assets/test_sec/test_form_10q.py`
- `tests/test_assets/test_sec/test_form_4.py`
- `tests/test_assets/test_sec/test_form_13f.py`
- `tests/test_checks.py` - Time-based check tests

---

## Files to Modify/Create

| File | Action |
|------|--------|
| `src/pipelines/assets/sec/` | **CREATE** directory |
| `src/pipelines/assets/sec/__init__.py` | **CREATE** exports |
| `src/pipelines/assets/sec/common.py` | **CREATE** shared utilities, parsing functions |
| `src/pipelines/assets/sec/registry.py` | **CREATE** sec_filer_registry (bronze), company/institution_registry (silver) |
| `src/pipelines/assets/sec/bulk_downloads.py` | **CREATE** company_facts, submissions (bronze bulk downloads) |
| `src/pipelines/assets/sec/form_10k.py` | **CREATE** 10-K text (bronze), financials+sections (silver), annual_reports (gold) |
| `src/pipelines/assets/sec/form_10q.py` | **CREATE** 10-Q text (bronze), financials (silver), quarterly_reports (gold) |
| `src/pipelines/assets/sec/form_4.py` | **CREATE** Form 4 (bronze), transactions (silver), insider_activity (gold) |
| `src/pipelines/assets/sec/form_13f.py` | **CREATE** 13-F (bronze), holdings (silver), holdings (gold) |
| `src/pipelines/assets/sec.py` | **DELETE** after migration |
| `src/pipelines/resources.py` | **MODIFY** add SecApiResource with bulk download + individual fetch methods |
| `src/pipelines/partitions.py` | **MODIFY** add time partitions, remove company partitions |
| `src/pipelines/checks.py` | **MODIFY** replace company checks with time checks |
| `src/pipelines/jobs.py` | **MODIFY** update SEC jobs |
| `src/pipelines/schedules.py` | **MODIFY** update SEC schedules |
| `src/pipelines/definitions.py` | **MODIFY** register new assets |
| `config/sec_filings.yaml` | **MODIFY** simplify config |
| `tests/test_assets/test_sec/` | **CREATE** test directory |

---

## Benefits

1. **Massive API request reduction** - 2 bulk downloads + ~200 HTML instead of 10,000+ requests
2. **Pre-parsed XBRL data** - No py-xbrl parsing needed, SEC provides JSON format
3. **Matches SEC data organization** - SEC indices are time-based
4. **No raw HTML storage** - Parse on fetch, store structured data only
5. **Simpler CIK handling** - SEC registry is source of truth
6. **Easy company additions** - Just update config, rematerialize gold
7. **Better asset checks** - Time completeness, not company completeness
8. **Parallel development** - Separate files per form type
9. **Form-appropriate granularity** - Monthly for high-volume Form 4

---

## Future Work (Not In Scope)

### RAG Chunking Strategy
When ready to build RAG on SEC filings:

**Recommended approach:**
- **Hierarchical chunking** with semantic awareness
- **Chunk size**: 1000-1500 tokens (sentence-aware)
- **Preserve hierarchy**: Item > Subheading > Paragraph in metadata
- **Tables**: LLM-summarize rather than embed raw HTML

**Key sections for RAG:**
- Item 1A: Risk Factors (highest signal, naturally organized)
- Item 7: MD&A (rich financial narrative)
- Item 1: Business (company overview)

**Tools:**
- sec-parser for semantic tree structure
- LlamaIndex/LangChain for orchestration
- Chroma/Pinecone for vector storage

**Reference implementations:**
- [run-llama/sec-insights](https://github.com/run-llama/sec-insights)
- [Kay + Cybersyn + LangChain](https://blog.langchain.dev/kay-x-cybersyn-x-langchain/)
