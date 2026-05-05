from unittest.mock import MagicMock, patch
from backend.api.deps import get_rag_pipeline


def test_deps_importable():
    from backend.api import deps  # noqa: F401
    assert True


def test_get_settings_returns_settings():
    from backend.api.deps import get_settings
    from backend.config.settings import Settings
    s = get_settings()
    assert isinstance(s, Settings)


def test_get_rag_pipeline_wires_intent_repo_and_cache():
    """Verify get_rag_pipeline wires IntentRepo + RedisCache into LLMIntentClassifier."""
    with patch("backend.api.deps.get_settings") as mock_settings, \
         patch("backend.api.deps.get_llm_provider") as mock_llm, \
         patch("backend.api.deps.get_embedding_provider") as mock_embedding, \
         patch("backend.api.deps.get_redis_cache") as mock_redis, \
         patch("backend.api.deps.get_session_factory") as mock_sf, \
         patch("backend.api.deps.get_vector_store") as mock_vs, \
         patch("backend.api.deps.get_reranker") as mock_reranker:

        mock_settings.return_value = MagicMock(
            rag_window_size=5,
            rag_summary_threshold=10,
            rag_intent_confidence_threshold=0.6,
        )
        mock_llm.return_value = MagicMock()
        mock_embedding.return_value = MagicMock()
        mock_redis.return_value = MagicMock()
        mock_sf.return_value = MagicMock()
        mock_vs.return_value = MagicMock()
        mock_reranker.return_value = None

        conv_repo = MagicMock()
        trace_repo = MagicMock()
        intent_repo = MagicMock()
        mapping_repo = MagicMock()

        pipeline = get_rag_pipeline(
            conv_repo=conv_repo,
            trace_repo=trace_repo,
            intent_repo=intent_repo,
            mapping_repo=mapping_repo,
        )

        # LLMIntentClassifier should receive intent_repo and cache
        classifier = pipeline._intent_classifier
        assert classifier._repo is intent_repo
        assert classifier._cache is mock_redis.return_value


def test_get_rag_pipeline_wires_embedding_llm_to_retriever():
    """Verify MultiChannelRetriever receives embedding_llm."""
    with patch("backend.api.deps.get_settings") as mock_settings, \
         patch("backend.api.deps.get_llm_provider") as mock_llm, \
         patch("backend.api.deps.get_embedding_provider") as mock_embedding, \
         patch("backend.api.deps.get_redis_cache") as mock_redis, \
         patch("backend.api.deps.get_session_factory") as mock_sf, \
         patch("backend.api.deps.get_vector_store") as mock_vs, \
         patch("backend.api.deps.get_reranker") as mock_reranker:

        embedding_llm = MagicMock()
        mock_settings.return_value = MagicMock(
            rag_window_size=5,
            rag_summary_threshold=10,
            rag_intent_confidence_threshold=0.6,
        )
        mock_llm.return_value = MagicMock()
        mock_embedding.return_value = embedding_llm
        mock_redis.return_value = MagicMock()
        mock_sf.return_value = MagicMock()
        mock_vs.return_value = MagicMock()
        mock_reranker.return_value = None

        pipeline = get_rag_pipeline(
            conv_repo=MagicMock(),
            trace_repo=MagicMock(),
            intent_repo=MagicMock(),
            mapping_repo=MagicMock(),
        )

        # MultiChannelRetriever should use embedding_llm
        retriever = pipeline._retriever
        assert retriever._llm is embedding_llm


def test_get_rag_pipeline_accepts_mapping_repo():
    """Verify get_rag_pipeline accepts mapping_repo dependency (for future QueryTermMapper)."""
    with patch("backend.api.deps.get_settings") as mock_settings, \
         patch("backend.api.deps.get_llm_provider") as mock_llm, \
         patch("backend.api.deps.get_embedding_provider") as mock_embedding, \
         patch("backend.api.deps.get_redis_cache") as mock_redis, \
         patch("backend.api.deps.get_session_factory") as mock_sf, \
         patch("backend.api.deps.get_vector_store") as mock_vs, \
         patch("backend.api.deps.get_reranker") as mock_reranker:

        mock_settings.return_value = MagicMock(
            rag_window_size=5,
            rag_summary_threshold=10,
            rag_intent_confidence_threshold=0.6,
        )
        mock_llm.return_value = MagicMock()
        mock_embedding.return_value = MagicMock()
        mock_redis.return_value = MagicMock()
        mock_sf.return_value = MagicMock()
        mock_vs.return_value = MagicMock()
        mock_reranker.return_value = None

        mapping_repo = MagicMock()
        pipeline = get_rag_pipeline(
            conv_repo=MagicMock(),
            trace_repo=MagicMock(),
            intent_repo=MagicMock(),
            mapping_repo=mapping_repo,
        )
        # mapping_repo is accepted as a parameter (will be wired to QueryTermMapper in Task 11)
        assert pipeline is not None
