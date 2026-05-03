from __future__ import annotations
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict
from backend.core.models.knowledge import DocumentChunk, ChunkWithEmbedding


class FetcherSettings(BaseModel):
    source_type: Literal["local", "http"]
    source_uri: str


class ParserSettings(BaseModel):
    parser_type: Literal["unstructured", "markdown"] = "markdown"


class ChunkerSettings(BaseModel):
    chunker_type: Literal["fixed", "paragraph", "sentence", "structure_aware"] = "structure_aware"
    chunk_size: int = 500
    overlap: int = 50
    # StructureAware 专用（新增，有默认值，向后兼容）
    min_chars: int = 600
    target_chars: int = 1400
    max_chars: int = 1800


class IndexerSettings(BaseModel):
    batch_size: int = 100


class EnhanceTaskType(str, Enum):
    CONTEXT_ENHANCE = "context_enhance"
    KEYWORDS = "keywords"
    QUESTIONS = "questions"
    METADATA = "metadata"


class EnhanceTask(BaseModel):
    type: EnhanceTaskType
    system_prompt: str | None = None
    user_prompt_template: str | None = None


class EnhancerSettings(BaseModel):
    model_id: str | None = None
    tasks: list[EnhanceTask] = []


class ChunkEnrichType(str, Enum):
    KEYWORDS = "keywords"
    SUMMARY = "summary"
    METADATA = "metadata"


class ChunkEnrichTask(BaseModel):
    type: ChunkEnrichType
    system_prompt: str | None = None
    user_prompt_template: str | None = None


class EnricherSettings(BaseModel):
    model_id: str | None = None
    attach_document_metadata: bool = True
    tasks: list[ChunkEnrichTask] = []


class IngestionConfig(BaseModel):
    fetcher: FetcherSettings
    parser: ParserSettings
    chunker: ChunkerSettings
    indexer: IndexerSettings = IndexerSettings()
    enhancer: EnhancerSettings | None = None
    enricher: EnricherSettings | None = None


class NodeResult(BaseModel):
    node_name: str
    status: Literal["success", "failed", "skipped"]
    duration_ms: int = 0
    error: str | None = None
    output_summary: str | None = None


class IngestionContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    pipeline_id: str
    task_id: str
    config: IngestionConfig

    raw_content: bytes | None = None
    parsed_text: str | None = None
    enhanced_text: str | None = None
    keywords: list[str] = []
    questions: list[str] = []
    chunks: list[DocumentChunk] = []
    embedded_chunks: list[ChunkWithEmbedding] = []

    metadata: dict[str, Any] = {}
    node_results: list[NodeResult] = []
