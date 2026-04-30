from __future__ import annotations
from typing import Any, Literal, Union
from pydantic import BaseModel
from fastrag.core.models.intent import IntentResult


class ChatRequest(BaseModel):
    query: str
    conversation_id: str
    deep_thinking: bool = False          # 新增


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ConversationHistory(BaseModel):
    messages: list[ChatMessage] = []
    summary: str | None = None


class MetaEvent(BaseModel):              # 新增
    type: Literal["meta"] = "meta"
    task_id: str


class LLMEvent(BaseModel):
    type: Literal["content", "thinking", "done"]
    content: str = ""
    title: str | None = None             # 新增，仅 done 时携带


class GuidanceEvent(BaseModel):
    type: Literal["guidance"] = "guidance"
    intent: IntentResult


class RetrievedChunk(BaseModel):
    content: str
    score: float
    metadata: dict[str, Any] = {}
    document_id: str | None = None


ChatEvent = Union[MetaEvent, LLMEvent, GuidanceEvent]
