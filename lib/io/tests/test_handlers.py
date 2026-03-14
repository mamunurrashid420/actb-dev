"""Tests for file type handlers."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import polars as pl
import pytest
from upath import UPath

from shared.io.handlers import (
    JSONHandler,
    PandasJSONEncoder,
    ParquetDatasetHandler,
    ParquetHandler,
)


class TestParquetHandler:
    """Tests for ParquetHandler."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def handler(self):
        """Create ParquetHandler instance."""
        return ParquetHandler()

    def test_supported_type(self, handler):
        """Test supported_type property."""
        assert handler.supported_type == pd.DataFrame

    def test_extension(self, handler):
        """Test extension property."""
        assert handler.extension == ".parquet"

    def test_dump_and_load(self, handler, temp_dir):
        """Test saving and loading DataFrame."""
        # Arrange
        want_df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        file_path = UPath(temp_dir / "test.parquet")

        # Act
        handler.dump(want_df, file_path)
        got_df = handler.load(file_path)

        # Assert
        pd.testing.assert_frame_equal(got_df, want_df)

    def test_dump_creates_file(self, handler, temp_dir):
        """Test that dump creates the file."""
        # Arrange
        df = pd.DataFrame({"col": [1, 2]})
        file_path = UPath(temp_dir / "output.parquet")

        # Act
        handler.dump(df, file_path)

        # Assert
        assert file_path.exists()

    def test_dump_uses_file_like_object(self, handler, temp_dir):
        """Test that dump uses path.open() for compatibility with S3Path.

        This prevents regression where paths are passed directly to pandas,
        which doesn't work with S3Path objects.
        """
        # Arrange
        df = pd.DataFrame({"col": [1, 2]})
        file_path = UPath(temp_dir / "test.parquet")

        # Act & Assert - patch the open method to track calls
        with patch.object(type(file_path), "open", wraps=file_path.open) as mock_open:
            handler.dump(df, file_path)
            mock_open.assert_called_once()
            args, kwargs = mock_open.call_args
            assert args[0] == "wb", "ParquetHandler.dump must open in binary write mode"

    def test_load_uses_file_like_object(self, handler, temp_dir):
        """Test that load uses path.open() for compatibility with S3Path."""
        # Arrange - create a valid parquet file first
        df = pd.DataFrame({"col": [1, 2]})
        file_path = UPath(temp_dir / "test.parquet")
        df.to_parquet(str(file_path), index=False)

        # Act & Assert - patch the open method to track calls
        with patch.object(type(file_path), "open", wraps=file_path.open) as mock_open:
            handler.load(file_path)
            mock_open.assert_called_once()
            args, kwargs = mock_open.call_args
            assert args[0] == "rb", "ParquetHandler.load must open in binary read mode"


