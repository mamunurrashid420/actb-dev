from __future__ import annotations

import os
from unittest.mock import patch

from xlake.stores.config import (
    CustomerAppLogicStoreConfig,
    StoresConfig,
    load_stores_config,
)
from xlake.stores.settings import XLakeSettings


def test_load_config_sqlite() -> None:
    """Test loading config with explicit XLakeSettings for SQLite backend."""
    settings = XLakeSettings(local_sqlite_path=":memory:")

    with patch.dict(os.environ, {"APP_ENV": "development"}, clear=False):
        cfg = load_stores_config(settings=settings)

    assert isinstance(cfg, StoresConfig)
    assert cfg.env == "development"
    assert isinstance(cfg.customer_app_logic, CustomerAppLogicStoreConfig)
    assert cfg.customer_app_logic.backend == "sqlite"
    assert cfg.customer_app_logic.sqlite is not None
    assert cfg.customer_app_logic.sqlite.database_path == ":memory:"


def test_load_config_supabase() -> None:
    """Test loading config with explicit XLakeSettings for Supabase backend."""
    settings = XLakeSettings(
        customer_supabase_url="https://example.supabase.co",
        customer_supabase_service_key="sekret",
        customer_supabase_schema="custom",
    )

    with patch.dict(os.environ, {"APP_ENV": "production"}, clear=False):
        cfg = load_stores_config(settings=settings)

    assert cfg.env == "production"
    assert cfg.customer_app_logic.backend == "supabase"
    assert cfg.customer_app_logic.supabase is not None
    assert cfg.customer_app_logic.supabase.url == "https://example.supabase.co"
    assert cfg.customer_app_logic.supabase.api_key.get_secret_value() == "sekret"
    assert cfg.customer_app_logic.supabase.schema == "custom"
