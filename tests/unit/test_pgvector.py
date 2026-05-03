import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.infra.vector.pgvector import PgVectorStore
from backend.core.models.knowledge import DocumentChunk, ChunkWithEmbedding
from backend.core.models.chat import RetrievedChunk
from backend.db.models.knowledge import KnowledgeChunkORM


@pytest.mark.asyncio
async def test_search_returns_retrieved_chunks():
    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_orm = KnowledgeChunkORM(
        id="chunk-1",
        document_id="doc-1",
        knowledge_base_id="kb-1",
        content="Some text",
        chunk_index=0,
        embedding=[0.1] * 4096,
        metadata_={"filename": "test.pdf"},
    )
    mock_result = MagicMock()
    mock_row = MagicMock()
    mock_row.KnowledgeChunkORM = mock_orm
    mock_row.distance = 0.1
    mock_result.all.return_value = [mock_row]
    mock_session.execute = AsyncMock(return_value=mock_result)

    store = PgVectorStore(session_factory=mock_session_factory)
    results = await store.search(
        query_vector=[0.1] * 4096, top_k=5, knowledge_base_id="kb-1"
    )

    assert len(results) == 1
    assert isinstance(results[0], RetrievedChunk)
    assert results[0].content == "Some text"
    assert results[0].document_id == "doc-1"


@pytest.mark.asyncio
async def test_upsert_calls_session_add():
    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    store = PgVectorStore(session_factory=mock_session_factory)
    chunks = [
        ChunkWithEmbedding(
            chunk=DocumentChunk(content="text", chunk_index=0, metadata={"document_id": "doc-1"}),
            embedding=[0.1] * 4096,
        )
    ]
    metadata = {"knowledge_base_id": "kb-1", "document_id": "doc-1"}
    await store.upsert(chunks, metadata)

    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_sets_keywords_tsv_from_metadata():
    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    store = PgVectorStore(session_factory=mock_session_factory)
    chunks = [
        ChunkWithEmbedding(
            chunk=DocumentChunk(
                content="text",
                chunk_index=0,
                metadata={"document_id": "doc-1", "_keywords_str": "退款 政策"},
            ),
            embedding=[0.1] * 1024,
        )
    ]
    await store.upsert(chunks, metadata={"knowledge_base_id": "kb-1", "document_id": "doc-1"})

    added_orm = mock_session.add.call_args[0][0]
    # keywords_tsv 应为 SQL 表达式（不是 None）
    assert added_orm.keywords_tsv is not None
    # _keywords_str 应从 metadata_ 中被移除
    assert "_keywords_str" not in added_orm.metadata_


@pytest.mark.asyncio
async def test_search_questions_returns_chunks():
    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    from backend.db.models.knowledge import KnowledgeDocQuestionORM, KnowledgeChunkORM

    mock_q_result = MagicMock()
    mock_q_result.all.return_value = [("doc-1",), ("doc-1",)]  # 两个 question 命中同一文档

    mock_chunk_orm = KnowledgeChunkORM(
        id="chunk-1", document_id="doc-1", knowledge_base_id="kb-1",
        content="chunk text", chunk_index=0,
        embedding=[0.1] * 1024, metadata_={},
    )
    mock_chunk_result = MagicMock()
    mock_chunk_row = MagicMock()
    mock_chunk_row.KnowledgeChunkORM = mock_chunk_orm
    mock_chunk_row.distance = 0.2
    mock_chunk_result.all.return_value = [mock_chunk_row]

    mock_session.execute = AsyncMock(side_effect=[mock_q_result, mock_chunk_result])

    store = PgVectorStore(session_factory=mock_session_factory)
    results = await store.search_questions(
        query_vector=[0.1] * 1024, top_k=5, knowledge_base_id="kb-1"
    )

    assert len(results) == 1
    assert results[0].content == "chunk text"
    assert results[0].document_id == "doc-1"
