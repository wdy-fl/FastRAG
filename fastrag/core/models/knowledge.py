from __future__ import annotations
from typing import Any
from pydantic import BaseModel


class KnowledgeBase(BaseModel):
    id: str
    name: str
    description: str = ""


class Document(BaseModel):
    id: str
    knowledge_base_id: str
    filename: str
    source_type: str
    source_uri: str
    status: str = "pending"
    chunk_count: int = 0


class DocumentChunk(BaseModel):
    content: str
    chunk_index: int
    metadata: dict[str, Any] = {}


class ChunkWithEmbedding(BaseModel):
    chunk: DocumentChunk
    embedding: list[float]
