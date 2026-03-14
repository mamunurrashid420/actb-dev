"""Prompt API routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.lib.auth.dependencies import get_current_user

from .schema import PromptCreate, PromptResponse, PromptUpdate
from .service import PromptService

router = APIRouter()


@router.get("", response_model=list[PromptResponse])
async def list_prompts(
    _user=Depends(get_current_user),
    service: PromptService = Depends(),
):
    """List all prompts."""
    return await service.list()


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: str,
    _user=Depends(get_current_user),
    service: PromptService = Depends(),
):
    """Get a prompt by ID."""
    prompt = await service.get_by_id(prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found",
        )
    return prompt


@router.post("", response_model=PromptResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    data: PromptCreate,
    _user=Depends(get_current_user),
    service: PromptService = Depends(),
):
    """Create a new prompt."""
    return await service.create(data)


@router.put("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: str,
    data: PromptUpdate,
    _user=Depends(get_current_user),
    service: PromptService = Depends(),
):
    """Update an existing prompt."""
    data.id = prompt_id
    return await service.update(data)


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: str,
    _user=Depends(get_current_user),
    service: PromptService = Depends(),
):
    """Delete a prompt."""
    deleted = await service.delete(prompt_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found",
        )
