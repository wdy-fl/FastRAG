from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseModel):
    base_url: str = "http://localhost:11434/v1"
    api_key: str | None = None
    chat_model: str = "qwen3:8b"


class EmbeddingSettings(BaseModel):
    base_url: str = "http://localhost:11434/v1"
    api_key: str | None = None
    model: str = "qwen3-embedding"
    dimensions: int = 1024


class IngestionSettings(BaseModel):
    task_timeout_seconds: int = 600  # 默认 10 分钟


class RerankSettings(BaseModel):
    api_key: str | None = None
    model: str = "gte-rerank"
    top_n: int = 5


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fastrag"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    llm: LLMSettings = LLMSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    ingestion: IngestionSettings = IngestionSettings()
    rerank: RerankSettings = RerankSettings()
    rag_window_size: int = 4
    rag_summary_threshold: int = 5
    rag_retrieval_top_k: int = 10
    rag_intent_confidence_threshold: float = 0.6

    model_config = SettingsConfigDict(
        env_prefix="FASTRAG_",
        env_file=".env",
        env_nested_delimiter="__",
    )
