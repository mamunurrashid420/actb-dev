"""Text splitting utilities for RAG chunking.

This module provides splitters for processing knowledge base documents,
particularly the data-viz-bible format with YAML frontmatter and markdown content.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

if TYPE_CHECKING:
    from ..models import VizDesignRule


class VizBiblePathError(ValueError):
    """Raised when a file path is not within the data-viz-bible directory."""

    pass


@dataclass
class VizBibleChunk:
    """A chunk of content from a VizBible document.

    Contains all metadata extracted from YAML frontmatter plus parsing context.
    Designed to map directly to VizDesignRule for storage.

    Attributes:
        content: The text content of the chunk (with contextual prefix).
        raw_content: Original content without contextual prefix.

        # From frontmatter
        document_type: "reference" | "action-interface" | "action-implementation"
        pipeline_stage: "selection" | "refinement" | "formatting" | "implementation" | None
        chart_type: Chart type slug (e.g., "line_chart") or None
        library: Implementation library (e.g., "recharts", "d3") or None
        data_pattern: Data pattern for selection rules (e.g., "temporal-measure") or None
        chart_family: Chart family (e.g., "evolution", "comparison") or None
        priority: Priority level ("P0", "P1", "P2") or None
        aliases: Alternative names for the chart type
        tags: Tags from frontmatter
        category: Reference category for foundation docs ("schema", "classification", "index")

        # From parsing
        origin_path: Source file path (e.g., "/data-viz-bible/selection/selection-line_chart.md")
        section_path: Header breadcrumb (e.g., "Selection: Line Chart > When to Use")
        chunk_index: Index of this chunk within the document
        total_chunks: Total number of chunks from the document
        char_count: Character count of raw_content
    """

    content: str
    raw_content: str = ""

    # From frontmatter
    document_type: str = "reference"
    pipeline_stage: str | None = None
    chart_type: str | None = None
    library: str | None = None
    data_pattern: str | None = None
    chart_family: str | None = None
    priority: str | None = None
    aliases: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    category: str | None = None

    # From parsing
    origin_path: str = ""
    section_path: str = ""
    chunk_index: int = 0
    total_chunks: int = 1
    char_count: int = 0

    # Legacy fields for backward compatibility
    metadata: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    _debug: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "content": self.content,
            "raw_content": self.raw_content,
            "document_type": self.document_type,
            "pipeline_stage": self.pipeline_stage,
            "chart_type": self.chart_type,
            "library": self.library,
            "data_pattern": self.data_pattern,
            "chart_family": self.chart_family,
            "priority": self.priority,
            "aliases": self.aliases,
            "tags": self.tags,
            "category": self.category,
            "origin_path": self.origin_path,
            "section_path": self.section_path,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "char_count": self.char_count,
            # Legacy
            "metadata": self.metadata,
            "headers": self.headers,
            "_debug": self._debug,
        }

    @property
    def header_path(self) -> str:
        """Return a breadcrumb-style path of headers (e.g., 'Title > Section > Subsection')."""
        ordered_headers = []
        for level in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            if level in self.headers:
                ordered_headers.append(self.headers[level])
        return " > ".join(ordered_headers)

    def to_viz_design_rule(self) -> VizDesignRule:
        """Convert this chunk to a VizDesignRule model instance.

        Returns:
            VizDesignRule instance ready for storage.
        """
        from ..models import VizDesignRule

        now = datetime.now(UTC)
        return VizDesignRule(
            rule_id=str(uuid.uuid4()),
            document_type=self.document_type,
            origin_path=self.origin_path,
            pipeline_stage=self.pipeline_stage,
            chart_type=self.chart_type,
            library=self.library,
            data_pattern=self.data_pattern,
            chart_family=self.chart_family,
            priority=self.priority,
            aliases=self.aliases,
            section_path=self.section_path,
            content=self.content,
            tags=self.tags,
            category=self.category,
            created_at=now,
            updated_at=now,
        )


class VizBibleDocSplitter:
    """Splitter for VizBible knowledge base documents.

    Parses documents with YAML frontmatter and markdown content,
    splitting by header sections with optional recursive splitting
    for oversized sections.

    Document format:
        ---
        type: action-implementation
        chart-type: line_chart
        ...
        ---

        # Document Title

        ## Section One
        Content...

        ## Section Two
        Content...

    Chunking strategies:
    - action-interface documents (blueprints): Kept as single chunks since they
      describe complete processes for each pipeline stage.
    - action-implementation documents (chart-specific): Split by header sections
      for granular retrieval.
    - reference documents: Split by header sections.

    Usage:
        splitter = VizBibleDocSplitter()
        chunks = splitter.split_file(Path("selection-line_chart.md"))

        # Or from text
        chunks = splitter.split_text(text, origin="/data-viz-bible/...")
    """

    # Headers to split on (H1 through H4)
    DEFAULT_HEADERS_TO_SPLIT_ON = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
        ("####", "h4"),
    ]

    # Frontmatter pattern: content between --- markers at start of document
    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    def __init__(
        self,
        *,
        max_chunk_size: int = 2000,
        chunk_overlap: int = 200,
        headers_to_split_on: list[tuple[str, str]] | None = None,
        strip_headers: bool = False,
        keep_blueprints_whole: bool = True,
    ) -> None:
        """Initialize the splitter.

        Args:
            max_chunk_size: Maximum characters per chunk before recursive splitting.
            chunk_overlap: Character overlap for recursive splits.
            headers_to_split_on: List of (marker, name) tuples for header splitting.
                Defaults to H1-H4.
            strip_headers: Whether to remove headers from chunk content.
                Defaults to False (keeps headers for context).
            keep_blueprints_whole: Whether to keep action-interface documents
                (blueprints) as single chunks. Defaults to True.
        """
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap
        self.headers_to_split_on = (
            headers_to_split_on or self.DEFAULT_HEADERS_TO_SPLIT_ON
        )
        self.strip_headers = strip_headers
        self.keep_blueprints_whole = keep_blueprints_whole

        # Initialize splitters
        self._header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on,
            strip_headers=self.strip_headers,
        )
        self._recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.max_chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def split_file(self, path: Path) -> list[VizBibleChunk]:
        """Split a file into chunks.

        Args:
            path: Path to the markdown file. Must be within a data-viz-bible/ directory.

        Returns:
            List of VizBibleChunk objects.

        Raises:
            VizBiblePathError: If the file is not within a data-viz-bible/ directory.
            FileNotFoundError: If the file does not exist.
        """
        text = path.read_text(encoding="utf-8")

        # Compute origin path (validates file is in data-viz-bible/)
        origin = self._compute_origin(path)

        return self.split_text(text, origin=origin)

    def split_text(
        self, text: str, *, origin: str | None = None
    ) -> list[VizBibleChunk]:
        """Split text into chunks.

        Args:
            text: The document text with optional YAML frontmatter.
            origin: Optional origin path for debug metadata.

        Returns:
            List of VizBibleChunk objects with contextual prefixes.
        """
        # Parse frontmatter and extract structured metadata
        metadata, markdown_content = self._parse_frontmatter(text)
        parsed = self._extract_metadata_fields(metadata)

        # Determine if this is a blueprint (action-interface) document
        is_blueprint = (
            self.keep_blueprints_whole and parsed["document_type"] == "action-interface"
        )

        if is_blueprint:
            # Keep the entire document as a single chunk
            chunks = self._create_single_chunk(
                markdown_content, metadata, parsed, origin
            )
        else:
            # Split by headers as usual
            chunks = self._split_by_headers(markdown_content, metadata, parsed, origin)

        return chunks

    def _create_single_chunk(
        self,
        markdown_content: str,
        metadata: dict[str, Any],
        parsed: dict[str, Any],
        origin: str | None,
    ) -> list[VizBibleChunk]:
        """Create a single chunk for the entire document (for blueprints).

        Args:
            markdown_content: The markdown content without frontmatter.
            metadata: Raw frontmatter metadata.
            parsed: Parsed/extracted metadata fields.
            origin: Origin path.

        Returns:
            List containing a single VizBibleChunk.
        """
        # Extract title from first H1 header
        title_match = re.search(r"^#\s+(.+)$", markdown_content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else "Document"

        section_path = title
        raw_content = markdown_content.strip()

        # Build contextual prefix
        prefix = self._build_contextual_prefix(parsed, section_path)
        content = f"{prefix}\n{raw_content}" if prefix else raw_content

        chunk = VizBibleChunk(
            content=content,
            raw_content=raw_content,
            document_type=parsed["document_type"],
            pipeline_stage=parsed["pipeline_stage"],
            chart_type=parsed["chart_type"],
            library=parsed["library"],
            data_pattern=parsed["data_pattern"],
            chart_family=parsed["chart_family"],
            priority=parsed["priority"],
            aliases=parsed["aliases"],
            tags=parsed["tags"],
            category=parsed["category"],
            origin_path=origin or "",
            section_path=section_path,
            chunk_index=0,
            total_chunks=1,
            char_count=len(raw_content),
            # Legacy fields
            metadata=metadata.copy(),
            headers={"h1": title},
            _debug={
                "origin": origin,
                "chunk_index": 0,
                "total_chunks": 1,
                "char_count": len(raw_content),
            },
        )

        return [chunk]

    def _split_by_headers(
        self,
        markdown_content: str,
        metadata: dict[str, Any],
        parsed: dict[str, Any],
        origin: str | None,
    ) -> list[VizBibleChunk]:
        """Split content by headers into multiple chunks.

        Args:
            markdown_content: The markdown content without frontmatter.
            metadata: Raw frontmatter metadata.
            parsed: Parsed/extracted metadata fields.
            origin: Origin path.

        Returns:
            List of VizBibleChunk objects.
        """
        # Split by headers
        header_docs = self._header_splitter.split_text(markdown_content)

        # Process each header section
        chunks: list[VizBibleChunk] = []

        for doc in header_docs:
            raw_content = doc.page_content
            headers = dict(doc.metadata)  # e.g., {"h1": "Title", "h2": "Section"}

            # Build section path from headers
            section_path = self._build_section_path(headers)

            # Build contextual prefix
            prefix = self._build_contextual_prefix(parsed, section_path)
            content = f"{prefix}\n{raw_content}" if prefix else raw_content

            # Check if section needs recursive splitting
            if len(raw_content) > self.max_chunk_size:
                # Split large section recursively
                sub_chunks = self._recursive_splitter.split_text(raw_content)
                for sub_idx, sub_content in enumerate(sub_chunks):
                    sub_section_path = (
                        f"{section_path} (part {sub_idx + 1})"
                        if len(sub_chunks) > 1
                        else section_path
                    )
                    sub_prefix = self._build_contextual_prefix(parsed, sub_section_path)
                    prefixed_content = (
                        f"{sub_prefix}\n{sub_content}" if sub_prefix else sub_content
                    )

                    chunks.append(
                        VizBibleChunk(
                            content=prefixed_content,
                            raw_content=sub_content,
                            document_type=parsed["document_type"],
                            pipeline_stage=parsed["pipeline_stage"],
                            chart_type=parsed["chart_type"],
                            library=parsed["library"],
                            data_pattern=parsed["data_pattern"],
                            chart_family=parsed["chart_family"],
                            priority=parsed["priority"],
                            aliases=parsed["aliases"],
                            tags=parsed["tags"],
                            category=parsed["category"],
                            origin_path=origin or "",
                            section_path=sub_section_path,
                            chunk_index=0,  # Will be set later
                            total_chunks=0,  # Will be set later
                            char_count=len(sub_content),
                            # Legacy fields
                            metadata=metadata.copy(),
                            headers=headers.copy(),
                            _debug={},
                        )
                    )
            else:
                chunks.append(
                    VizBibleChunk(
                        content=content,
                        raw_content=raw_content,
                        document_type=parsed["document_type"],
                        pipeline_stage=parsed["pipeline_stage"],
                        chart_type=parsed["chart_type"],
                        library=parsed["library"],
                        data_pattern=parsed["data_pattern"],
                        chart_family=parsed["chart_family"],
                        priority=parsed["priority"],
                        aliases=parsed["aliases"],
                        tags=parsed["tags"],
                        category=parsed["category"],
                        origin_path=origin or "",
                        section_path=section_path,
                        chunk_index=0,  # Will be set later
                        total_chunks=0,  # Will be set later
                        char_count=len(raw_content),
                        # Legacy fields
                        metadata=metadata.copy(),
                        headers=headers.copy(),
                        _debug={},
                    )
                )

        # Update chunk indices
        total_chunks = len(chunks)
        for idx, chunk in enumerate(chunks):
            chunk.chunk_index = idx
            chunk.total_chunks = total_chunks
            chunk._debug = {
                "origin": origin,
                "chunk_index": idx,
                "total_chunks": total_chunks,
                "char_count": chunk.char_count,
            }

        return chunks

    def _extract_metadata_fields(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Extract and normalize metadata fields from frontmatter.

        Args:
            metadata: Raw YAML frontmatter dict.

        Returns:
            Dict with normalized field values.
        """
        # Map frontmatter keys to our field names (handle hyphenated keys)
        doc_type = metadata.get("type", "reference")
        action = metadata.get("action")
        chart_type = metadata.get("chart-type")
        library = metadata.get("library")
        data_pattern = metadata.get("data-pattern")
        chart_family = metadata.get("family")
        priority = metadata.get("priority")
        aliases = metadata.get("aliases", [])
        tags = metadata.get("tags", [])
        category = metadata.get("category")

        # Ensure aliases and tags are lists
        if isinstance(aliases, str):
            aliases = [aliases]
        if isinstance(tags, str):
            tags = [tags]

        return {
            "document_type": doc_type,
            "pipeline_stage": action,
            "chart_type": chart_type,
            "library": library,
            "data_pattern": data_pattern,
            "chart_family": chart_family,
            "priority": priority,
            "aliases": aliases or [],
            "tags": tags or [],
            "category": category,
        }

    def _build_section_path(self, headers: dict[str, str]) -> str:
        """Build a breadcrumb-style section path from headers.

        Args:
            headers: Dict of header level to header text (e.g., {"h1": "Title", "h2": "Section"}).

        Returns:
            Section path string (e.g., "Title > Section").
        """
        ordered_headers = []
        for level in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            if level in headers:
                ordered_headers.append(headers[level])
        return " > ".join(ordered_headers) if ordered_headers else "Document"

    def _build_contextual_prefix(
        self, parsed: dict[str, Any], section_path: str
    ) -> str:
        """Build a contextual prefix for semantic search.

        Creates a bracket-enclosed prefix that provides context for the chunk,
        making it self-contained for semantic search.

        Example: "[Line Chart - Selection - When to Use]"

        Args:
            parsed: Parsed metadata fields.
            section_path: The section path within the document.

        Returns:
            Contextual prefix string or empty string if insufficient context.
        """
        parts = []

        # Add chart type if present
        if parsed["chart_type"]:
            # Convert slug to title case (e.g., "line_chart" -> "Line Chart")
            chart_name = (
                parsed["chart_type"].replace("_", " ").replace("-", " ").title()
            )
            parts.append(chart_name)

        # Add pipeline stage if present
        if parsed["pipeline_stage"]:
            parts.append(parsed["pipeline_stage"].title())

        # Add library for implementation docs
        if parsed["library"]:
            parts.append(parsed["library"])

        # Add the last part of section path (most specific header)
        if section_path:
            # Get the last segment of the section path
            last_section = (
                section_path.split(" > ")[-1] if " > " in section_path else section_path
            )
            # Only add if it's different from what we already have
            if last_section and last_section.lower() not in [p.lower() for p in parts]:
                parts.append(last_section)

        if not parts:
            return ""

        return f"[{' - '.join(parts)}]"

    def _parse_frontmatter(self, text: str) -> tuple[dict[str, Any], str]:
        """Extract YAML frontmatter from document.

        Args:
            text: Full document text.

        Returns:
            Tuple of (metadata dict, remaining markdown content).
        """
        match = self.FRONTMATTER_PATTERN.match(text)

        if match:
            yaml_content = match.group(1)
            try:
                metadata = yaml.safe_load(yaml_content) or {}
            except yaml.YAMLError:
                metadata = {}
            # Remove frontmatter from content
            markdown_content = text[match.end() :]
        else:
            metadata = {}
            markdown_content = text

        return metadata, markdown_content

    def _compute_origin(self, path: Path) -> str:
        """Compute the origin path for a file.

        The file must be within a data-viz-bible/ directory.

        Args:
            path: The file path.

        Returns:
            Origin string like '/data-viz-bible/selection/selection-line_chart.md'.

        Raises:
            VizBiblePathError: If the file is not within a data-viz-bible/ directory.
        """
        path = path.resolve()
        path_str = str(path)

        # File must be within data-viz-bible/
        if "data-viz-bible" not in path_str:
            raise VizBiblePathError(
                f"File must be within a data-viz-bible/ directory: {path}"
            )

        # Extract from data-viz-bible onwards
        idx = path_str.find("data-viz-bible")
        return "/" + path_str[idx:]
