from __future__ import annotations
from typing import Any, Literal, Union
from pydantic import BaseModel, model_validator
from backend.core.models.intent import IntentResult


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

    @model_validator(mode="after")
    def title_only_on_done(self) -> "LLMEvent":
        if self.title is not None and self.type != "done":
            raise ValueError("title is only allowed on type='done' events")
        return self


class GuidanceEvent(BaseModel):
    type: Literal["guidance"] = "guidance"
    intent: IntentResult


class RetrievedChunk(BaseModel):
    content: str
    score: float
    metadata: dict[str, Any] = {}
    document_id: str | None = None


class SourceItem(BaseModel):
    ref: int
    document_id: str | None = None
    document_name: str | None = None
    score: float
    content: str
    summary: str | None = None


class SourcesEvent(BaseModel):
    type: Literal["sources"] = "sources"
    sources: list[SourceItem]


ChatEvent = Union[MetaEvent, LLMEvent, GuidanceEvent, SourcesEvent]
