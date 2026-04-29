from __future__ import annotations
from typing import Any, Literal, Union
from pydantic import BaseModel
from fastrag.core.models.intent import IntentResult


class ChatRequest(BaseModel):
    query: str
    conversation_id: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ConversationHistory(BaseModel):
    messages: list[ChatMessage] = []
    summary: str | None = None


class LLMEvent(BaseModel):
    type: Literal["content", "thinking", "done"]
    content: str = ""


class GuidanceEvent(BaseModel):
    type: Literal["guidance"] = "guidance"
    intent: IntentResult


class RetrievedChunk(BaseModel):
    content: str
    score: float
    metadata: dict[str, Any] = {}
    document_id: str | None = None


ChatEvent = Union[LLMEvent, GuidanceEvent]
