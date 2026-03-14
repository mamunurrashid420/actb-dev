# Understanding the Asset Architecture

**Note:** This document explains WHY our architecture works the way it does. For quick reference during coding, see `CLAUDE.md`.

## The Problem We Solved

When we started building the pipeline, we faced a critical question: **How do we organize hundreds of economic indicators across dozens of countries without creating thousands of individual assets?**

Consider these scenarios:
- FRED provides 800,000+ economic series - we can't create an asset for each one
- World Bank tracks 1,400+ indicators across 200+ countries - that's 280,000 combinations
- SEC filings: 5,000+ public companies × 5 form types × multiple years

### The Naive Approach (What We Avoided)

```python
# ❌ DON'T: This doesn't scale
@dg.asset
def gdp_usa():
    return fetch_from_fred('GDP')

@dg.asset
def gdp_china():
    return fetch_from_world_bank('CHN', 'NY.GDP.MKTP.CD')

@dg.asset
def gdp_japan():
    return fetch_from_world_bank('JPN', 'NY.GDP.MKTP.CD')
# ... 197 more GDP assets?!

@dg.asset
def unemployment_usa():
    return fetch_from_fred('UNRATE')
# ... another 200 for unemployment?!

@dg.asset
def cpi_usa():
    return fetch_from_fred('CPIAUCSL')
# ... you get the idea
```

**This leads to:**
- ❌ Thousands of nearly-identical asset definitions
- ❌ Copy-paste bugs when fixing issues
- ❌ No way to add new countries without code changes
- ❌ Cluttered asset graph (impossible to navigate in UI)
- ❌ Difficult to apply uniform transformations
- ❌ No systematic way to handle missing data

## Our Solution: Partition-Based Architecture

**Key Insight:** If multiple pieces of data have the **same structure** and require the **same processing logic**, they should be **partitions of one asset**, not separate assets.

### Example: FRED Economic Data

Instead of 5 separate assets, we have **1 asset with 5 partitions**:

```python
# ✅ DO: One asset, multiple partitions
@dg.asset(
    key_prefix=['fred', 'raw'],
    name='timeseries',
    partitions_def=dg.StaticPartitionsDefinition(['GDP', 'UNRATE', 'CPIAUCSL', 'PCE', 'FEDFUNDS'])
)
def fred_timeseries(context):
    series_id = context.partition_key  # 'GDP', 'UNRATE', etc.

    # Same fetch logic for all series
    data = fred_api.get_series(series_id)

    # Same processing for all series (all have date, value columns)
    return pd.DataFrame({'date': data.index, 'value': data.values})
    # Saves to: fred/raw/timeseries/GDP.parquet
    #           fred/raw/timeseries/UNRATE.parquet
    #           fred/raw/timeseries/CPIAUCSL.parquet
```

**What this gives us:**
- ✅ Add new series by updating a list, not writing new code
- ✅ Fix bugs once, applies to all series
- ✅ Materialize all partitions together or individually
- ✅ Clean asset graph: 1 node instead of 100+
- ✅ Systematic error handling
- ✅ Uniform metadata structure

### Visual Comparison

**Before (Individual Assets):**
```
Asset Graph:
  gdp_usa ─┐
  gdp_china ┤
  gdp_japan ┤
  gdp_germany ┤
  gdp_uk ───┤
  ... 195 more ─┴─→ (cluttered, hard to navigate)
```

**After (Partitioned Assets):**
```
Asset Graph:
  fred/raw/timeseries ─→ [GDP, UNRATE, CPIAUCSL, PCE, FEDFUNDS]
       ↑
   Single node, clean graph, 5 partitions materialized independently
```

## The Two-Layer Strategy

But we have another challenge: **Sources use their own identifiers, but users think in semantic terms.**

### The User Experience Problem

Users want to ask questions like:
- "What's unemployment in France?"
- "How does inflation in Japan compare to the US?"
- "Show me GDP for Germany"

But APIs use source-specific codes:
- FRED uses: `'UNRATE'`, `'GDP'`, `'CPIAUCSL'`
- World Bank uses: `'SL.UEM.TOTL.ZS'`, `'NY.GDP.MKTP.CD'`
- Users think in: countries ('France', 'Japan', 'US'), not API codes

