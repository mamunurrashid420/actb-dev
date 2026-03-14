"""Tests for AssetStore."""

import shutil
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from shared.io.store import AssetStore


class TestAssetStore:
    """Tests for AssetStore."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def store(self, temp_dir):
        """Create AssetStore instance."""
        return AssetStore(temp_dir)

    def test_save_and_load_dataframe(self, store):
        """Test saving and loading a DataFrame."""
        # Arrange
        want_df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        asset_path = "test/data"

        # Act
        store.save(asset_path, want_df)
        got_df = store.load(asset_path)

        # Assert
        pd.testing.assert_frame_equal(got_df, want_df)

    def test_save_and_load_dict(self, store):
        """Test saving and loading a dict."""
        # Arrange
        want_data = {"key": "value", "number": 42}
        asset_path = "test/config"

        # Act
        store.save(asset_path, want_data)
        got_data = store.load(asset_path)

        # Assert
        assert got_data == want_data

    def test_save_and_load_with_partition(self, store):
        """Test saving and loading with single partition."""
        # Arrange
        want_df = pd.DataFrame({"value": [100, 200]})
        asset_path = "bronze/fred/timeseries"
        partition = "GDP"

        # Act
        store.save(asset_path, want_df, partition_key=partition)
        got_df = store.load(asset_path, partition_key=partition)

        # Assert
        pd.testing.assert_frame_equal(got_df, want_df)

    def test_save_and_load_with_dict_partition(self, store):
        """Test saving and loading with multi-dimensional partition."""
        # Arrange
        want_df = pd.DataFrame({"value": [1000]})
        asset_path = "bronze/world_bank/data"
        partition = {"country": "USA", "indicator": "GDP"}

        # Act
        store.save(asset_path, want_df, partition_key=partition)
        got_df = store.load(asset_path, partition_key=partition)

        # Assert
        pd.testing.assert_frame_equal(got_df, want_df)

    def test_resolve_path_nonpartitioned(self, store, temp_dir):
        """Test path resolution for non-partitioned asset uses Hive-standard."""
        # Arrange
        asset_path = "silver/reference/crosswalk"

        # Act
        got_path = store.resolve_path(asset_path)

        # Assert - Hive-standard: {asset}/data (not {asset}.parquet)
        assert str(got_path).endswith("silver/reference/crosswalk/data")

    def test_resolve_path_single_partition(self, store, temp_dir):
        """Test path resolution with single partition."""
        # Arrange
        asset_path = "bronze/fred/timeseries"
        partition = "GDP"

        # Act
        got_path = store.resolve_path(asset_path, partition_key=partition)

        # Assert
        assert "partition=GDP" in str(got_path)
        assert str(got_path).endswith("data")

    def test_resolve_path_dict_partition(self, store, temp_dir):
        """Test path resolution with multi-dimensional partition."""
        # Arrange
        asset_path = "bronze/data"
        partition = {"country": "USA", "indicator": "GDP"}

        # Act
        got_path = store.resolve_path(asset_path, partition_key=partition)

        # Assert - dimensions sorted alphabetically
        assert "country=USA" in str(got_path)
        assert "indicator=GDP" in str(got_path)
        assert str(got_path).endswith("data")

    def test_exists_true(self, store):
        """Test exists returns True for existing asset."""
        # Arrange
        df = pd.DataFrame({"col": [1]})
        asset_path = "test/exists"
        store.save(asset_path, df)

        # Act
        got = store.exists(asset_path)

        # Assert
        assert got is True

    def test_exists_false(self, store):
        """Test exists returns False for non-existing asset."""
        # Act
        got = store.exists("nonexistent/asset")

        # Assert
        assert got is False

    def test_exists_with_partition(self, store):
        """Test exists works with partitioned assets."""
        # Arrange
        df = pd.DataFrame({"col": [1]})
        asset_path = "partitioned/asset"
        store.save(asset_path, df, partition_key="A")

        # Act/Assert
        assert store.exists(asset_path, partition_key="A") is True
        assert store.exists(asset_path, partition_key="B") is False

    def test_load_nonexistent_raises(self, store):
        """Test loading non-existent asset raises FileNotFoundError."""
        # Act/Assert
        with pytest.raises(FileNotFoundError):
            store.load("does/not/exist")

    def test_creates_directories(self, store, temp_dir):
        """Test that save creates necessary directories."""
        # Arrange
        df = pd.DataFrame({"col": [1]})
        asset_path = "deeply/nested/path/asset"

        # Act
        store.save(asset_path, df)

        # Assert
        expected_dir = temp_dir / "deeply" / "nested" / "path"
        assert expected_dir.exists()

    def test_unsupported_type_raises(self, store):
        """Test saving unsupported type raises TypeError."""
        # Act/Assert
        with pytest.raises(TypeError):
            store.save("test/asset", ["not", "supported"])
