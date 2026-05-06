import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.db.repos.intent import IntentRepo


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_cache():
    cache = AsyncMock()
    cache.delete = AsyncMock()
    return cache


@pytest.mark.asyncio
async def test_create_invalidates_cache(mock_session, mock_cache):
    repo = IntentRepo(session=mock_session, cache=mock_cache)
    mock_session.refresh = AsyncMock(return_value=MagicMock(
        id="n1", name="test",
        intent_type="kb", keywords=[], description="", knowledge_base_id=None,
    ))
    await repo.create_intent_node(
        name="test", intent_type="kb", keywords=[], description="",
    )
    mock_cache.delete.assert_awaited_once_with("intent:nodes")


@pytest.mark.asyncio
async def test_delete_invalidates_cache(mock_session, mock_cache):
    repo = IntentRepo(session=mock_session, cache=mock_cache)
    await repo.delete_intent_node("node-1")
    mock_cache.delete.assert_awaited_once_with("intent:nodes")


@pytest.mark.asyncio
async def test_update_invalidates_cache(mock_session, mock_cache):
    repo = IntentRepo(session=mock_session, cache=mock_cache)
    mock_orm = MagicMock()
    mock_orm.id = "n1"
    mock_session.get = AsyncMock(return_value=mock_orm)
    mock_session.refresh = AsyncMock(return_value=MagicMock(
        id="n1", name="updated",
        intent_type="kb", keywords=[], description="", knowledge_base_id="kb-1",
    ))
    await repo.update_intent_node("n1", name="updated")
    mock_cache.delete.assert_awaited_once_with("intent:nodes")


@pytest.mark.asyncio
async def test_no_cache_no_invalidation(mock_session):
    repo = IntentRepo(session=mock_session, cache=None)
    mock_session.refresh = AsyncMock(return_value=MagicMock(
        id="n1", name="test",
        intent_type="kb", keywords=[], description="", knowledge_base_id=None,
    ))
    await repo.create_intent_node(
        name="test", intent_type="kb", keywords=[], description="",
    )
    # 不应抛异常


@pytest.mark.asyncio
async def test_update_raises_on_missing_node(mock_session, mock_cache):
    repo = IntentRepo(session=mock_session, cache=mock_cache)
    mock_session.get = AsyncMock(return_value=None)
    with pytest.raises(ValueError, match="not found"):
        await repo.update_intent_node("missing", name="x")
