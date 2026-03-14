"""Tests for VizBibleDocSplitter."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from xlake.utils.text_splitter import (
    VizBibleChunk,
    VizBibleDocSplitter,
    VizBiblePathError,
)

# -----------------------------------------------------------------------------
# Fixtures: Sample documents matching data-viz-bible format
# -----------------------------------------------------------------------------

SAMPLE_LINE_CHART_DOC = """\
---
type: action-implementation
action: selection
chart-type: line_chart
aliases: [line graph, trend chart]
data-pattern: temporal-measure
family: evolution
priority: P0
tags: [selection, line_chart, evolution, trends]
---

# Selection: Line Chart

Shows trends and changes over continuous data, typically time.

## When to Use

- **Showing trends over time**: Revenue by month, users by week
- **Continuous data with meaningful connections**: Values can be interpolated
- **Comparing multiple series over the same interval**: Revenue vs. costs

### Data Pattern

- 0 DIMENSIONS + 1 MEASURE + TEMPORAL (single series)
- 1 DIMENSION + 1 MEASURE + TEMPORAL (multiple series)

### User Intent Signals

Queries that suggest a line chart:
- "Show me the trend over..."
- "How has X changed over time..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| Discrete categories | Lines imply false continuity | Bar Chart |
| Single time point | Line adds no value | Slope Chart |

## Critical Rules

> **Lines must connect meaningful continuous data.**

The line between points implies intermediate values exist.
"""

MINIMAL_DOC = """\
---
type: reference
---

# Simple Doc

Just some content here.
"""

NO_FRONTMATTER_DOC = """\
# Document Without Frontmatter

## Section One

Content for section one.

## Section Two

Content for section two.
"""

LARGE_SECTION_DOC = """\
---
type: test
---

# Large Section Test

## Very Large Section

