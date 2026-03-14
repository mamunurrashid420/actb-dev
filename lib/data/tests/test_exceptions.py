"""Tests for data library exceptions."""

import pytest

from shared.data.exceptions import (
    AssetNotFoundError,
    DataLibraryError,
    EnvironmentNotFoundError,
    EnvironmentPermissionError,
    PartitionNotFoundError,
)


class TestDataLibraryError:
    """Tests for base exception class."""

    def test_is_exception(self):
        """Test that DataLibraryError is an Exception."""
        assert issubclass(DataLibraryError, Exception)

    def test_can_be_raised(self):
        """Test that DataLibraryError can be raised."""
        with pytest.raises(DataLibraryError):
            raise DataLibraryError("test error")


class TestAssetNotFoundError:
    """Tests for AssetNotFoundError."""

    def test_basic_error(self):
        """Test error without suggestions."""
        with pytest.raises(AssetNotFoundError) as exc_info:
            raise AssetNotFoundError("economic/growth/gdp")

        want_asset_path = "economic/growth/gdp"
        got_asset_path = exc_info.value.asset_path
        assert got_asset_path == want_asset_path

        want_suggestions = []
        got_suggestions = exc_info.value.suggestions
        assert got_suggestions == want_suggestions

    def test_error_with_suggestions(self):
        """Test error includes suggestions in message."""
        suggestions = ["economic/labor/gdp", "economic/growth/gdp_real"]

        with pytest.raises(AssetNotFoundError) as exc_info:
            raise AssetNotFoundError("economic/growth/gdp", suggestions=suggestions)

        error_message = str(exc_info.value)
        assert "Did you mean" in error_message
        assert "economic/labor/gdp" in error_message
        assert "economic/growth/gdp_real" in error_message

    def test_limits_suggestions(self):
        """Test that only first 5 suggestions are shown."""
        suggestions = [f"asset_{i}" for i in range(10)]

        with pytest.raises(AssetNotFoundError) as exc_info:
            raise AssetNotFoundError("test/asset", suggestions=suggestions)

        error_message = str(exc_info.value)
        # Should show first 5
        for i in range(5):
            assert f"asset_{i}" in error_message
        # Should not show beyond 5
        assert "asset_5" not in error_message


class TestPartitionNotFoundError:
    """Tests for PartitionNotFoundError."""

    def test_basic_error(self):
        """Test error without available partitions."""
        with pytest.raises(PartitionNotFoundError) as exc_info:
            raise PartitionNotFoundError("economic/growth/gdp", "XX")

        want_asset_path = "economic/growth/gdp"
        got_asset_path = exc_info.value.asset_path
        assert got_asset_path == want_asset_path

        want_partition = "XX"
        got_partition = exc_info.value.partition
        assert got_partition == want_partition

    def test_error_with_available_partitions(self):
        """Test error includes available partitions."""
        available = ["US", "CN", "JP"]

        with pytest.raises(PartitionNotFoundError) as exc_info:
            raise PartitionNotFoundError(
                "economic/growth/gdp", "XX", available=available
            )

        error_message = str(exc_info.value)
        assert "Available partitions" in error_message
        assert "US" in error_message
        assert "CN" in error_message
        assert "JP" in error_message

    def test_limits_displayed_partitions(self):
        """Test that only first 10 partitions are shown."""
        available = [f"P{i:03d}" for i in range(20)]

        with pytest.raises(PartitionNotFoundError) as exc_info:
            raise PartitionNotFoundError("test/asset", "XXX", available=available)

        error_message = str(exc_info.value)
        # Should show count
        assert "20 total" in error_message
        # Should show first 10
        assert "P000" in error_message
        assert "P009" in error_message
        # Should indicate more
        assert "and 10 more" in error_message


class TestEnvironmentNotFoundError:
    """Tests for EnvironmentNotFoundError."""

    def test_basic_error(self):
        """Test error includes environment name."""
        available = ["local", "dev", "prod"]

        with pytest.raises(EnvironmentNotFoundError) as exc_info:
            raise EnvironmentNotFoundError("staging", available)

        want_env = "staging"
        got_env = exc_info.value.env_name
        assert got_env == want_env

        want_available = available
        got_available = exc_info.value.available
        assert got_available == want_available

    def test_error_lists_available(self):
        """Test error message lists available environments."""
        available = ["local", "dev", "prod"]

        with pytest.raises(EnvironmentNotFoundError) as exc_info:
            raise EnvironmentNotFoundError("staging", available)

        error_message = str(exc_info.value)
        assert "Available environments" in error_message
        assert "local" in error_message
        assert "dev" in error_message
        assert "prod" in error_message


class TestEnvironmentPermissionError:
    """Tests for EnvironmentPermissionError."""

    def test_basic_error(self):
        """Test error includes environment and context."""
        with pytest.raises(EnvironmentPermissionError) as exc_info:
            raise EnvironmentPermissionError("prod", "notebook")

        want_env = "prod"
        got_env = exc_info.value.env_name
        assert got_env == want_env

        want_context = "notebook"
        got_context = exc_info.value.context
        assert got_context == want_context

    def test_error_message_helpful(self):
        """Test error message explains the issue."""
        with pytest.raises(EnvironmentPermissionError) as exc_info:
            raise EnvironmentPermissionError("prod", "notebook")

        error_message = str(exc_info.value)
        assert "Cannot write to prod" in error_message
        assert "notebook" in error_message
        assert "read-only" in error_message
        assert "local or dev" in error_message
