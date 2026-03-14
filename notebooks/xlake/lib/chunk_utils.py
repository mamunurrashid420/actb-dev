"""Chunk display utilities for XLake notebooks.

Provides helpers for displaying and summarizing VizBibleChunk objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xlake.utils.text_splitter import VizBibleChunk


def print_chunk_details(chunk: VizBibleChunk, label: str) -> None:
    """Print chunk details using VizBibleChunk fields.

    Args:
        chunk: A VizBibleChunk instance.
        label: A label for the chunk (e.g., "First Chunk").
    """
    print(f"**{label}:**")
    print(f"  origin_path:    {chunk.origin_path}")
    print(f"  section_path:   {chunk.section_path}")
    print(f"  document_type:  {chunk.document_type}")
    print(f"  pipeline_stage: {chunk.pipeline_stage}")
    print(f"  chart_type:     {chunk.chart_type}")
    print(f"  library:        {chunk.library}")
    print(f"  tags:           {chunk.tags}")
    print(f"  char_count:     {chunk.char_count:,}")
    print(f"  chunk_index:    {chunk.chunk_index}/{chunk.total_chunks}")
    print("-" * 60)
    print(chunk.content[:500] + "..." if len(chunk.content) > 500 else chunk.content)
    print("\n")


def summarize_chunks(chunks: list[VizBibleChunk]) -> dict[str, Any]:
    """Return stats summary for a list of chunks.

    Args:
        chunks: List of VizBibleChunk instances.

    Returns:
        Dict with summary statistics including:
        - total_chunks: Total number of chunks
        - total_chars: Total character count
        - char_stats: Dict with min, max, avg character counts
        - by_document_type: Count of chunks per document type
        - by_pipeline_stage: Count of chunks per pipeline stage
        - by_chart_type: Count of chunks per chart type
    """
    if not chunks:
        return {
            "total_chunks": 0,
            "total_chars": 0,
            "char_stats": {"min": 0, "max": 0, "avg": 0},
            "by_document_type": {},
            "by_pipeline_stage": {},
            "by_chart_type": {},
        }

    char_counts = [c.char_count for c in chunks]

    # Count by document type
    by_doc_type: dict[str, int] = {}
    for c in chunks:
        doc_type = c.document_type or "unknown"
        by_doc_type[doc_type] = by_doc_type.get(doc_type, 0) + 1

    # Count by pipeline stage
    by_stage: dict[str, int] = {}
    for c in chunks:
        stage = c.pipeline_stage or "(none)"
        by_stage[stage] = by_stage.get(stage, 0) + 1

    # Count by chart type
    by_chart: dict[str, int] = {}
    for c in chunks:
        chart = c.chart_type or "(none)"
        by_chart[chart] = by_chart.get(chart, 0) + 1

    return {
        "total_chunks": len(chunks),
        "total_chars": sum(char_counts),
        "char_stats": {
            "min": min(char_counts),
            "max": max(char_counts),
            "avg": sum(char_counts) / len(char_counts),
        },
        "by_document_type": by_doc_type,
        "by_pipeline_stage": by_stage,
        "by_chart_type": by_chart,
    }


def print_chunk_summary(chunks: list[VizBibleChunk]) -> None:
    """Print a formatted summary of chunks.

    Args:
        chunks: List of VizBibleChunk instances.
    """
    stats = summarize_chunks(chunks)

    print(f"Total chunks: {stats['total_chunks']}")
    print()

    print("Character counts per chunk:")
    print(f"  Min:  {stats['char_stats']['min']:,}")
    print(f"  Max:  {stats['char_stats']['max']:,}")
    print(f"  Avg:  {stats['char_stats']['avg']:,.0f}")
    print(f"  Total: {stats['total_chars']:,}")
    print()

    print("Chunks by document_type:")
    for doc_type, count in sorted(stats["by_document_type"].items()):
        print(f"  {doc_type}: {count}")

    print("\nChunks by pipeline_stage:")
    for stage, count in sorted(
        stats["by_pipeline_stage"].items(), key=lambda x: (x[0] != "(none)", x[0])
    ):
        print(f"  {stage}: {count}")

    if any(ct != "(none)" for ct in stats["by_chart_type"]):
        print("\nChunks by chart_type:")
        for chart, count in sorted(
            stats["by_chart_type"].items(), key=lambda x: (x[0] == "(none)", x[0])
        ):
            if chart != "(none)":
                print(f"  {chart}: {count}")
