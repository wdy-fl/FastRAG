from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.infra.search.bm25_index import Bm25IndexManager
from backend.core.models.chat import RetrievedChunk


def _make_mock_session_factory(chunks_data=None):
    """构造 mock session_factory，模拟从 PG 加载 chunks。"""
    chunks_data = chunks_data or [
        MagicMock(
            id="c1",
            content="退货退款政策说明，30日内可申请退货退款",
            document_id="doc-1",
            knowledge_base_id="kb-1",
            metadata_={"filename": "refund.pdf"},
        ),
        MagicMock(
            id="c2",
            content="售后服务流程，如何申请维修和退换货",
            document_id="doc-2",
            knowledge_base_id="kb-1",
            metadata_={"filename": "service.pdf"},
        ),
        MagicMock(
            id="c3",
            content="产品使用指南，快速上手教程",
            document_id="doc-3",
            knowledge_base_id="kb-2",
            metadata_={"filename": "guide.pdf"},
        ),
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = chunks_data
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_session_factory


@pytest.mark.asyncio
async def test_build_creates_kb_indexes():
    """构建后应包含按 kb_id 分组的索引 + 全局索引。"""
    manager = Bm25IndexManager(session_factory=_make_mock_session_factory())
    await manager.build()

    assert manager.has_index("kb-1")
    assert manager.has_index("kb-2")
    assert manager.has_index(None)  # global


@pytest.mark.asyncio
async def test_search_returns_scored_chunks():
    """搜索应返回按 BM25 打分的 RetrievedChunk 列表。"""
    manager = Bm25IndexManager(session_factory=_make_mock_session_factory())
    await manager.build()

    results = manager.search(query="退货退款", kb_id="kb-1", top_k=5)
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(r, RetrievedChunk) for r in results)
    # "退货退款" 应在退款政策文档上得分更高
    assert results[0].content == "退货退款政策说明，30日内可申请退货退款"


@pytest.mark.asyncio
async def test_search_filters_by_kb_id():
    """指定 kb_id 时只搜该知识库的索引。"""
    manager = Bm25IndexManager(session_factory=_make_mock_session_factory())
    await manager.build()

    results_kb2 = manager.search(query="退货", kb_id="kb-2", top_k=5)
    # kb-2 只有"产品使用指南"，不含"退货"，应返回空或低分
    for r in results_kb2:
        assert r.metadata.get("_knowledge_base_id") == "kb-2"


@pytest.mark.asyncio
async def test_search_uses_jieba_tokenization():
    """jieba 分词应将中文句子拆分为有意义的词元。"""
    manager = Bm25IndexManager(session_factory=_make_mock_session_factory())
    await manager.build()

    # "退款流程" 被拆分为 ["退款", "流程"]，能匹配到含"退款"的 chunk
    results = manager.search(query="退款流程", kb_id="kb-1", top_k=5)
    assert len(results) > 0
    assert any("退款" in r.content for r in results)


@pytest.mark.asyncio
async def test_mark_dirty_triggers_rebuild():
    """mark_dirty 后，ensure_ready 应触发重建。"""
    manager = Bm25IndexManager(session_factory=_make_mock_session_factory())
    await manager.build()
    assert not manager.is_dirty

    manager.mark_dirty()
    assert manager.is_dirty

    # ensure_ready 会重建
    await manager.ensure_ready()
    assert not manager.is_dirty


@pytest.mark.asyncio
async def test_ensure_ready_skips_if_not_dirty():
    """非脏状态时 ensure_ready 不应重建。"""
    manager = Bm25IndexManager(session_factory=_make_mock_session_factory())
    await manager.build()
    assert not manager.is_dirty

    # Capture reference to existing index before ensure_ready
    global_before = manager._global_index

    await manager.ensure_ready()

    # Same index object means no rebuild happened
    assert manager._global_index is global_before
    assert not manager.is_dirty


@pytest.mark.asyncio
async def test_empty_corpus_returns_empty():
    """空知识库搜索应返回空列表。"""
    empty_factory = _make_mock_session_factory(chunks_data=[])
    manager = Bm25IndexManager(session_factory=empty_factory)
    await manager.build()

    results = manager.search(query="测试", kb_id="kb-1", top_k=5)
    assert results == []


@pytest.mark.asyncio
async def test_ensure_ready_builds_on_first_call():
    """首次调用 ensure_ready 时应自动构建索引。"""
    manager = Bm25IndexManager(session_factory=_make_mock_session_factory())
    assert manager.is_dirty  # 初始为脏

    await manager.ensure_ready()
    assert not manager.is_dirty
    assert manager.has_index(None)  # global index built


@pytest.mark.asyncio
async def test_search_global_index_returns_from_all_kbs():
    """kb_id=None 时使用全局索引，应包含所有知识库的文档。"""
    manager = Bm25IndexManager(session_factory=_make_mock_session_factory())
    await manager.build()

    # Verify global index contains items from both kb-1 and kb-2
    global_corpus = manager._global_index
    assert global_corpus is not None
    kb_ids = {item.knowledge_base_id for item in global_corpus.items}
    assert "kb-1" in kb_ids
    assert "kb-2" in kb_ids
