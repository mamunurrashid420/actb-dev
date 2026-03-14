# Data Pipeline Architecture

> **Status**: Active - Phase 1 complete

This document describes the Dagster-based data pipeline architecture for external data ingestion and transformation.

## Current Implementation

The pipeline is operational in `pipelines/` with:

- **Medallion Architecture**: Bronze (raw) → Silver (cleaned) → Gold (semantic) layers
- **Partition-Based Design**: Single-dimension partitions (country codes, tickers)
- **Four Data Sources**: FRED, BLS, World Bank, SEC EDGAR
- **Reference Layer**: Crosswalk-based routing from semantic to source-native IDs

## Key Architectural Constraints

1. Medallion architecture with flexible DAG transformations
2. Partition-based versioning for time-series data
3. Source-native IDs for raw, semantic namespaces for LLM access
4. Fail-fast validation - data quality is non-negotiable

## Detailed Documentation

See `pipelines/docs/` for comprehensive documentation:

- [ASSET_ARCHITECTURE.md](../pipelines/docs/ASSET_ARCHITECTURE.md) - Dagster asset patterns
- [TESTING_STRATEGY.md](../pipelines/docs/TESTING_STRATEGY.md) - Testing approach
- [OPERATIONS.md](../pipelines/docs/OPERATIONS.md) - Running the pipeline

## References

- [MONOREPO_ROADMAP.md](../MONOREPO_ROADMAP.md) - Migration phases
- [pipelines/AI_INSTRUCTIONS.md](../pipelines/AI_INSTRUCTIONS.md) - Agent reference for pipeline code
