"""User API routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.lib.auth.dependencies import get_current_user
from .schema import CurrentUserResponse, UserProfileResponse, UserProfileUpdate
from .service import UserService

router = APIRouter()


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user_info(
    user=Depends(get_current_user),
    service: UserService = Depends(),
):
    """Get current authenticated user info."""
    return await service.get_current_user_info(user)


@router.get("/me/profile", response_model=UserProfileResponse)
async def get_my_profile(
    user=Depends(get_current_user),
    service: UserService = Depends(),
):
    """Get current user's profile."""
    profile = await service.get_profile_self(user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    return profile


@router.put("/me/profile", response_model=UserProfileResponse)
async def update_my_profile(
    data: UserProfileUpdate,
    user=Depends(get_current_user),
    service: UserService = Depends(),
):
    """Update current user's profile."""
    return await service.update_profile_self(user.id, data)
