"""Retrieval utilities for XLake notebooks.

Provides search helpers with similarity scores and chart type matching.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xlake.core import TenantContext, UserContext
    from xlake.stores.core_context_store import QdrantSqliteLocalFSCoreContextStore


# =============================================================================
# Chart Type Matching
# =============================================================================


def get_combo_chart_types(test_case: dict) -> list[str]:
    """Extract constituent chart types from a combo chart's combo_types property.

    For combo charts, the actual chart types are specified in:
    - expected_chart.combo_types (list of chart type strings)

    Args:
        test_case: A test case dict with 'expected_chart' key.

    Returns:
        List of constituent chart types, or empty list if not a combo.
    """
    expected_chart = test_case.get("expected_chart", {})
    return expected_chart.get("combo_types", [])


def matches_expected_chart_type(
    retrieved: str | list[str] | None,
    expected: str | list[str],
) -> bool:
    """Check if retrieved chart type(s) match expected.

    Supports both single chart types (string comparison) and combo charts
    (list comparison, order-independent).

    Args:
        retrieved: Retrieved chart type(s) - string for single, list for combo
        expected: Expected chart type(s) - string for single, list for combo

    Returns:
        True if retrieved matches expected.

    Examples:
        # Single chart type
        matches_expected_chart_type("line_chart", "line_chart")  # True
        matches_expected_chart_type("line_chart", "bar_chart_vertical")   # False

        # Combo chart (pass combo_types as expected)
        matches_expected_chart_type(
            ["bar_chart_vertical", "line_chart"],
            ["bar_chart_vertical", "line_chart"]
        )  # True (order-independent)
    """
    if retrieved is None:
        return False

    # List comparison for combo charts (order-independent)
    if isinstance(expected, list):
        if isinstance(retrieved, list):
            return set(retrieved) == set(expected)
        return False

    # String comparison for single chart types
    if isinstance(retrieved, str) and isinstance(expected, str):
        return retrieved == expected

    return False


# =============================================================================
# Search Functions
# =============================================================================


def search_with_scores(
    store: QdrantSqliteLocalFSCoreContextStore,
    query: str,
    tenant: TenantContext,
    user: UserContext,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Search for relevant chunks and return results with debug metadata.

    Uses the Qdrant client directly to get similarity scores, then
    fetches full rule details from SQLite.

    Args:
        store: The CoreContextStore instance with indexed VizDesignRules.
        query: The search query string.
        tenant: TenantContext for authorization.
        user: UserContext for authorization.
        top_k: Number of top results to return.

    Returns:
        List of dicts with: rank, score, origin_path, section_path,
        pipeline_stage, chart_type, library, content_preview
    """
    # Get embeddings for query
    embeddings = store._embedder.get_embeddings([query])
    if not embeddings:
        return []

    # Search Qdrant directly to get scores
    hits = store._qdrant_client.search(
        collection_name=store.COLLECTION_VIZ_RULES,
        query_vector=embeddings[0],
        limit=top_k,
    )

    results = []
    for rank, hit in enumerate(hits, 1):
        try:
            # Fetch full rule from SQLite
            rule = store.get_viz_design_rule(hit.id, tenant=tenant, user=user)

            # Truncate content for preview
            content_preview = rule.content[:300].replace("\n", " ")
            if len(rule.content) > 300:
                content_preview += "..."

            results.append({
                "rank": rank,
                "score": round(hit.score, 4),
                "rule_id": rule.rule_id,
                "origin_path": rule.origin_path,
                "section_path": rule.section_path,
                "pipeline_stage": rule.pipeline_stage or "(none)",
                "chart_type": rule.chart_type or "(none)",
                "library": rule.library or "(none)",
                "content_preview": content_preview,
            })
        except KeyError:
            # Rule not found in SQLite (shouldn't happen)
            results.append({
                "rank": rank,
                "score": round(hit.score, 4),
                "error": f"Rule {hit.id} not found",
            })

    return results


def print_search_results(query: str, results: list[dict[str, Any]]) -> None:
    """Pretty-print search results with debug metadata.

    Args:
        query: The original search query.
        results: List of result dicts from search_with_scores().
    """
    print(f'Query: "{query}"')
    print(f"Results: {len(results)}")
    print("=" * 80)

    for r in results:
        if "error" in r:
            print(f"[{r['rank']}] SCORE={r['score']} ERROR: {r['error']}")
            continue

        print(f"[{r['rank']}] SCORE={r['score']:.4f}")
        print(f"    origin:   {r['origin_path']}")
        print(f"    section:  {r['section_path']}")
        print(
            f"    stage:    {r['pipeline_stage']} | chart: {r['chart_type']} | lib: {r['library']}"
        )
        print(f"    preview:  {r['content_preview'][:100]}...")
        print()


# =============================================================================
# Query Building
# =============================================================================


def build_search_query(
    test_case: dict[str, Any],
    instructions: str | None = None,
) -> str:
    """Build a search query from a test case's nlp_query and output_schema.

    Combines the natural language query with field information from the schema
    to improve retrieval relevance. Optionally prepends custom instructions.

    Args:
        test_case: A test case dict with 'nlp_query' and 'output_schema' keys.
        instructions: Optional instructions to prepend to the query.

    Returns:
        Combined query string for semantic search with explicit keys.
    """
    parts = []

    # Instructions (optional, prepended first)
    if instructions:
        parts.append(f"instructions: {instructions}")

    # NLP query (always included)
    parts.append(f"nlp_query: {test_case['nlp_query']}")

    # Schema fields (if present)
    schema = test_case.get("output_schema", {})
    fields = schema.get("fields", [])
    if fields:
        fields_summary = ", ".join(
            f"{f['name']} ({f.get('role', 'UNKNOWN')})" for f in fields
        )
        parts.append(f"schema: {fields_summary}")

    return "\n".join(parts)


# =============================================================================
# Data Shape Helpers
# =============================================================================


def get_data_shape(test_case: dict[str, Any]) -> str:
    """Extract data shape pattern (e.g., '1D + 1M') from test case schema.

    Args:
        test_case: A test case dict with 'output_schema' key.

    Returns:
        Data shape string like '1D + 1M' or 'unknown' if no fields.
    """
    schema = test_case.get("output_schema", {})
    fields = schema.get("fields", [])

    dims = sum(1 for f in fields if f.get("role") == "DIMENSION")
    measures = sum(1 for f in fields if f.get("role") == "MEASURE")
    temporal = sum(1 for f in fields if f.get("role") == "TEMPORAL")

    parts = []
    if dims > 0:
        parts.append(f"{dims}D")
    if measures > 0:
        parts.append(f"{measures}M")
    if temporal > 0:
        parts.append("TEMPORAL")

    return " + ".join(parts) if parts else "unknown"


def content_mentions_data_shape(content: str, data_shape: str) -> bool:
    """Check if content mentions the data shape pattern.

    Args:
        content: The content string to search in.
        data_shape: The data shape pattern (e.g., '1D + 1M').

    Returns:
        True if the content mentions the data shape pattern.
    """
    content_lower = content.lower()
    parts = data_shape.split(" + ")

    for part in parts:
        if part.endswith("D"):
            n = part[:-1]
            if not any(p in content_lower for p in [f"{n}d", f"{n} dimension"]):
                return False
        elif part.endswith("M"):
            n = part[:-1]
            if not any(p in content_lower for p in [f"{n}m", f"{n} measure"]):
                return False

    return bool(parts)