### Solution: Source-Native → Semantic Layers

We create **two parallel partition systems**:

1. **Source Layer (Raw Nodes)**: Use source-native identifiers
2. **Semantic Layer (Leaf Nodes)**: Use user-friendly identifiers
3. **Reference Assets**: Map between them

```
┌─────────────────────────────────────────┐
│  User Query: "Unemployment in France?"  │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│  SEMANTIC LAYER (Leaf Nodes)            │
│                                          │
│  Asset: economic/labor_market/unemployment
│  Partition: 'FR' (2-letter country)     │
│  User-friendly, LLM-accessible          │
└────────────────┬────────────────────────┘
                 │
         ┌───────┴───────┐
         │  CROSSWALK    │
         │  ROUTING      │ Maps: 'FR' + 'unemployment'
         │               │   → World Bank: 'FRA' + 'SL.UEM.TOTL.ZS'
         └───────┬───────┘
                 │
┌────────────────▼────────────────────────┐
│  SOURCE LAYER (Raw Nodes)                │
│                                          │
│  Asset: world_bank/raw/timeseries        │
│  Partition: 'FRA|SL.UEM.TOTL.ZS'        │
│  Source-native IDs, API-specific        │
└──────────────────────────────────────────┘
```

### Why This Matters

**1. Source Independence**

We can switch data providers without changing published assets:

```python
# Published asset doesn't care about the source
@dg.asset(partitions_def=semantic_countries)
def unemployment(context):
    country = context.partition_key  # 'US'

    # Intelligent routing based on data availability
    if country == 'US':
        return load_from_fred('UNRATE')  # Best quality for US
    else:
        return load_from_world_bank(f'{country_3letter}|SL.UEM.TOTL.ZS')
```

**2. Intelligent Fallback**

Different countries have data in different sources:

```python
# Try primary source first, fall back if missing
df = try_fred(country, 'unemployment_rate')
if df is None:
    df = try_world_bank(country, 'unemployment_rate')
if df is None:
    df = try_bls(country, 'unemployment_rate')
```

**3. User-Friendly Queries**

LLMs and users work with familiar concepts:
- Countries: 'US', 'FR', 'JP' (not 'USA', 'FRA', 'JPN')
- Indicators: 'unemployment', 'gdp', 'inflation' (not 'SL.UEM.TOTL.ZS', 'NY.GDP.MKTP.CD')

## Multi-Dimensional Partitions

Some data naturally has multiple dimensions. World Bank data is partitioned by **BOTH** country **AND** indicator:

### The Challenge

World Bank provides:
- 20 countries we care about
- 8 indicators per country
- = 160 different data combinations

All combinations have the **same structure** (date, value) and require the **same processing**.

### Solution: Multi-Dimensional Partitions

```python
@dg.asset(
    partitions_def=dg.MultiPartitionsDefinition({
        'country': ['USA', 'CHN', 'JPN', 'DEU', 'GBR', ...],  # 20 countries
        'indicator': ['NY.GDP.MKTP.CD', 'SL.UEM.TOTL.ZS', ...]  # 8 indicators
    })
)
def worldbank_timeseries(context):
    partition_key = context.partition_key  # "USA|NY.GDP.MKTP.CD"
    country, indicator = partition_key.split('|')

    # Fetch this specific country-indicator combo
    return world_bank_api.get_indicator(indicator, [country])

    # Saves to: world_bank/raw/timeseries/USA_NY.GDP.MKTP.CD.parquet
```

**Partition Key Syntax:**
- In code: `"USA|NY.GDP.MKTP.CD"` (pipe separator)
- In files: `USA_NY.GDP.MKTP.CD.parquet` (underscore separator)
- IO manager handles the conversion

**Benefits:**
- ✅ All 160 combinations defined in one asset
- ✅ Add new countries: append to country list
- ✅ Add new indicators: append to indicator list
- ✅ Materialize specific combinations: `--partition "USA|NY.GDP.MKTP.CD"`
- ✅ Materialize all: 160 partitions execute in parallel

