"""Supabase client configuration."""

from functools import lru_cache

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client

from src.app.config import get_settings
from supabase._sync.client import SyncMemoryStorage

try:
    from supabase.lib.client_options import ClientOptions
except Exception:  # pragma: no cover - optional dependency in older supabase-py
    ClientOptions = None

security = HTTPBearer()


def _build_client_options(headers: dict) -> object:
    """Build a supabase client options object compatible with current SDK."""
    if ClientOptions is not None:
        options = ClientOptions()
        options.headers = headers
    else:
        class _Options:
            pass
        options = _Options()
        options.headers = headers
        options.schema = "public"
        options.realtime = None
        options.auto_refresh_token = True
        options.persist_session = True
        options.flow_type = "pkce"
        options.postgrest_client_timeout = 60
        options.storage_client_timeout = 60
        options.function_client_timeout = 60
        options.httpx_client = None
    # Ensure attributes expected by newer supabase client exist.
    if not hasattr(options, "storage"):
        options.storage = SyncMemoryStorage()
    if not hasattr(options, "httpx_client"):
        options.httpx_client = None
    if not hasattr(options, "auto_refresh_token"):
        options.auto_refresh_token = True
    if not hasattr(options, "persist_session"):
        options.persist_session = True
    if not hasattr(options, "flow_type"):
        options.flow_type = "pkce"
    if not hasattr(options, "schema"):
        options.schema = "public"
    if not hasattr(options, "realtime"):
        options.realtime = None
    return options


@lru_cache
def get_supabase_client() -> Client:
    """Get cached Supabase client instance.

    Uses the anon key by default for RLS-protected queries.
    For service-level operations, use get_supabase_service_client().

    Raises:
        RuntimeError: If SUPABASE_URL or SUPABASE_ANON_KEY are not configured.
    """
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise RuntimeError(
            "Supabase not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY "
            "environment variables, or use playground routes only."
        )
    return create_client(settings.supabase_url, settings.supabase_anon_key)


@lru_cache
def get_supabase_service_client() -> Client | None:
    """Get cached Supabase service client (bypasses RLS).

    Returns None if Supabase is not configured or service role key is missing.
    Use this only for administrative operations.
    """
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_supabase_admin_client() -> Client:
    """Return service-role client or raise if not configured."""
    client = get_supabase_service_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_SERVICE_ROLE_KEY is not configured",
        )
    return client


def get_supabase_user_client(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> Client:
    """Return a Supabase client bound to the user's JWT for RLS."""
    settings = get_settings()
    token = credentials.credentials
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": settings.supabase_anon_key,
    }
    options = _build_client_options(headers)
    return create_client(settings.supabase_url, settings.supabase_anon_key, options)


def get_supabase_user_client_optional(
    credentials: HTTPAuthorizationCredentials | None = Security(
        HTTPBearer(auto_error=False)
    ),
) -> Client | None:
    """Return a Supabase client bound to the user's JWT, or None if missing."""
    if credentials is None:
        return None
    settings = get_settings()
    token = credentials.credentials
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": settings.supabase_anon_key,
    }
    options = _build_client_options(headers)
    return create_client(settings.supabase_url, settings.supabase_anon_key, options)


def create_supabase_anon_client(extra_headers: dict | None = None) -> Client:
    """Create a Supabase client with anon key and optional headers."""
    settings = get_settings()
    headers = {"apikey": settings.supabase_anon_key}
    if extra_headers:
        headers.update(extra_headers)
    options = _build_client_options(headers)
    return create_client(settings.supabase_url, settings.supabase_anon_key, options)
