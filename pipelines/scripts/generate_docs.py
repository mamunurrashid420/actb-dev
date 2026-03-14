#!/usr/bin/env python
"""Generate markdown documentation from Dagster assets.

Usage:
    cd data
    PYTHONPATH=src uv run python scripts/generate_docs.py

Output:
    docs/generated/
    ├── README.md
    ├── DATA_INVENTORY.md
    └── LINEAGE.md
"""

from pathlib import Path

from pipelines.definitions import defs
from pipelines.utils.docs_generator import generate_docs


def main() -> None:
    """Generate documentation from Dagster definitions."""
    output_dir = Path(__file__).parent.parent / "docs" / "generated"
    generate_docs(defs, output_dir)


if __name__ == "__main__":
    main()
