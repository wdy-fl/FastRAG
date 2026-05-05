import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.core.rag.term_mapper import QueryTermMapper


def _make_orm_mapping(source_term: str, target_term: str, knowledge_base_id: str | None = None):
    m = MagicMock()
    m.id = "test-id"
    m.source_term = source_term
    m.target_term = target_term
    m.knowledge_base_id = knowledge_base_id
    return m


@pytest.mark.asyncio
async def test_mapper_replaces_terms_with_word_boundary():
    mock_repo = AsyncMock()
    mock_repo.list_mappings = AsyncMock(return_value=[
        _make_orm_mapping("DB", "数据库", None),
    ])
    mapper = QueryTermMapper(mapping_repo=mock_repo)
    result = await mapper.expand("DB 连接池怎么配")
    assert result == "数据库 连接池怎么配"


@pytest.mark.asyncio
async def test_mapper_does_not_replace_substring():
    mock_repo = AsyncMock()
    mock_repo.list_mappings = AsyncMock(return_value=[
        _make_orm_mapping("DB", "数据库", None),
    ])
    mapper = QueryTermMapper(mapping_repo=mock_repo)
    result = await mapper.expand("MONGODB 配置")
    assert result == "MONGODB 配置"


@pytest.mark.asyncio
async def test_mapper_filters_by_kb_id():
    """When kb_id is provided, both global (knowledge_base_id=None) and
    KB-specific mappings are eligible. Since the global mapping runs first
    and replaces the term, the KB-specific one no longer matches."""
    mock_repo = AsyncMock()
    mock_repo.list_mappings = AsyncMock(return_value=[
        _make_orm_mapping("DB", "数据库", None),
        _make_orm_mapping("DB", "RDS", "kb-infra"),
    ])
    mapper = QueryTermMapper(mapping_repo=mock_repo)

    # Without kb_id, only global mapping applies (kb-specific is filtered out)
    result = await mapper.expand("DB 连接池", kb_id=None)
    assert result == "数据库 连接池"

    # With matching kb_id, both are eligible; global runs first so DB→数据库
    result = await mapper.expand("DB 连接池", kb_id="kb-infra")
    assert result == "数据库 连接池"

    # A KB-only mapping (no global counterpart) should apply when kb_id matches
    mock_repo2 = AsyncMock()
    mock_repo2.list_mappings = AsyncMock(return_value=[
        _make_orm_mapping("API", "接口", "kb-infra"),
    ])
    mapper2 = QueryTermMapper(mapping_repo=mock_repo2)
    result2 = await mapper2.expand("API 调用", kb_id="kb-infra")
    assert result2 == "接口 调用"

    # Same KB-specific mapping should NOT apply when kb_id doesn't match
    result3 = await mapper2.expand("API 调用", kb_id="kb-other")
    assert result3 == "API 调用"


@pytest.mark.asyncio
async def test_mapper_returns_original_when_no_mappings():
    mock_repo = AsyncMock()
    mock_repo.list_mappings = AsyncMock(return_value=[])
    mapper = QueryTermMapper(mapping_repo=mock_repo)
    result = await mapper.expand("Hello world")
    assert result == "Hello world"


@pytest.mark.asyncio
async def test_mapper_returns_original_when_no_repo():
    mapper = QueryTermMapper(mapping_repo=None)
    result = await mapper.expand("Hello world")
    assert result == "Hello world"
