# Jobs Reference

This guide documents all available jobs in the actBI pipeline and how to execute them.

## Prerequisites

All commands run from the `pipelines/` directory using `uv run dagster`:

```bash
cd pipelines
```

## Available Jobs

### SEC Filing Jobs

| Job | Description | Partitions |
|-----|-------------|------------|
| `sec_bulk_downloads_refresh` | Download submissions.zip + companyfacts.zip | None |
| `sec_registry_refresh` | Refresh filer registry and filtered registries | None |
| `sec_10k_refresh` | Refresh 10-K annual reports (bronze → silver) | Yearly (2020-2025) |
| `sec_10q_refresh` | Refresh 10-Q quarterly reports (bronze → silver) | Quarterly (2020-Q1 to 2025-Q4) |
| `sec_form4_refresh` | Refresh Form 4 insider trading (bronze → silver) | Monthly (2020-01 to 2025-12) |
| `sec_13f_refresh` | Refresh 13-F institutional holdings (bronze → silver) | Quarterly (2020-Q1 to 2025-Q4) |
| `sec_financials_refresh` | Extract financials from bulk company facts | None |
| `sec_gold_refresh` | Refresh all SEC gold layer assets | None |

### Agriculture Jobs

| Job | Description | Partitions |
|-----|-------------|------------|
| `nasa_power_raw_refresh` | Fetch NASA POWER weather data | Location |
| `agriculture_indicators_refresh` | Refresh agriculture indicators | Location |
| `agriculture_full_pipeline` | Complete agriculture pipeline | Location |
| `brazil_coffee_refresh` | Brazil coffee regions only | Location |

## Executing Jobs

### Unpartitioned Jobs

For jobs without partitions, use `job execute`:

```bash
# SEC foundation data
uv run dagster job execute -j sec_bulk_downloads_refresh
uv run dagster job execute -j sec_registry_refresh

# SEC derived data
uv run dagster job execute -j sec_financials_refresh
uv run dagster job execute -j sec_gold_refresh
```

### Partitioned Jobs - Single Partition

For jobs with partitions, use `asset materialize` with `--partition`:

```bash
# 10-K for 2024 only
uv run dagster asset materialize \
  --select "bronze/sec/form_10k_text,silver/sec/form_10k_sections" \
  --partition "2024"

# 10-Q for Q4 2024
uv run dagster asset materialize \
  --select "bronze/sec/form_10q_text,silver/sec/form_10q_sections" \
  --partition "2024-Q4"

# Form 4 for December 2024
uv run dagster asset materialize \
  --select "bronze/sec/form_4,silver/sec/form_4_transactions" \
  --partition "2024-12"

# 13-F for Q4 2024
uv run dagster asset materialize \
  --select "bronze/sec/form_13f,silver/sec/form_13f_holdings" \
  --partition "2024-Q4"
```

### Partitioned Jobs - All Partitions (Backfill)

To backfill all partitions, use `job execute` without partition specification:

```bash
# All 10-K years (2020-2025)
uv run dagster job execute -j sec_10k_refresh

# All 10-Q quarters (2020-Q1 to 2025-Q4)
uv run dagster job execute -j sec_10q_refresh

# All Form 4 months (2020-01 to 2025-12)
uv run dagster job execute -j sec_form4_refresh

# All 13-F quarters (2020-Q1 to 2025-Q4)
uv run dagster job execute -j sec_13f_refresh
```

### Partition Ranges

To materialize a range of partitions:

```bash
# 10-K for 2022-2024
uv run dagster asset materialize \
  --select "bronze/sec/form_10k_text,silver/sec/form_10k_sections" \
  --partition-range "2022...2024"

# 10-Q for 2024 (all quarters)
uv run dagster asset materialize \
  --select "bronze/sec/form_10q_text,silver/sec/form_10q_sections" \
  --partition-range "2024-Q1...2024-Q4"
```

## Common Workflows

### Initial SEC Data Setup

Run in this order:

```bash
# 1. Download bulk data (large, run first)
uv run dagster job execute -j sec_bulk_downloads_refresh

# 2. Build registries
uv run dagster job execute -j sec_registry_refresh

# 3. Fetch form data (pick specific partitions or backfill all)
uv run dagster asset materialize \
  --select "bronze/sec/form_10k_text,silver/sec/form_10k_sections" \
  --partition "2024"

# 4. Extract financials
uv run dagster job execute -j sec_financials_refresh

# 5. Build gold layer
uv run dagster job execute -j sec_gold_refresh
```

### Weekly SEC Refresh

```bash
# Current year 10-K
uv run dagster asset materialize \
  --select "bronze/sec/form_10k_text,silver/sec/form_10k_sections" \
  --partition "2024"

# Current quarter 10-Q and 13-F
uv run dagster asset materialize \
  --select "bronze/sec/form_10q_text,silver/sec/form_10q_sections" \
  --partition "2024-Q4"

uv run dagster asset materialize \
  --select "bronze/sec/form_13f,silver/sec/form_13f_holdings" \
  --partition "2024-Q4"

# Refresh gold layer
uv run dagster job execute -j sec_gold_refresh
```

### Daily Form 4 Refresh

```bash
# Current month insider trading
uv run dagster asset materialize \
  --select "bronze/sec/form_4,silver/sec/form_4_transactions" \
  --partition "2024-12"

# Update gold layer
uv run dagster job execute -j sec_gold_refresh
```

## Partition Reference

### SEC Yearly Partitions (10-K)
`2020`, `2021`, `2022`, `2023`, `2024`, `2025`

### SEC Quarterly Partitions (10-Q, 13-F)
`2020-Q1`, `2020-Q2`, `2020-Q3`, `2020-Q4`, ... `2025-Q4`

### SEC Monthly Partitions (Form 4)
`2020-01`, `2020-02`, ... `2025-12`

## Listing Jobs

```bash
# List all jobs
uv run dagster job list

# List assets in a job
uv run dagster job list -j sec_10k_refresh
```

## Troubleshooting

### "No module named 'pipelines'"
Run from the `pipelines/` directory.

### Job hangs or takes too long
Bulk downloads are large. Use the Dagster UI to monitor progress:
```bash
uv run dagster dev
```

### Partition not found
Check valid partition keys in `src/pipelines/partitions.py`.
