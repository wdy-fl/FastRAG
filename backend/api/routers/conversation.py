from __future__ import annotations
from typing import Literal

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


class UpdateConversationRequest(BaseModel):
    title: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    seq: int
    sources: list[dict] | None = None
    feedback: str | None = None


class FeedbackRequest(BaseModel):
    rating: Literal["up", "down"] | None


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


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: str,
    repo: ConversationRepo = Depends(get_conversation_repo),
) -> list[MessageResponse]:
    conv = await repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await repo.get_all_messages(conversation_id)
    return [
        MessageResponse(
            id=m.id, role=m.role, content=m.content, seq=m.seq,
            sources=m.sources, feedback=m.feedback,
        )
        for m in messages
    ]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    repo: ConversationRepo = Depends(get_conversation_repo),
) -> ConversationResponse:
    conv = await repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationResponse(id=conv.id, title=conv.title)


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    body: UpdateConversationRequest,
    repo: ConversationRepo = Depends(get_conversation_repo),
) -> ConversationResponse:
    conv = await repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await repo.update_title(conv, body.title)
    return ConversationResponse(id=conversation_id, title=body.title)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    repo: ConversationRepo = Depends(get_conversation_repo),
) -> None:
    await repo.delete_conversation(conversation_id)


@router.post("/messages/{message_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def submit_feedback(
    message_id: str,
    req: FeedbackRequest,
    repo: ConversationRepo = Depends(get_conversation_repo),
) -> None:
    message = await repo.get_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    await repo.update_message_feedback(message, req.rating)
