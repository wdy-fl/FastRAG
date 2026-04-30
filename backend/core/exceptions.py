class FastRAGError(Exception):
    """Base exception for FastRAG."""


class IngestionError(FastRAGError):
    """Raised when the ingestion pipeline encounters an unrecoverable error."""


class LLMError(FastRAGError):
    """Raised on LLM API failures."""


class RetrievalError(FastRAGError):
    """Raised when retrieval fails."""
