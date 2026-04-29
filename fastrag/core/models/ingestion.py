from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict
from fastrag.core.models.knowledge import DocumentChunk, ChunkWithEmbedding


class FetcherSettings(BaseModel):
    source_type: Literal["local", "s3", "http"]
    source_uri: str


class ParserSettings(BaseModel):
    parser_type: Literal["unstructured", "markdown"] = "unstructured"


class ChunkerSettings(BaseModel):
    chunker_type: Literal["fixed", "paragraph", "sentence", "structure_aware"] = "structure_aware"
    chunk_size: int = 500
    overlap: int = 50


class IndexerSettings(BaseModel):
    batch_size: int = 100


class EnhancerSettings(BaseModel):
    """Optional node — presence enables enhancement step."""


class EnricherSettings(BaseModel):
    """Optional node — presence enables enrichment step."""


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
    chunks: list[DocumentChunk] = []
    embedded_chunks: list[ChunkWithEmbedding] = []

    metadata: dict[str, Any] = {}
    node_results: list[NodeResult] = []