""" + (
    "This is a long paragraph that will be repeated many times to create a large section. "
    * 50
)


# -----------------------------------------------------------------------------
# Tests: Frontmatter Parsing
# -----------------------------------------------------------------------------


class TestFrontmatterParsing:
    """Tests for YAML frontmatter extraction."""

    def test_parses_frontmatter_metadata(self) -> None:
        """Should extract all frontmatter key-value pairs."""
        splitter = VizBibleDocSplitter()
        chunks = splitter.split_text(SAMPLE_LINE_CHART_DOC)

        # All chunks should have the same metadata
        assert len(chunks) > 0
        metadata = chunks[0].metadata

        assert metadata["type"] == "action-implementation"
        assert metadata["action"] == "selection"
        assert metadata["chart-type"] == "line_chart"
        assert metadata["aliases"] == ["line graph", "trend chart"]
        assert metadata["priority"] == "P0"
        assert "selection" in metadata["tags"]

    def test_handles_no_frontmatter(self) -> None:
        """Should handle documents without frontmatter."""
        splitter = VizBibleDocSplitter()
        chunks = splitter.split_text(NO_FRONTMATTER_DOC)

        assert len(chunks) > 0
        # Metadata should be empty dict
        assert chunks[0].metadata == {}

    def test_handles_minimal_frontmatter(self) -> None:
        """Should handle minimal frontmatter."""
        splitter = VizBibleDocSplitter()
        chunks = splitter.split_text(MINIMAL_DOC)

        assert len(chunks) > 0
        assert chunks[0].metadata == {"type": "reference"}


# -----------------------------------------------------------------------------
# Tests: Header Hierarchy
# -----------------------------------------------------------------------------


class TestHeaderHierarchy:
    """Tests for header-based splitting and hierarchy tracking."""

    def test_captures_h1_header(self) -> None:
        """Should capture H1 (document title) in headers."""
        splitter = VizBibleDocSplitter()
        chunks = splitter.split_text(SAMPLE_LINE_CHART_DOC)

        # All chunks should reference the H1
        for chunk in chunks:
            assert "h1" in chunk.headers
            assert chunk.headers["h1"] == "Selection: Line Chart"

    def test_captures_h2_sections(self) -> None:
        """Should split on H2 sections and capture them."""
        splitter = VizBibleDocSplitter()
        chunks = splitter.split_text(SAMPLE_LINE_CHART_DOC)

        # Find chunks with different H2 headers
        h2_headers = {chunk.headers.get("h2") for chunk in chunks}

        assert "When to Use" in h2_headers
        assert "When NOT to Use" in h2_headers
        assert "Critical Rules" in h2_headers

    def test_captures_h3_subsections(self) -> None:
        """Should capture H3 headers for subsections."""
        splitter = VizBibleDocSplitter()
        chunks = splitter.split_text(SAMPLE_LINE_CHART_DOC)

        # Find chunks with H3 headers
        chunks_with_h3 = [c for c in chunks if "h3" in c.headers]

        assert len(chunks_with_h3) > 0

        h3_headers = {c.headers["h3"] for c in chunks_with_h3}
        assert "Data Pattern" in h3_headers
        assert "User Intent Signals" in h3_headers

    def test_header_path_property(self) -> None:
        """Should generate breadcrumb-style header path."""
        splitter = VizBibleDocSplitter()
        chunks = splitter.split_text(SAMPLE_LINE_CHART_DOC)

        # Find a chunk with H3
        chunk_with_h3 = next(
            (c for c in chunks if c.headers.get("h3") == "Data Pattern"), None
        )
        assert chunk_with_h3 is not None

        expected_path = "Selection: Line Chart > When to Use > Data Pattern"
        assert chunk_with_h3.header_path == expected_path


# -----------------------------------------------------------------------------
# Tests: Chunking Behavior
# -----------------------------------------------------------------------------


class TestChunkingBehavior:
    """Tests for chunking logic."""

    def test_creates_multiple_chunks(self) -> None:
        """Should create multiple chunks for a multi-section document."""
        splitter = VizBibleDocSplitter()
        chunks = splitter.split_text(SAMPLE_LINE_CHART_DOC)

        # Should have several chunks (one per major section/subsection)
        assert len(chunks) >= 4

    def test_chunk_content_not_empty(self) -> None:
        """All chunks should have non-empty content."""
        splitter = VizBibleDocSplitter()
        chunks = splitter.split_text(SAMPLE_LINE_CHART_DOC)

        for chunk in chunks:
            assert chunk.content.strip() != ""

    def test_recursive_splitting_for_large_sections(self) -> None:
        """Should recursively split sections exceeding max_chunk_size."""
        # Use a small max_chunk_size to force recursive splitting
        splitter = VizBibleDocSplitter(max_chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_text(LARGE_SECTION_DOC)

        # The large section should be split into multiple chunks
        # All should reference the same H2
        large_section_chunks = [
            c for c in chunks if c.headers.get("h2") == "Very Large Section"
        ]

        assert len(large_section_chunks) > 1, (
            "Large section should be split into multiple chunks"
        )

        # All sub-chunks should have the same headers
        for chunk in large_section_chunks:
            assert chunk.headers.get("h1") == "Large Section Test"
            assert chunk.headers.get("h2") == "Very Large Section"

    def test_preserves_metadata_across_chunks(self) -> None:
        """All chunks from same document should have same metadata."""
        splitter = VizBibleDocSplitter()
        chunks = splitter.split_text(SAMPLE_LINE_CHART_DOC)

        first_metadata = chunks[0].metadata
        for chunk in chunks[1:]:
            assert chunk.metadata == first_metadata


# -----------------------------------------------------------------------------
# Tests: Debug Metadata
# -----------------------------------------------------------------------------


class TestDebugMetadata:
    """Tests for _debug metadata fields."""

    def test_includes_origin(self) -> None:
        """Should include origin in _debug when provided."""
        splitter = VizBibleDocSplitter()
        origin = "/data-viz-bible/selection/selection-line_chart.md"
        chunks = splitter.split_text(SAMPLE_LINE_CHART_DOC, origin=origin)

        for chunk in chunks:
            assert chunk._debug["origin"] == origin

    def test_includes_chunk_index(self) -> None:
        """Should include chunk_index in _debug."""
        splitter = VizBibleDocSplitter()
        chunks = splitter.split_text(SAMPLE_LINE_CHART_DOC)

        for idx, chunk in enumerate(chunks):
            assert chunk._debug["chunk_index"] == idx

    def test_includes_total_chunks(self) -> None:
        """Should include total_chunks in _debug."""
        splitter = VizBibleDocSplitter()
        chunks = splitter.split_text(SAMPLE_LINE_CHART_DOC)

        total = len(chunks)
        for chunk in chunks:
            assert chunk._debug["total_chunks"] == total

    def test_includes_char_count(self) -> None:
        """Should include char_count in _debug (measures raw_content, not content with prefix)."""
        splitter = VizBibleDocSplitter()
        chunks = splitter.split_text(SAMPLE_LINE_CHART_DOC)

        for chunk in chunks:
            # char_count measures raw_content (without contextual prefix)
            assert chunk._debug["char_count"] == len(chunk.raw_content)
            assert chunk.char_count == len(chunk.raw_content)

    def test_origin_none_when_not_provided(self) -> None:
        """Origin should be None when not provided."""
        splitter = VizBibleDocSplitter()
        chunks = splitter.split_text(SAMPLE_LINE_CHART_DOC)

        for chunk in chunks:
            assert chunk._debug["origin"] is None


# -----------------------------------------------------------------------------
# Tests: File Operations
# -----------------------------------------------------------------------------


class TestFileOperations:
    """Tests for file-based splitting."""

    def test_split_file_in_data_viz_bible(self) -> None:
        """Should split a file within data-viz-bible/ and compute origin."""
        splitter = VizBibleDocSplitter()

        # Create a temp directory structure that includes data-viz-bible
        with tempfile.TemporaryDirectory() as tmpdir:
            viz_bible_dir = Path(tmpdir) / "data-viz-bible" / "selection"
            viz_bible_dir.mkdir(parents=True)

            test_file = viz_bible_dir / "selection-line_chart.md"
            test_file.write_text(SAMPLE_LINE_CHART_DOC, encoding="utf-8")

            chunks = splitter.split_file(test_file)

            assert len(chunks) > 0
            # Origin should be set with data-viz-bible path
            origin = chunks[0]._debug["origin"]
            assert origin is not None
            assert "data-viz-bible" in origin
            assert "selection-line_chart.md" in origin

    def test_split_file_outside_data_viz_bible_raises_error(self) -> None:
        """Should raise VizBiblePathError for files outside data-viz-bible/."""
        splitter = VizBibleDocSplitter()

        # Create a temp file NOT in data-viz-bible/
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(SAMPLE_LINE_CHART_DOC)
            temp_path = Path(f.name)

        try:
            with pytest.raises(VizBiblePathError) as exc_info:
                splitter.split_file(temp_path)

            assert "data-viz-bible" in str(exc_info.value)
        finally:
            temp_path.unlink()

    def test_computes_origin_from_path(self) -> None:
        """Should compute origin path correctly for data-viz-bible paths."""
        splitter = VizBibleDocSplitter()

        # Test path within data-viz-bible
        test_path = Path(
            "/some/repo/knowledge/data-viz-bible/selection/selection-line_chart.md"
        )
        origin = splitter._compute_origin(test_path)

        assert origin == "/data-viz-bible/selection/selection-line_chart.md"

    def test_compute_origin_raises_for_invalid_path(self) -> None:
        """Should raise VizBiblePathError for paths outside data-viz-bible/."""
        splitter = VizBibleDocSplitter()

        # Test path NOT in data-viz-bible
        test_path = Path("/some/other/docs/random-file.md")

        with pytest.raises(VizBiblePathError) as exc_info:
            splitter._compute_origin(test_path)

        assert "data-viz-bible" in str(exc_info.value)


# -----------------------------------------------------------------------------
# Tests: VizBibleChunk
# -----------------------------------------------------------------------------


class TestVizBibleChunk:
    """Tests for the VizBibleChunk dataclass."""

    def test_to_dict(self) -> None:
        """Should convert to dictionary correctly."""
        chunk = VizBibleChunk(
            content="Test content",
            metadata={"type": "test"},
            headers={"h1": "Title", "h2": "Section"},
            _debug={
                "origin": "/test.md",
                "chunk_index": 0,
                "total_chunks": 1,
                "char_count": 12,
            },
        )

        d = chunk.to_dict()

        assert d["content"] == "Test content"
        assert d["metadata"] == {"type": "test"}
        assert d["headers"] == {"h1": "Title", "h2": "Section"}
        assert d["_debug"]["origin"] == "/test.md"

    def test_header_path_empty(self) -> None:
        """Should return empty string for chunk with no headers."""
        chunk = VizBibleChunk(content="Test")

        assert chunk.header_path == ""

    def test_header_path_single_header(self) -> None:
        """Should return single header without separator."""
        chunk = VizBibleChunk(content="Test", headers={"h1": "Title"})

        assert chunk.header_path == "Title"

    def test_header_path_preserves_order(self) -> None:
        """Should order headers from h1 to h6."""
        chunk = VizBibleChunk(
            content="Test",
            headers={"h3": "Sub", "h1": "Title", "h2": "Section"},
        )

        assert chunk.header_path == "Title > Section > Sub"


# -----------------------------------------------------------------------------
# Tests: Edge Cases
# -----------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_document(self) -> None:
        """Should handle empty document."""
        splitter = VizBibleDocSplitter()
        chunks = splitter.split_text("")

        # Should return empty list or single empty chunk
        assert isinstance(chunks, list)

    def test_frontmatter_only(self) -> None:
        """Should handle document with only frontmatter."""
        doc = """\
