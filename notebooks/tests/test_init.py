"""Tests for notebook initialization module."""


class TestInit:
    """Tests for notebooks.init module."""

    def test_init_imports_successfully(self, monkeypatch):
        """Test that init module can be imported and executed."""
        # Set a test data path to avoid path resolution issues
        monkeypatch.setenv("ACTBI_DATA_PATH", "/tmp/test_assets")

        # Import should succeed and set up environment
        from notebooks import init

        # Verify data module is available
        assert hasattr(init, "data")

    def test_init_sets_local_environment(self, monkeypatch):
        """Test that init configures local environment."""
        monkeypatch.setenv("ACTBI_DATA_PATH", "/tmp/test_assets")

        from notebooks import init  # noqa: F401

        got = init.data.current_env()
        want = "local"

        assert got == want

    def test_init_provides_pandas(self, monkeypatch):
        """Test that init provides pandas as pd."""
        monkeypatch.setenv("ACTBI_DATA_PATH", "/tmp/test_assets")

        from notebooks import init

        assert hasattr(init, "pd")
        assert init.pd.__name__ == "pandas"

    def test_init_provides_matplotlib(self, monkeypatch):
        """Test that init provides matplotlib.pyplot as plt."""
        monkeypatch.setenv("ACTBI_DATA_PATH", "/tmp/test_assets")

        from notebooks import init

        assert hasattr(init, "plt")
