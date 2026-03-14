"""Variable API routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.lib.auth.dependencies import get_current_user

from .schema import VariableCreate, VariableResponse, VariableUpdate
from .service import VariableService

router = APIRouter()


@router.get("", response_model=list[VariableResponse])
async def list_variables(
    _user=Depends(get_current_user),
    service: VariableService = Depends(),
):
    """List all variables."""
    return await service.list()


@router.get("/{variable_id}", response_model=VariableResponse)
async def get_variable(
    variable_id: str,
    _user=Depends(get_current_user),
    service: VariableService = Depends(),
):
    """Get a variable by ID."""
    variable = await service.get_by_id(variable_id)
    if not variable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variable not found",
        )
    return variable


@router.post("", response_model=VariableResponse, status_code=status.HTTP_201_CREATED)
async def create_variable(
    data: VariableCreate,
    _user=Depends(get_current_user),
    service: VariableService = Depends(),
):
    """Create a new variable."""
    return await service.create(data)


@router.put("/{variable_id}", response_model=VariableResponse)
async def update_variable(
    variable_id: str,
    data: VariableUpdate,
    _user=Depends(get_current_user),
    service: VariableService = Depends(),
):
    """Update an existing variable."""
    # Ensure the ID matches
    data.id = variable_id
    return await service.update(data)


@router.delete("/{variable_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variable(
    variable_id: str,
    _user=Depends(get_current_user),
    service: VariableService = Depends(),
):
    """Delete a variable."""
    deleted = await service.delete(variable_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variable not found",
        )
