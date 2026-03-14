"""Tests for FileSystemIOManager."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import dagster as dg
import pandas as pd
import polars as pl
import pytest
from upath import UPath

from pipelines.io_managers import FileSystemIOManager, JSONHandler, ParquetHandler


class TestFileSystemIOManager:
    """Test suite for FileSystemIOManager."""

    def setup_method(self):
        """Set up test fixtures before each test."""
        # Create temp directory for each test
        self.temp_dir = Path(tempfile.mkdtemp())
        self.io_manager = FileSystemIOManager(base_path=str(self.temp_dir))

    def teardown_method(self):
        """Clean up after each test."""
        # Remove temp directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_handle_output_dataframe(self):
        """Test saving DataFrame as Parquet file using Hive-standard path."""
        # Arrange
        df = pd.DataFrame({"col1": [1, 2, 3], "col2": [4, 5, 6]})
        context = dg.build_output_context(asset_key=dg.AssetKey(["test", "asset"]))
        # Hive-standard: {asset}/data.parquet
        want_file = self.temp_dir / "test" / "asset" / "data.parquet"

        # Act
        self.io_manager.handle_output(context, df)
        got_file_exists = want_file.exists()

        # Assert
        assert got_file_exists, f"Expected file at {want_file}"
        # Verify we can read it back
        loaded_df = pd.read_parquet(want_file)
        assert loaded_df.equals(df)

    def test_handle_output_dict(self):
        """Test saving dict as JSON file using Hive-standard path."""
        # Arrange
        data = {"key": "value", "number": 42, "nested": {"inner": "data"}}
        context = dg.build_output_context(asset_key=dg.AssetKey(["test", "snapshot"]))
        # Hive-standard: {asset}/data.json
        want_file = self.temp_dir / "test" / "snapshot" / "data.json"

        # Act
        self.io_manager.handle_output(context, data)
        got_file_exists = want_file.exists()

        # Assert
        assert got_file_exists, f"Expected file at {want_file}"
        # Verify we can read it back
        with open(want_file) as f:
            loaded_data = json.load(f)
        assert loaded_data == data

    def test_handle_output_creates_directories(self):
        """Test that handle_output creates nested directories."""
        # Arrange
        df = pd.DataFrame({"col": [1, 2]})
        context = dg.build_output_context(
            asset_key=dg.AssetKey(["level1", "level2", "level3", "asset"])
        )
        # Hive-standard: directory is {asset}/ which contains data.parquet
        want_dir = self.temp_dir / "level1" / "level2" / "level3" / "asset"

        # Act
        self.io_manager.handle_output(context, df)
        got_dir_exists = want_dir.exists()

        # Assert
        assert got_dir_exists, f"Expected directory at {want_dir}"

    def test_load_input_dataframe(self):
        """Test loading DataFrame from Parquet file."""
        # Arrange
        want_df = pd.DataFrame({"col1": [1, 2, 3], "col2": [4, 5, 6]})
        asset_key = dg.AssetKey(["test", "asset"])
        context = dg.build_output_context(asset_key=asset_key)
        # Save it first
        self.io_manager.handle_output(context, want_df)

        # Act
        load_context = dg.build_input_context(asset_key=asset_key)
        got_df = self.io_manager.load_input(load_context)

        # Assert
        assert isinstance(got_df, pd.DataFrame)
        assert got_df.equals(want_df)

    def test_load_input_dict(self):
        """Test loading dict from JSON file."""
        # Arrange
        want_data = {"key": "value", "number": 42}
        asset_key = dg.AssetKey(["test", "snapshot"])
        context = dg.build_output_context(asset_key=asset_key)
        # Save it first
        self.io_manager.handle_output(context, want_data)

        # Act
        load_context = dg.build_input_context(asset_key=asset_key)
        got_data = self.io_manager.load_input(load_context)

        # Assert
        assert isinstance(got_data, dict)
        assert got_data == want_data

    def test_get_path_without_extension_hierarchical(self):
        """Test that _get_path_without_extension creates Hive-standard paths."""
        # Arrange
        context = dg.build_output_context(
            asset_key=dg.AssetKey(["bronze", "fred", "timeseries"])
        )
        # Hive-standard: {asset}/data (extension added later)
        want_path = UPath(self.temp_dir) / "bronze" / "fred" / "timeseries" / "data"

        # Act
        got_path = self.io_manager._get_path_without_extension(context)

        # Assert
        assert got_path == want_path

    def test_handle_output_unsupported_type(self):
        """Test that unsupported types raise TypeError."""
        # Arrange
        unsupported_data = [1, 2, 3]  # List is not supported
        context = dg.build_output_context(asset_key=dg.AssetKey(["test", "asset"]))

        # Act & Assert
        with pytest.raises(TypeError, match="No handler for type"):
            self.io_manager.handle_output(context, unsupported_data)

    def test_partitioned_asset_saves_to_correct_path(self):
        """Test partitioned assets save to Hive-style path without double-partitioning.

        Verifies the path is partition=USA/data.parquet, not partition=USA/data/USA.parquet.
        """
        # Arrange
        df = pd.DataFrame({"col1": [1, 2, 3], "value": [100, 200, 300]})
        asset_key = dg.AssetKey(["bronze", "test", "partitioned_asset"])
        partition_key = "USA"

        output_context = dg.build_output_context(
            asset_key=asset_key,
            partition_key=partition_key,
        )

        want_path = (
            self.temp_dir
            / "bronze"
            / "test"
            / "partitioned_asset"
            / "partition=USA"
            / "data.parquet"
        )

        # Act - mock _get_partition_key to simulate a truly partitioned asset
        # (build_output_context doesn't properly support partitions_def)
        with patch.object(
            self.io_manager, "_get_partition_key", return_value=partition_key
        ):
            self.io_manager.handle_output(output_context, df)

        # Assert
        assert want_path.exists(), f"Expected file at {want_path}"

        # Verify data was saved correctly
        got_df = pd.read_parquet(want_path)
        assert got_df.equals(df)

    def test_unpartitioned_asset_ignores_job_partition_key(self):
        """Test unpartitioned assets ignore partition_key from partitioned job context.

        When an unpartitioned asset runs in a partitioned job (e.g., job with USA partition),
        the asset should still save to Hive-standard unpartitioned path, not partition=USA/.
        """
        # Arrange
        df = pd.DataFrame({"col1": [1, 2, 3], "value": [100, 200, 300]})
        asset_key = dg.AssetKey(["bronze", "bls", "all_series"])

        # Simulate unpartitioned asset in partitioned job context
        # partition_key is set but has_asset_partitions will be False
        output_context = dg.build_output_context(
            asset_key=asset_key,
            partition_key="USA",  # Job has partition, but asset doesn't
        )

        # Hive-standard unpartitioned path: {asset}/data.parquet
        want_path = self.temp_dir / "bronze" / "bls" / "all_series" / "data.parquet"
        bad_path = (
            self.temp_dir
            / "bronze"
            / "bls"
            / "all_series"
            / "partition=USA"
            / "data.parquet"
        )

        # Act
        self.io_manager.handle_output(output_context, df)

        # Assert - should be at unpartitioned Hive-standard path
        assert want_path.exists(), f"Expected file at {want_path}"
        assert not bad_path.parent.exists(), (
            f"Should NOT create partition directory: {bad_path.parent}"
        )

        # Verify data
        got_df = pd.read_parquet(want_path)
        assert got_df.equals(df)

    def test_lazyframe_output_cleans_old_single_file(self):
        """Test that writing LazyFrame removes old data.parquet file.

        When switching from DataFrame (single file) to LazyFrame (sharded),
        the old data.parquet should be removed to prevent schema conflicts.
        """
        # Arrange - create old single file format
        asset_dir = self.temp_dir / "bronze" / "test" / "asset"
        asset_dir.mkdir(parents=True)
        old_file = asset_dir / "data.parquet"

        # Create old DataFrame file with different schema
        old_df = pd.DataFrame({"old_col": [1, 2, 3]})
        old_df.to_parquet(old_file)
        assert old_file.exists(), "Setup: old file should exist"

        # Create new LazyFrame
        new_lf = pl.DataFrame({"new_col": ["a", "b", "c"]}).lazy()
        context = dg.build_output_context(
            asset_key=dg.AssetKey(["bronze", "test", "asset"])
        )

        # Act
        self.io_manager.handle_output(context, new_lf)

        # Assert - old file should be removed
        assert not old_file.exists(), "Old data.parquet should be removed"

        # Assert - new shard files should exist
        shard_files = list(asset_dir.glob("part-*.parquet"))
        assert len(shard_files) > 0, "New shard files should exist"

    def test_dataframe_output_cleans_old_shard_files(self):
        """Test that writing DataFrame removes old part-*.parquet files.

        When switching from LazyFrame (sharded) to DataFrame (single file),
        the old shard files should be removed to prevent schema conflicts.
        """
        # Arrange - create old shard files
        asset_dir = self.temp_dir / "bronze" / "test" / "asset"
        asset_dir.mkdir(parents=True)

        # Create fake old shard files
        (asset_dir / "part-0000.parquet").write_bytes(b"dummy")
        (asset_dir / "part-0001.parquet").write_bytes(b"dummy")
        old_shards = list(asset_dir.glob("part-*.parquet"))
        assert len(old_shards) == 2, "Setup: old shards should exist"

        # Create new DataFrame
        new_df = pd.DataFrame({"new_col": [1, 2, 3]})
        context = dg.build_output_context(
            asset_key=dg.AssetKey(["bronze", "test", "asset"])
        )

        # Act
        self.io_manager.handle_output(context, new_df)

        # Assert - old shard files should be removed
        remaining_shards = list(asset_dir.glob("part-*.parquet"))
        assert len(remaining_shards) == 0, "Old shard files should be removed"

        # Assert - new single file should exist
        data_file = asset_dir / "data.parquet"
        assert data_file.exists(), "New data.parquet should exist"


class TestParquetHandler:
    """Test suite for ParquetHandler."""

    def setup_method(self):
        """Set up test fixtures before each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.handler = ParquetHandler()

    def teardown_method(self):
        """Clean up after each test."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_supported_type(self):
        """Test that ParquetHandler supports DataFrame type."""
        # Arrange
        want_type = pd.DataFrame

        # Act
        got_type = self.handler.supported_type

        # Assert
        assert got_type == want_type

    def test_extension(self):
        """Test that ParquetHandler uses .parquet extension."""
        # Arrange
        want_extension = ".parquet"

        # Act
        got_extension = self.handler.extension

        # Assert
        assert got_extension == want_extension

    def test_dump_and_load(self):
        """Test that ParquetHandler can dump and load DataFrames."""
        # Arrange
        want_df = pd.DataFrame({"col1": [1, 2, 3], "col2": [4, 5, 6]})
        path = UPath(self.temp_dir) / "test.parquet"

        # Act - dump
        self.handler.dump(want_df, path)
        got_file_exists = path.exists()

        # Assert - file exists
        assert got_file_exists

        # Act - load
        got_df = self.handler.load(path)

        # Assert - loaded data matches
        assert got_df.equals(want_df)


class TestJSONHandler:
    """Test suite for JSONHandler."""

    def setup_method(self):
        """Set up test fixtures before each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.handler = JSONHandler()

    def teardown_method(self):
        """Clean up after each test."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_supported_type(self):
        """Test that JSONHandler supports dict type."""
        # Arrange
        want_type = dict

        # Act
        got_type = self.handler.supported_type

        # Assert
        assert got_type == want_type

    def test_extension(self):
        """Test that JSONHandler uses .json extension."""
        # Arrange
        want_extension = ".json"

        # Act
        got_extension = self.handler.extension

        # Assert
        assert got_extension == want_extension

    def test_dump_and_load(self):
        """Test that JSONHandler can dump and load dicts."""
        # Arrange
        want_data = {"key": "value", "number": 42, "nested": {"inner": "data"}}
        path = UPath(self.temp_dir) / "test.json"

        # Act - dump
        self.handler.dump(want_data, path)
        got_file_exists = path.exists()

        # Assert - file exists
        assert got_file_exists

        # Act - load
        got_data = self.handler.load(path)

        # Assert - loaded data matches
        assert got_data == want_data
