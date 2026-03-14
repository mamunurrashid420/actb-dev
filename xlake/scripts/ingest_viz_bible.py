#!/usr/bin/env python3
"""Ingest data-viz-bible documents into CoreContextStore.

This script parses all markdown files from the data-viz-bible knowledge base,
converts them to VizDesignRule chunks, and stores them in the CoreContextStore
with vector embeddings for semantic search.

The store configuration is determined by environment variables:
- APP_ENV: development|staging|production (default: development)
- Development uses local SQLite and Qdrant (paths from XLAKE_CORE_* env vars)
- Staging/Production uses Qdrant Cloud and Supabase (credentials from env vars)

Usage:
    # From the xlake directory (uses APP_ENV to determine store config)
    python scripts/ingest_viz_bible.py --viz-bible-path ../../knowledge/data-viz-bible

    # Dry run (parse and show stats without storing)
    python scripts/ingest_viz_bible.py \
        --viz-bible-path ../../knowledge/data-viz-bible \
        --dry-run

    # From a Jupyter notebook or Python code
    from xlake.utils import ingest_viz_bible
    stats = ingest_viz_bible(Path("path/to/data-viz-bible"))
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from xlake.stores.config import get_environment
from xlake.utils.knowledge_utils import ingest_viz_bible


def main() -> None:
    """Main entry point for the ingestion script."""
    parser = argparse.ArgumentParser(
        description="Ingest data-viz-bible documents into CoreContextStore",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--viz-bible-path",
        type=Path,
        required=True,
        help="Path to the data-viz-bible directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse files and show stats without storing",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print progress for each file",
    )

    args = parser.parse_args()

    # Validate viz-bible path
    if not args.viz_bible_path.exists():
        print(f"Error: data-viz-bible path does not exist: {args.viz_bible_path}")
        sys.exit(1)

    if not args.viz_bible_path.is_dir():
        print(f"Error: data-viz-bible path is not a directory: {args.viz_bible_path}")
        sys.exit(1)

    # Get environment for display
    env = get_environment()

    # Run ingestion
    print(f"\n{'=' * 60}")
    print("Data-Viz-Bible Ingestion Script")
    print(f"{'=' * 60}")
    print(f"Source: {args.viz_bible_path}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    if not args.dry_run:
        print(f"Environment: {env}")
    print(f"{'=' * 60}\n")

    start_time = datetime.now(UTC)
    stats = ingest_viz_bible(
        viz_bible_path=args.viz_bible_path,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    end_time = datetime.now(UTC)
    duration = (end_time - start_time).total_seconds()

    # Print results
    print(f"\n{'=' * 60}")
    print("Ingestion Complete")
    print(f"{'=' * 60}")
    print(f"Duration: {duration:.2f}s")
    print("\nFiles:")
    print(f"  Processed: {stats['files_processed']}")
    print(f"  Skipped:   {stats['files_skipped']}")
    print(f"  Errors:    {stats['errors']}")
    print("\nChunks:")
    print(f"  Created:   {stats['chunks_created']}")
    print(f"  Stored:    {stats['chunks_stored']}")
    print("\nBy Type:")
    print(f"  Blueprints (action-interface): {stats['blueprints']}")
    print(f"  Chart Rules (action-impl):     {stats['chart_rules']}")
    print(f"  Foundation (reference):        {stats['foundation_rules']}")
    print(f"{'=' * 60}\n")

    if stats["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
