"""Tests for environment configuration and management."""

import pytest

from shared.data import (
    EnvironmentNotFoundError,
    current_env,
    env,
    list_environments,
    use_env,
)
from shared.data.assets import EnvironmentConfig, S3Config, get_environment


class TestEnvironmentConfig:
    """Tests for EnvironmentConfig dataclass."""

    def test_environment_structure(self):
        """Test that environment config has expected fields."""
        config = EnvironmentConfig(
            name="test",
            base_path="_data/test",
            can_write=True,
            description="Test environment",
        )

        assert config.name == "test"
        assert config.base_path == "_data/test"
        assert config.can_write is True
        assert config.description == "Test environment"


class TestGetEnvironment:
    """Tests for get_environment function."""

    def test_get_local_environment(self):
        """Test retrieving local environment."""
        config = get_environment("local")

        assert config.name == "local"
        assert config.can_write is True
        assert isinstance(config.description, str)

    def test_get_prod_environment(self):
        """Test retrieving prod environment."""
        config = get_environment("prod")

        assert config.name == "prod"
        assert config.can_write is False  # Prod should be read-only
        assert isinstance(config.description, str)

    def test_get_nonexistent_environment(self):
        """Test error when environment doesn't exist."""
        with pytest.raises(EnvironmentNotFoundError) as exc_info:
            get_environment("nonexistent")

        error = exc_info.value
        assert error.env_name == "nonexistent"
        assert "local" in error.available
        assert "prod" in error.available


class TestListEnvironments:
    """Tests for list_environments function."""

    def test_lists_environments(self):
        """Test that list_environments returns expected environments."""
        environments = list_environments()

        assert isinstance(environments, list)
        assert "local" in environments
        assert "prod" in environments


class TestCurrentEnv:
    """Tests for current_env function."""

    def test_default_environment(self):
        """Test that default environment is prod."""
        # Reset to default
        use_env("prod")

        want_env = "prod"
        got_env = current_env()
        assert got_env == want_env


class TestUseEnv:
    """Tests for use_env function."""

    def test_switch_to_local(self):
        """Test switching to local environment."""
        use_env("local")

        want_env = "local"
        got_env = current_env()
        assert got_env == want_env

        # Cleanup: reset to prod
        use_env("prod")

    def test_switch_to_prod(self):
        """Test switching to prod environment."""
        use_env("prod")

        want_env = "prod"
        got_env = current_env()
        assert got_env == want_env

    def test_switch_to_nonexistent(self):
        """Test error when switching to nonexistent environment."""
        with pytest.raises(EnvironmentNotFoundError):
            use_env("nonexistent")

        # Current env should be unchanged
        assert current_env() in ["local", "prod"]


class TestEnvContextManager:
    """Tests for env context manager."""

    def test_temporary_switch(self):
        """Test temporarily switching environment."""
        # Start with prod
        use_env("prod")
        want_initial = "prod"
        got_initial = current_env()
        assert got_initial == want_initial

        # Switch to local temporarily
        with env("local"):
            want_temp = "local"
            got_temp = current_env()
            assert got_temp == want_temp

        # Should be back to prod
        want_final = "prod"
        got_final = current_env()
        assert got_final == want_final

    def test_nested_context_managers(self):
        """Test nested environment switches."""
        use_env("prod")

        with env("local"):
            assert current_env() == "local"

            with env("prod"):
                assert current_env() == "prod"

            # Back to local
            assert current_env() == "local"

        # Back to prod
        assert current_env() == "prod"

    def test_exception_in_context(self):
        """Test that environment is restored even if exception occurs."""
        use_env("prod")

        try:
            with env("local"):
                assert current_env() == "local"
                raise ValueError("test error")
        except ValueError:
            pass

        # Should still be back to prod
        want_env = "prod"
        got_env = current_env()
        assert got_env == want_env

    def test_context_with_nonexistent_env(self):
        """Test error when context manager given nonexistent env."""
        with pytest.raises(EnvironmentNotFoundError), env("nonexistent"):
            pass

        # Current env should be unchanged
        assert current_env() in ["local", "prod"]


class TestS3Config:
    """Tests for S3Config dataclass."""

    def test_s3_config_structure(self):
        """Test S3Config has expected fields."""
        config = S3Config(
            endpoint_url="https://example.com/s3",
            bucket="test-bucket",
            region="us-east-1",
        )

        assert config.endpoint_url == "https://example.com/s3"
        assert config.bucket == "test-bucket"
        assert config.region == "us-east-1"


class TestDevEnvironment:
    """Tests for dev environment configuration."""

    def test_get_dev_environment(self):
        """Test retrieving dev environment."""
        config = get_environment("dev")

        assert config.name == "dev"
        assert config.can_write is True
        assert config.base_path == "s3://actbi_pipelines_dev"
        assert config.s3_config is not None
        assert config.s3_config.bucket == "actbi_pipelines_dev"

    def test_dev_in_list_environments(self):
        """Test that dev is in the list of available environments."""
        environments = list_environments()
        assert "dev" in environments

    def test_local_has_no_s3_config(self):
        """Test that local environment has no S3 config."""
        config = get_environment("local")
        assert config.s3_config is None

    def test_prod_has_no_s3_config(self):
        """Test that prod environment has no S3 config."""
        config = get_environment("prod")
        assert config.s3_config is None
