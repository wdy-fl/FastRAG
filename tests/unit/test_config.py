from fastrag.config.settings import Settings, LLMSettings, EmbeddingSettings


def test_settings_defaults():
    s = Settings()
    assert isinstance(s.llm.chat_model, str) and s.llm.chat_model
    assert s.rag_window_size == 4
    assert s.rag_intent_confidence_threshold == 0.6


def test_llm_settings_defaults():
    s = LLMSettings()
    assert s.base_url == "http://localhost:11434/v1"


def test_embedding_settings_defaults():
    s = EmbeddingSettings()
    assert s.dimensions == 1024
    assert s.base_url == "http://localhost:11434/v1"


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("FASTRAG_RAG_WINDOW_SIZE", "8")
    s = Settings()
    assert s.rag_window_size == 8


def test_db_base_has_metadata():
    from fastrag.db.models.base import Base
    assert Base.metadata is not None


def test_session_factory_creation():
    from fastrag.db.session import create_session_factory
    factory = create_session_factory("postgresql+asyncpg://user:pw@localhost/db")
    assert factory is not None
