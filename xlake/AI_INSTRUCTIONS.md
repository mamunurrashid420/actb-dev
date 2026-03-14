# XLake - AI Reference

**For detailed explanations, see xlake/README.md (human docs)**

## Scope

- Provide a semantic layer over physical data stores
- Offer unified APIs for discovery and querying
- Maintain multi-tenant isolation and consistent semantics across connectors

## Directory Structure

```
src/xlake/
  core/         # Graph model, entities, context objects
  stores/       # Store abstractions and concrete store implementations
  connectors/   # DB connectors (e.g., Postgres, BigQuery)
  api/          # Public API surface (thin, stable)
```

## Conventions

- Abbreviated imports where applicable
- Type hints on all functions and public classes
- Concise, single-line docstrings preferred
- Resource-based dependency injection for connectors/stores