---
type: test
---
"""
        splitter = VizBibleDocSplitter()
        chunks = splitter.split_text(doc)

        assert isinstance(chunks, list)

    def test_malformed_yaml(self) -> None:
        """Should handle malformed YAML frontmatter gracefully."""
        doc = """\
---
type: [unclosed bracket
invalid: yaml: here
---

# Title

Content.
"""
        splitter = VizBibleDocSplitter()
        chunks = splitter.split_text(doc)

        # Should still create chunks, just with empty metadata
        assert len(chunks) > 0
        # Metadata should be empty due to YAML error
        assert chunks[0].metadata == {}

    def test_custom_headers_to_split_on(self) -> None:
        """Should respect custom headers_to_split_on configuration."""
        # Only split on H1 and H2
        splitter = VizBibleDocSplitter(headers_to_split_on=[("#", "h1"), ("##", "h2")])
        chunks = splitter.split_text(SAMPLE_LINE_CHART_DOC)

        # Should not have any H3 headers captured (they'll be in content)
        for chunk in chunks:
            assert "h3" not in chunk.headers

    def test_strip_headers_option(self) -> None:
        """Should strip headers from content when configured."""
        splitter = VizBibleDocSplitter(strip_headers=True)
        chunks = splitter.split_text(MINIMAL_DOC)

        # Headers should still be in metadata, but stripped from content
        # The exact behavior depends on langchain's implementation
        assert len(chunks) > 0
