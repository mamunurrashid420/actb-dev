"""Authentication dependencies for FastAPI."""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from src.lib.auth.jwt import decode_access_token
from src.lib.auth.models import AuthContext
from src.lib.supabase.client import get_supabase_admin_client, get_supabase_user_client

security = HTTPBearer()


def get_access_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    return credentials.credentials


async def get_current_user(
    token: str = Depends(get_access_token),
) -> AuthContext:
    """Validate Supabase JWT and return auth context."""
    try:
        claims = decode_access_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    return AuthContext(
        id=user_id,
        email=claims.get("email"),
        claims=claims,
    )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Security(
        HTTPBearer(auto_error=False)
    ),
) -> AuthContext | None:
    """Get current user if authenticated, None otherwise."""
    if credentials is None:
        return None

    try:
        return await get_current_user(token=credentials.credentials)
    except HTTPException:
        return None


async def require_tenant_member(
    tenant_id: str,
    _user: AuthContext = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_user_client),
) -> None:
    """Optional membership guard; RLS remains the source of truth."""
    result = (
        supabase.table("tenant_users")
        .select("tenant_id")
        .eq("tenant_id", tenant_id)
        .eq("user_id", _user.id)
        .eq("status", "active")
        .maybe_single()
        .execute()
    )
    if result.data is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a tenant member",
        )


async def require_superadmin(
    user: AuthContext = Depends(get_current_user),
) -> AuthContext:
    """Validate that the user is a superadmin."""
    role = user.claims.get("role")
    is_admin = user.claims.get("is_app_admin")
    if role == "app_admin" or is_admin is True:
        return user

    # Fallback: check user_profiles.is_app_admin via service role.
    supabase = get_supabase_admin_client()
    result = (
        supabase.table("user_profiles")
        .select("is_app_admin")
        .eq("id", user.id)
        .maybe_single()
        .execute()
    )
    if result.data and result.data.get("is_app_admin") is True:
        return user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Superadmin privileges required",
    )
