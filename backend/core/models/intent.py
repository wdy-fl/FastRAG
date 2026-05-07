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


class IntentMatch(BaseModel):
    """单个意图匹配结果。"""
    node: IntentNode
    confidence: Literal["high", "medium", "low"] = "medium"


class IntentResult(BaseModel):
    matches: list[IntentMatch] = []
    needs_guidance: bool = False
    guidance_message: str | None = None
    candidates: list[IntentNode] = []

    @property
    def matched_nodes(self) -> list[IntentNode]:
        """所有 confidence 为 high 的匹配节点。"""
        return [m.node for m in self.matches if m.confidence == "high"]

    @property
    def primary_node(self) -> IntentNode | None:
        """最高置信度的匹配节点（high > medium > low），无匹配时返回 None。"""
        for level in ("high", "medium", "low"):
            for m in self.matches:
                if m.confidence == level:
                    return m.node
        return None