## The AllPartitionMapping Pattern

Here's where it gets interesting. **Published assets don't know which source partition they need until runtime.**

### The Problem

A published asset for unemployment in France needs:
- Semantic partition: `'FR'` (2-letter code)
- Source partition: `'FRA|SL.UEM.TOTL.ZS'` (3-letter + indicator code)

**There's no automatic 1:1 mapping.** We need intelligent routing.

### The Solution: Load All, Select at Runtime

```python
@dg.asset(
    partitions_def=semantic_countries,  # ['US', 'CN', 'JP', 'FR', ...]
    deps=[
        dg.AssetDep(
            dg.AssetKey(['fred', 'raw', 'timeseries']),
            partition_mapping=dg.AllPartitionMapping()  # Load ALL FRED partitions
        ),
        dg.AssetDep(
            dg.AssetKey(['world_bank', 'raw', 'timeseries']),
            partition_mapping=dg.AllPartitionMapping()  # Load ALL World Bank partitions
        ),
    ]
)
def unemployment(context):
    country = context.partition_key  # 'FR'

    # At runtime, select the right source partition
    if country == 'US':
        # Use FRED partition: 'UNRATE'
        df = load_fred_partition('UNRATE')
    else:
        # Use World Bank partition: 'FRA|SL.UEM.TOTL.ZS'
        country_3letter = COUNTRY_CODE_MAP[country]  # 'FR' → 'FRA'
        df = load_worldbank_partition(f'{country_3letter}|SL.UEM.TOTL.ZS')

    return df
```

**Why AllPartitionMapping?**

Without it, Dagster would try to do 1:1 partition mapping:
- Published partition `'FR'` → Look for source partition `'FR'`
- But source has `'FRA|SL.UEM.TOTL.ZS'` → **Mapping fails!**

By loading ALL source partitions, we can:
1. ✅ Look up the correct source partition at runtime
2. ✅ Implement fallback logic (try FRED, fall back to World Bank)
3. ✅ Choose best data source per country
4. ✅ Handle missing data gracefully

**The Trade-off:**

This loads more data into memory during execution, but:
- ✅ We only have hundreds of partitions, not millions
- ✅ Parquet files are small and load quickly
- ✅ The flexibility is worth the memory cost
- ✅ Enables sophisticated routing logic

**If we had millions of partitions**, we'd use a different approach (database lookups, external metadata store). But for our scale, this is optimal.

## When to Use Partitions vs. Individual Assets

**Use Partitions When:**
- ✅ Data has the same structure (same columns/schema)
- ✅ Same processing logic applies to all instances
- ✅ Instances are logically related (same concept, different values)
- ✅ You want to materialize instances independently
- ✅ You expect to add more instances over time

**Use Individual Assets When:**
- ✅ Data structures are fundamentally different
- ✅ Processing logic varies significantly
- ✅ Instances represent different concepts
- ✅ Dependencies between instances are complex
- ✅ Each instance has unique configuration

**Example:**

```python
# ✅ GOOD: Partitions for similar data
@dg.asset(partitions_def=['GDP', 'UNRATE', 'CPIAUCSL'])
def fred_timeseries(context):
    # All series have: date, value columns
    # All use: same fetch logic
    # All require: same transformations
    series_id = context.partition_key
    return fetch_and_process(series_id)

# ✅ GOOD: Separate assets for different concepts
@dg.asset
def company_registry():
    # Returns: CIK → ticker → name mapping
    # Structure: Different from timeseries
    # Purpose: Reference data, not timeseries

@dg.asset
def indicator_crosswalk():
    # Returns: semantic_name → source_id mapping
    # Structure: Different from timeseries
    # Purpose: Routing table, not data

@dg.asset
def fred_timeseries():
    # Returns: timeseries with partitions
    # Structure: date, value columns
    # Purpose: Actual data
```

## The Flexible DAG

Our assets form a **dependency graph** (DAG = Directed Acyclic Graph):

```
Source Nodes → (Optional Transforms) → Leaf Nodes
```

**Source Nodes** (Raw Data):
- No dependencies
- Fetch from APIs
- Use source-native partitions
- Marked as `visibility: internal`

