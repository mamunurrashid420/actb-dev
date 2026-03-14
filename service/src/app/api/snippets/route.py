"""Snippet API routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.lib.auth.dependencies import get_current_user

from .schema import SnippetCreate, SnippetResponse, SnippetUpdate
from .service import SnippetService

router = APIRouter()


@router.get("", response_model=list[SnippetResponse])
async def list_snippets(
    _user=Depends(get_current_user),
    service: SnippetService = Depends(),
):
    """List all snippets."""
    return await service.list()


@router.get("/{snippet_id}", response_model=SnippetResponse)
async def get_snippet(
    snippet_id: str,
    _user=Depends(get_current_user),
    service: SnippetService = Depends(),
):
    """Get a snippet by ID."""
    snippet = await service.get_by_id(snippet_id)
    if not snippet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snippet not found",
        )
    return snippet


@router.post("", response_model=SnippetResponse, status_code=status.HTTP_201_CREATED)
async def create_snippet(
    data: SnippetCreate,
    _user=Depends(get_current_user),
    service: SnippetService = Depends(),
):
    """Create a new snippet."""
    return await service.create(data)


@router.put("/{snippet_id}", response_model=SnippetResponse)
async def update_snippet(
    snippet_id: str,
    data: SnippetUpdate,
    _user=Depends(get_current_user),
    service: SnippetService = Depends(),
):
    """Update an existing snippet."""
    data.id = snippet_id
    return await service.update(data)


@router.delete("/{snippet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_snippet(
    snippet_id: str,
    _user=Depends(get_current_user),
    service: SnippetService = Depends(),
):
    """Delete a snippet."""
    deleted = await service.delete(snippet_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snippet not found",
        )
