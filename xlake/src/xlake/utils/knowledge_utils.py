"""Utilities for ingesting knowledge base documents into stores.

This module provides functions for parsing and ingesting knowledge base
documents (like the data-viz-bible) into the CoreContextStore with
vector embeddings for semantic search.

Example:
    >>> from pathlib import Path
    >>> from xlake.utils.knowledge_utils import ingest_viz_bible
    >>> stats = ingest_viz_bible(Path("path/to/data-viz-bible"))
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xlake.stores.core_context_store import CoreContextStore


def find_viz_bible_files(viz_bible_path: Path) -> list[Path]:
    """Find all markdown files in the data-viz-bible directory.

    Args:
        viz_bible_path: Path to the data-viz-bible directory.

    Returns:
        List of markdown file paths, excluding 99-contributing.md.
    """
    files = list(viz_bible_path.glob("**/*.md"))

    # Exclude contributing.md (for developers, not agents)
    files = [f for f in files if "99-contributing" not in f.name]

    # Sort for consistent ordering
    files.sort()

    return files


def create_store_from_env() -> CoreContextStore:
    """Create a CoreContextStore instance based on environment configuration.

    Uses APP_ENV to determine the environment (development/staging/production),
    then loads the appropriate configuration from environment variables.

    Environment variables:
    - APP_ENV: development|staging|production (default: development)

    For development:
    - XLAKE_CORE_CONTEXT_SQLITE_PATH: SQLite path (default: ':memory:')
    - XLAKE_CORE_CONTEXT_QDRANT_LOCAL_PATH: Local Qdrant path (default: ':memory:')

    For staging/production:
    - XLAKE_CORE_CONTEXT_QDRANT_URL: Qdrant Cloud URL
    - XLAKE_CORE_CONTEXT_QDRANT_API_KEY: Qdrant Cloud API key
    - XLAKE_CORE_SUPABASE_URL: Supabase project URL
    - XLAKE_CORE_SUPABASE_SERVICE_KEY: Supabase service role key

    Returns:
        A configured CoreContextStore instance.
    """
    from xlake.stores.config import get_environment, load_core_context_store_config
    from xlake.stores.core_context_store import create_core_context_store
    from xlake.stores.settings import get_xlake_settings

    env = get_environment()
    settings = get_xlake_settings()
    config = load_core_context_store_config(env, settings)
    return create_core_context_store(config)


def ingest_viz_bible(
    viz_bible_path: Path,
    *,
    store: CoreContextStore | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, int]:
    """Ingest all data-viz-bible documents into CoreContextStore.

    The store configuration is determined by environment variables via APP_ENV.
    You can also provide a pre-configured store for testing or custom setups.

    Args:
        viz_bible_path: Path to the data-viz-bible directory.
        store: Optional pre-configured CoreContextStore. If not provided,
            creates one from environment configuration (via create_store_from_env()).
        dry_run: If True, parse files but don't store (uses in-memory storage).
        verbose: If True, print progress for each file.

    Returns:
        Dict with ingestion statistics:
        - files_processed: Number of files successfully processed
        - files_skipped: Number of files skipped due to errors
        - chunks_created: Total chunks parsed from files
        - chunks_stored: Total chunks stored (0 if dry_run)
        - blueprints: Count of action-interface chunks
        - chart_rules: Count of action-implementation chunks
        - foundation_rules: Count of reference chunks
        - errors: Number of errors encountered

    Example:
        >>> from pathlib import Path
        >>> from xlake.utils.knowledge_utils import ingest_viz_bible
        >>> stats = ingest_viz_bible(Path("path/to/data-viz-bible"))
        >>> print(f"Stored {stats['chunks_stored']} chunks")
    """
    from xlake.core import TenantContext, UserContext
    from xlake.models.tenant import TenantIdentity
    from xlake.stores.config import QdrantLocalConfig, SqliteConfig
    from xlake.stores.core_context_store import QdrantSqliteLocalFSCoreContextStore
    from xlake.utils.text_splitter import VizBibleDocSplitter

    # Determine whether we own the store (and should close it)
    owns_store = store is None

    # Create store from environment if not provided
    if store is None:
        if dry_run:
            # For dry run, always use in-memory storage
            store = QdrantSqliteLocalFSCoreContextStore(
                qdrant_config=QdrantLocalConfig(path=":memory:"),
                sqlite_config=SqliteConfig(database_path=":memory:"),
            )
        else:
            store = create_store_from_env()

    # Initialize splitter
    splitter = VizBibleDocSplitter(
        max_chunk_size=2000,
        chunk_overlap=200,
        keep_blueprints_whole=True,  # Keep interface docs as single chunks
    )

    # Admin context for writing
    tenant_identity = TenantIdentity(
        tenant_id="actbi",
        tenant_name="ActBI",
        industry="technology",
        region="US",
        timezone="America/New_York",
        locale="en_US",
    )
    tenant = TenantContext(identity=tenant_identity)
    user = UserContext(
        user_id="ingest-script",
        tenant_id="actbi",
        role="admin",
    )

    # Find all files
    files = find_viz_bible_files(viz_bible_path)
    print(f"Found {len(files)} markdown files to process")

    # Statistics
    stats = {
        "files_processed": 0,
        "files_skipped": 0,
        "chunks_created": 0,
        "chunks_stored": 0,
        "blueprints": 0,
        "chart_rules": 0,
        "foundation_rules": 0,
        "errors": 0,
    }

    # Process each file
    for file_path in files:
        try:
            if verbose:
                print(f"Processing: {file_path.relative_to(viz_bible_path)}")

            # Parse file into chunks
            chunks = splitter.split_file(file_path)
            stats["chunks_created"] += len(chunks)

            # Categorize chunks
            for chunk in chunks:
                if chunk.document_type == "action-interface":
                    stats["blueprints"] += 1
                elif chunk.document_type == "action-implementation":
                    stats["chart_rules"] += 1
                elif chunk.document_type == "reference":
                    stats["foundation_rules"] += 1

            # Convert to VizDesignRule and store
            if not dry_run:
                for chunk in chunks:
                    rule = chunk.to_viz_design_rule()
                    store.upsert_viz_design_rule(rule, tenant=tenant, user=user)
                    stats["chunks_stored"] += 1

            stats["files_processed"] += 1

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            stats["errors"] += 1
            stats["files_skipped"] += 1

    # Close store only if we created it
    if owns_store:
        store.close()

    return stats
