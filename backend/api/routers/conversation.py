from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from backend.api.deps import get_conversation_repo
from backend.db.repos.conversation import ConversationRepo

router = APIRouter()


class CreateConversationRequest(BaseModel):
    title: str


class ConversationResponse(BaseModel):
    id: str
    title: str


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ConversationResponse)
async def create_conversation(
    body: CreateConversationRequest,
    repo: ConversationRepo = Depends(get_conversation_repo),
) -> ConversationResponse:
    conv = await repo.create_conversation(title=body.title)
    return ConversationResponse(id=conv.id, title=conv.title)


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    repo: ConversationRepo = Depends(get_conversation_repo),
) -> list[ConversationResponse]:
    convs = await repo.list_conversations()
    return [ConversationResponse(id=c.id, title=c.title) for c in convs]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    repo: ConversationRepo = Depends(get_conversation_repo),
) -> ConversationResponse:
    conv = await repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationResponse(id=conv.id, title=conv.title)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    repo: ConversationRepo = Depends(get_conversation_repo),
) -> None:
    await repo.delete_conversation(conversation_id)
