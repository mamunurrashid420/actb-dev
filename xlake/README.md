# XLake

XLake is the semantic layer and unified data access API for the actBI server monorepo. It provides a logical graph over physical storage, unified context stores, and consistent APIs for querying and discovery.

## Status

Phase 2 of the monorepo roadmap. This repository contains the initial project scaffold following our monorepo conventions.

## Architecture

See `docs/ARCHITECTURE.md` for an overview. For the broader plan, refer to `../docs/XLake-Store-Architecture.md`.

## Project Structure

```
xlake/
├── src/xlake/
│   ├── core/           # Graph model, context building, entities
│   ├── stores/         # Store abstractions and implementations
│   ├── connectors/     # Database connectors
│   └── api/            # Unified XLake API surface
└── tests/              # Pytest-based tests
```

## Development

### Prerequisites

**Important**: Before building or running tests, you must compile the protobuf definitions:

```bash
cd xlake
python scripts/compile_protos.py
```

This generates the Python code from `.proto` files in `src/xlake/proto/` to `src/xlake/generated/`.

### Running Tests

```bash
cd xlake
uv run pytest
```

## Coding Standards

Follow the shared standards in `../CODING_STANDARDS.md`. Use abbreviated imports where applicable, include type hints and concise docstrings for all functions and public classes.


