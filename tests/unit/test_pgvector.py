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
    mock_result.scalars.return_value.all.return_value = [mock_orm]
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
