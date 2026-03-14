"""Auth service implementations."""

from fastapi import Depends, HTTPException, status
from supabase import Client

from src.lib.auth.models import AuthContext
from src.lib.supabase.client import (
    get_supabase_client,
    get_supabase_user_client_optional,
    get_supabase_admin_client,
)

from .schema import LoginRequest, SetPasswordRequest


class AuthService:
    """Service for Supabase auth flows."""

    def __init__(
        self,
        supabase: Client = Depends(get_supabase_client),
        supabase_user: Client | None = Depends(get_supabase_user_client_optional),
        admin_client: Client = Depends(get_supabase_admin_client),
    ):
        self.supabase = supabase
        self.supabase_user = supabase_user
        self.admin = admin_client

    async def login(self, data: LoginRequest) -> dict:
        result = self.supabase.auth.sign_in_with_password(
            {"email": data.email, "password": data.password}
        )
        if result.session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        return {
            "access_token": result.session.access_token,
            "refresh_token": result.session.refresh_token,
            "token_type": result.session.token_type,
            "expires_in": result.session.expires_in,
            "user": result.user.model_dump() if result.user else None,
        }

    async def set_password(self, user: AuthContext, data: SetPasswordRequest) -> None:
        if not self.supabase_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        result = self.supabase_user.auth.update_user({"password": data.password})
        if not result.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to set password",
            )
            
        # Helper to activate invites
        try:
            from datetime import datetime, timezone
            self.admin.table("tenant_users").update({
                "status": "active",
                "accepted_at": datetime.now(timezone.utc).isoformat()
            }).eq("user_id", user.id).eq("status", "invited").execute()
        except Exception as e:
            # Non-blocking
            print(f"Failed to activate invitations: {e}")
