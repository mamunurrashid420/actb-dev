"""Conversation API routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.lib.auth.dependencies import get_current_user, require_tenant_member

from .schema import (
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    ConversationWithMessages,
    MessageCreate,
    MessageResponse,
)
from .service import ConversationService

router = APIRouter(prefix="/tenants/{tenant_id}/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    tenant_id: str,
    _user=Depends(get_current_user),
    _member=Depends(require_tenant_member),
    service: ConversationService = Depends(),
):
    """List all conversations for the current user."""
    return await service.list_for_user(tenant_id)


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    tenant_id: str,
    conversation_id: str,
    _user=Depends(get_current_user),
    _member=Depends(require_tenant_member),
    service: ConversationService = Depends(),
):
    """Get a conversation with all its messages."""
    conversation = await service.get_with_messages(tenant_id, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conversation


@router.post(
    "", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED
)
async def create_conversation(
    tenant_id: str,
    data: ConversationCreate,
    user=Depends(get_current_user),
    _member=Depends(require_tenant_member),
    service: ConversationService = Depends(),
):
    """Create a new conversation."""
    return await service.create(tenant_id, data, user.id)


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    tenant_id: str,
    conversation_id: str,
    data: ConversationUpdate,
    _user=Depends(get_current_user),
    _member=Depends(require_tenant_member),
    service: ConversationService = Depends(),
):
    """Update an existing conversation."""
    # Verify the conversation exists
    existing = await service.get_by_id(tenant_id, conversation_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return await service.update(tenant_id, conversation_id, data)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    tenant_id: str,
    conversation_id: str,
    _user=Depends(get_current_user),
    _member=Depends(require_tenant_member),
    service: ConversationService = Depends(),
):
    """Delete a conversation."""
    # Verify the conversation exists
    existing = await service.get_by_id(tenant_id, conversation_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    await service.delete(tenant_id, conversation_id)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_message(
    tenant_id: str,
    conversation_id: str,
    data: MessageCreate,
    _user=Depends(get_current_user),
    _member=Depends(require_tenant_member),
    service: ConversationService = Depends(),
):
    """Add a message to a conversation."""
    # Verify conversation exists
    existing = await service.get_by_id(tenant_id, conversation_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return await service.add_message(conversation_id, data)


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    tenant_id: str,
    conversation_id: str,
    _user=Depends(get_current_user),
    _member=Depends(require_tenant_member),
    service: ConversationService = Depends(),
):
    """Get all messages for a conversation."""
    # Verify conversation exists
    existing = await service.get_by_id(tenant_id, conversation_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return await service.get_messages(conversation_id)
