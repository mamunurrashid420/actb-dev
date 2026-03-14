# Data Documentation

*Generated: 2026-01-22 18:59*

Auto-generated documentation for the actBI data pipeline.

## Summary

| Layer | Count |
|-------|-------|
| 🥇 Gold | 18 |
| 🥈 Silver | 24 |
| 🥉 Bronze | 68 |
| **Total** | **110** |

## Documentation Files

- [DATA_INVENTORY.md](DATA_INVENTORY.md) - Complete asset inventory by layer
- [LINEAGE.md](LINEAGE.md) - Asset dependency relationships
- [SCHEDULES.md](SCHEDULES.md) - Automated refresh schedules (21 schedules)

## Medallion Architecture

### 🥇 Gold Layer
Published, semantic assets ready for consumption. Use friendly partitions
(country codes, tickers) and route to appropriate bronze sources.

### 🥈 Silver Layer
Reference data (crosswalks, registries) and transformed/validated data.
Maps semantic identifiers to source-native IDs.

### 🥉 Bronze Layer
Raw data from external APIs. Partitioned by source-native identifiers
(series IDs, CIKs, indicator codes).