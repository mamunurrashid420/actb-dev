"""XLake notebook utilities library.

This package provides reusable helper functions for XLake analysis notebooks.
"""

from .chunk_utils import print_chunk_details, print_chunk_summary, summarize_chunks
from .retrieval_utils import (
    build_search_query,
    content_mentions_data_shape,
    get_combo_chart_types,
    get_data_shape,
    matches_expected_chart_type,
    print_search_results,
    search_with_scores,
)
from .store_utils import create_test_contexts, create_test_store

__all__ = [
    # retrieval_utils
    "search_with_scores",
    "print_search_results",
    "build_search_query",
    "matches_expected_chart_type",
    "get_combo_chart_types",
    "get_data_shape",
    "content_mentions_data_shape",
    # chunk_utils
    "print_chunk_details",
    "print_chunk_summary",
    "summarize_chunks",
    # store_utils
    "create_test_store",
    "create_test_contexts",
]