**Leaf Nodes** (Published Data):
- Depend on sources (and optional intermediates)
- Use semantic partitions
- Optimized for LLM queries
- Marked as `visibility: llm_accessible`

**Intermediate Nodes** (Optional):
- We currently transform directly from source to leaf
- Could add: validation, enrichment, aggregation
- Number of transformation steps is completely flexible

**Current Pipeline:**

```
fred/raw/timeseries (partitioned by series_id)
    ↓ (direct transform)
economic/labor_market/unemployment (partitioned by country)

world_bank/raw/timeseries (partitioned by country|indicator)
    ↓ (direct transform)
economic/labor_market/unemployment (partitioned by country)
```

**If we needed complexity, we could add:**

```
fred/raw/timeseries
    ↓
fred/validated/timeseries (add: validation)
    ↓
fred/normalized/timeseries (add: normalization)
    ↓
economic/labor_market/unemployment
```

**Use the minimum transformations needed.** Don't add complexity until it's required.

## Why This Architecture Matters

**1. Scalability**
- Add new countries/series by updating lists
- No code changes for new instances
- Scales from 10 to 10,000 partitions

**2. Maintainability**
- Fix bugs once, applies to all partitions
- Uniform error handling
- Consistent metadata structure

**3. LLM-Ready**
- Semantic layer optimized for natural language
- Clean partition naming (`'US'`, `'FR'` not `'USA'`, `'FRA'`)
- Metadata includes `questions_answered` for discovery

**4. Source Independence**
- Can switch providers without breaking published layer
- Intelligent routing per country/indicator
- Fallback logic built-in

**5. Clear Separation**
- Raw data uses source IDs (technical)
- Published data uses semantic names (user-friendly)
- Reference assets manage the mapping

**6. Operational Control**
- Materialize all partitions or just one
- Monitor success/failure per partition
- Retry individual partitions on failure
- Schedule different sources independently

## Evolution: How We Got Here

**Version 1 (Naive):**
- Individual assets per series
- Realized: doesn't scale

**Version 2 (Basic Partitions):**
- Partitioned by series ID
- Realized: users don't know series IDs

**Version 3 (Two Layers):**
- Source layer: partitioned by source IDs
- Published layer: partitioned by semantic names
- Realized: need routing between layers

**Version 4 (Current):**
- Source layer: source-native partitions
- Reference assets: crosswalk routing
- Published layer: semantic partitions + AllPartitionMapping
- Result: Scalable, maintainable, user-friendly ✅

## Next Steps for Understanding

1. **Read the code**: See `src/pipelines/assets/` for actual implementations
2. **Check partitions**: Look at `src/pipelines/partitions.py` for all partition definitions
3. **Explore UI**: Start Dagster UI and browse the asset graph
4. **Materialize an asset**: Try `dg asset materialize --select "fred/raw/timeseries" --partition "GDP"`
5. **Read detailed docs**: See `docs/ASSET_ARCHITECTURE.md` for comprehensive patterns

## Questions This Design Answers

**Q: Why not one asset per country per indicator?**
A: Would create 160+ assets for World Bank alone. Doesn't scale. Same structure = use partitions.

**Q: Why two partition layers (source and semantic)?**
A: Sources use their own IDs. Users think in semantic terms. We need both + routing.

**Q: Why AllPartitionMapping instead of 1:1?**
A: No automatic mapping from `'FR'` to `'FRA|SL.UEM.TOTL.ZS'`. Need runtime routing logic.

**Q: What if we have millions of partitions?**
A: Then AllPartitionMapping won't work (too much memory). Would use database lookups instead. But we have hundreds, not millions.

**Q: Why not just use a relational database?**
A: Dagster assets provide: dependency tracking, retry logic, observability, scheduling, metadata. We use Parquet for storage efficiency.

**Q: Can I add intermediate transformation nodes?**
A: Yes! Add as needed between source and leaf. Keep it minimal until required.

**Q: How do I add a new country?**
A: Add to partition lists in `partitions.py`. No code changes needed.

This architecture lets us start with 4 sources and scale to dozens without refactoring.
