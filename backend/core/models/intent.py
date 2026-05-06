from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class IntentNode(BaseModel):
    id: str
    name: str
    intent_type: Literal["kb", "mcp", "system"] = "kb"
    knowledge_base_id: str | None = None
    keywords: list[str] = []
    description: str = ""


class IntentResult(BaseModel):
    matched_node: IntentNode | None = None
    confidence: float = 0.0
    needs_guidance: bool = False
    guidance_message: str | None = None
    candidates: list[IntentNode] = []