class TestJSONHandler:
    """Tests for JSONHandler."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def handler(self):
        """Create JSONHandler instance."""
        return JSONHandler()

    def test_supported_type(self, handler):
        """Test supported_type property."""
        assert handler.supported_type is dict

    def test_extension(self, handler):
        """Test extension property."""
        assert handler.extension == ".json"

    def test_dump_and_load(self, handler, temp_dir):
        """Test saving and loading dict."""
        # Arrange
        want_data = {"key": "value", "number": 42, "nested": {"inner": "data"}}
        file_path = UPath(temp_dir / "test.json")

        # Act
        handler.dump(want_data, file_path)
        got_data = handler.load(file_path)

        # Assert
        assert got_data == want_data

    def test_dump_creates_file(self, handler, temp_dir):
        """Test that dump creates the file."""
        # Arrange
        data = {"test": True}
        file_path = UPath(temp_dir / "output.json")

        # Act
        handler.dump(data, file_path)

        # Assert
        assert file_path.exists()

    def test_dump_formats_json(self, handler, temp_dir):
        """Test that dump creates formatted JSON."""
        # Arrange
        data = {"a": 1, "b": 2}
        file_path = UPath(temp_dir / "formatted.json")

        # Act
        handler.dump(data, file_path)

        # Assert - check it's indented
        with open(file_path) as f:
            content = f.read()
        assert "  " in content  # Has indentation


class TestParquetDatasetHandler:
    """Tests for ParquetDatasetHandler (Polars LazyFrame → sharded parquet)."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def handler(self):
        """Create ParquetDatasetHandler instance."""
        return ParquetDatasetHandler(rows_per_shard=100)

    def test_supported_type(self, handler):
        """Test supported_type property."""
        assert handler.supported_type == pl.LazyFrame

    def test_extension(self, handler):
        """Test extension property is empty (directory, not file)."""
        assert handler.extension == ""

    def test_dump_creates_shard_files(self, handler, temp_dir):
        """Test that dump creates properly named shard files."""
        # Arrange
        df = pl.DataFrame({"a": list(range(10)), "b": ["x"] * 10})
        lf = df.lazy()
        output_dir = UPath(temp_dir / "output")

        # Act
        handler.dump(lf, output_dir)

        # Assert - should create shard files with correct naming
        shard_files = sorted(output_dir.glob("part-*.parquet"))
        assert len(shard_files) >= 1
        assert shard_files[0].name == "part-0000.parquet"

    def test_dump_and_load_roundtrip(self, handler, temp_dir):
        """Test saving and loading LazyFrame roundtrip."""
        # Arrange
        want_df = pl.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        lf = want_df.lazy()
        output_dir = UPath(temp_dir / "output")

        # Act
        handler.dump(lf, output_dir)
        got_lf = handler.load(output_dir)
        got_df = got_lf.collect()

        # Assert - use Polars testing utilities
        assert got_df.shape == want_df.shape
        assert set(got_df.columns) == set(want_df.columns)

    def test_can_load_returns_true_for_shard_directory(self, handler, temp_dir):
        """Test can_load returns True for directory with shard files."""
        # Arrange - create a shard file
        output_dir = UPath(temp_dir / "output")
        output_dir.mkdir()
        (output_dir / "part-0000.parquet").write_bytes(b"dummy")

        # Act & Assert
        assert handler.can_load(output_dir) is True

    def test_can_load_returns_false_for_empty_directory(self, handler, temp_dir):
        """Test can_load returns False for empty directory."""
        # Arrange
        output_dir = UPath(temp_dir / "empty")
        output_dir.mkdir()

        # Act & Assert
        assert handler.can_load(output_dir) is False

    def test_can_load_returns_false_for_file(self, handler, temp_dir):
        """Test can_load returns False for file path."""
        # Arrange
        file_path = UPath(temp_dir / "file.txt")
        file_path.write_text("test")

        # Act & Assert
        assert handler.can_load(file_path) is False


class TestPandasJSONEncoder:
    """Tests for PandasJSONEncoder."""

    def test_encodes_timestamp(self):
        """Test encoding pandas Timestamp."""
        # Arrange
        ts = pd.Timestamp("2024-01-15 10:30:00")

        # Act
        got = json.dumps({"date": ts}, cls=PandasJSONEncoder)

        # Assert
        assert "2024-01-15" in got

    def test_encodes_datetime(self):
        """Test encoding datetime."""
        import datetime as dt

        # Arrange
        dt_obj = dt.datetime(2024, 1, 15, 10, 30, 0)

        # Act
        got = json.dumps({"date": dt_obj}, cls=PandasJSONEncoder)

        # Assert
        assert "2024-01-15" in got

    def test_normal_types_unchanged(self):
        """Test that normal types are encoded normally."""
        # Arrange
        data = {"string": "hello", "number": 42, "list": [1, 2, 3]}

        # Act
        got = json.dumps(data, cls=PandasJSONEncoder)
        loaded = json.loads(got)

        # Assert
        assert loaded == data
