"""Auth routes."""

from fastapi import APIRouter, Depends, status

from src.lib.auth.dependencies import get_current_user
from src.lib.supabase.client import get_supabase_admin_client

from .schema import AuthContextResponse, LoginRequest, LoginResponse, SetPasswordRequest
from .service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    data: LoginRequest,
    service: AuthService = Depends(),
):
    return await service.login(data)


@router.post("/set-password", status_code=status.HTTP_204_NO_CONTENT)
async def set_password(
    data: SetPasswordRequest,
    user=Depends(get_current_user),
    service: AuthService = Depends(),
):
    await service.set_password(user, data)
    return None


@router.get("/me", response_model=AuthContextResponse)
async def get_auth_context(user=Depends(get_current_user)):
    # Enrich claims with is_app_admin when possible.
    try:
        supabase = get_supabase_admin_client()
        result = (
            supabase.table("user_profiles")
            .select("is_app_admin")
            .eq("id", user.id)
            .maybe_single()
            .execute()
        )
        if result.data is not None:
            user.claims = user.claims or {}
            user.claims["is_app_admin"] = result.data.get("is_app_admin") is True
    except Exception:
        # Non-blocking; auth context still returns base claims.
        pass
    return user
