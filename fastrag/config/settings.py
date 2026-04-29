from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseModel):
    base_url: str = "http://localhost:11434/v1"
    api_key: str | None = None
    chat_model: str = "qwen3:8b"
    embedding_model: str = "qwen3-embedding"
    embedding_dimensions: int = 4096


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fastrag"
    redis_url: str = "redis://localhost:6379/0"
    llm: LLMSettings = LLMSettings()
    rag_window_size: int = 4
    rag_summary_threshold: int = 5
    rag_retrieval_top_k: int = 10
    rag_intent_confidence_threshold: float = 0.6
    s3_endpoint: str | None = None
    s3_bucket: str = "fastrag"

    model_config = SettingsConfigDict(
        env_prefix="FASTRAG_",
        env_file=".env",
        env_nested_delimiter="__",
    )
