import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from backend.core.models.chat import LLMEvent


def _make_app_with_mock_pipeline():
    from backend.main import app
    from backend.api import deps
    from backend.core.rag.pipeline import RAGPipeline
    from backend.infra.llm.client import OpenAICompatClient

    mock_pipeline = MagicMock(spec=RAGPipeline)

    async def fake_chat(request):
        yield LLMEvent(type="content", content="Hello")
        yield LLMEvent(type="done", content="")

    mock_pipeline.chat = fake_chat

    mock_llm = MagicMock(spec=OpenAICompatClient)

    async def fake_stream(messages, **kwargs):
        yield LLMEvent(type="content", content="Test title")

    mock_llm.stream = fake_stream

    app.dependency_overrides[deps.get_rag_pipeline] = lambda: mock_pipeline
    app.dependency_overrides[deps.get_llm_provider] = lambda: mock_llm
    return app


def test_chat_stream_returns_sse_events():
    app = _make_app_with_mock_pipeline()
    client = TestClient(app)
    response = client.post(
        "/chat/stream",
        json={"query": "What is AI?", "conversation_id": "conv-test"},
        headers={"Accept": "text/event-stream"},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    content = response.text
    assert "data:" in content


def test_chat_stream_invalid_body_returns_422():
    app = _make_app_with_mock_pipeline()
    client = TestClient(app)
    response = client.post("/chat/stream", json={"wrong_field": "x"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Conversation tests
# ---------------------------------------------------------------------------

def _mock_conv_repo():
    mock_repo = AsyncMock()
    from backend.main import app
    from backend.api import deps
    app.dependency_overrides[deps.get_conversation_repo] = lambda: mock_repo
    return mock_repo, app


def test_create_conversation_returns_201():
    mock_repo, app = _mock_conv_repo()
    mock_repo.create_conversation = AsyncMock(
        return_value=MagicMock(id="c1", title="My Chat")
    )
    client = TestClient(app)
    resp = client.post("/conversations", json={"title": "My Chat"})
    assert resp.status_code == 201
    assert resp.json()["id"] == "c1"


def test_list_conversations_returns_200():
    mock_repo, app = _mock_conv_repo()
    mock_repo.list_conversations = AsyncMock(return_value=[])
    client = TestClient(app)
    resp = client.get("/conversations")
    assert resp.status_code == 200
    assert resp.json() == []


def test_delete_conversation_returns_204():
    mock_repo, app = _mock_conv_repo()
    mock_repo.delete_conversation = AsyncMock(return_value=None)
    client = TestClient(app)
    resp = client.delete("/conversations/c1")
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Knowledge Base & Ingestion tests
# ---------------------------------------------------------------------------

def test_create_knowledge_base_returns_201():
    from backend.main import app
    from backend.api import deps
    mock_repo = AsyncMock()
    kb_mock = MagicMock()
    kb_mock.id = "kb1"
    kb_mock.name = "Finance KB"
    kb_mock.description = ""
    mock_repo.create_knowledge_base = AsyncMock(return_value=kb_mock)
    app.dependency_overrides[deps.get_knowledge_repo] = lambda: mock_repo
    client = TestClient(app)
    resp = client.post(
        "/knowledge-bases",
        json={"name": "Finance KB", "description": "", "ingestion_config": {}},
    )
    assert resp.status_code == 201
    assert resp.json()["id"] == "kb1"


def test_trigger_ingestion_returns_202():
    from backend.main import app
    from backend.api import deps
    mock_repo = AsyncMock()
    mock_repo.create_document = AsyncMock(
        return_value=MagicMock(id="doc1", status="pending")
    )
    mock_engine = MagicMock()
    mock_engine.execute = AsyncMock(return_value=MagicMock(node_results=[]))
    app.dependency_overrides[deps.get_knowledge_repo] = lambda: mock_repo
    app.dependency_overrides[deps.get_ingestion_engine] = lambda: mock_engine
    client = TestClient(app)
    resp = client.post(
        "/knowledge-bases/kb1/documents",
        json={
            "filename": "report.pdf",
            "source_type": "local",
            "source_uri": "/tmp/report.pdf",
        },
    )
    assert resp.status_code == 202


# ---------------------------------------------------------------------------
# Intent / Trace / Mapping tests
# ---------------------------------------------------------------------------

def test_get_intent_tree_returns_200():
    from backend.main import app
    from backend.api.deps import get_intent_repo
    mock_repo = AsyncMock()
    mock_repo.list_intent_nodes = AsyncMock(return_value=[])
    app.dependency_overrides[get_intent_repo] = lambda: mock_repo
    client = TestClient(app)
    resp = client.get("/intent-trees")
    assert resp.status_code == 200


def test_list_traces_returns_200():
    from backend.main import app
    from backend.api import deps
    mock_repo = AsyncMock()
    mock_repo.list_runs = AsyncMock(return_value=[])
    app.dependency_overrides[deps.get_trace_repo] = lambda: mock_repo
    client = TestClient(app)
    resp = client.get("/traces")
    assert resp.status_code == 200


def test_list_mappings_returns_200():
    from backend.main import app
    from backend.api.deps import get_mapping_repo
    mock_repo = AsyncMock()
    mock_repo.list_mappings = AsyncMock(return_value=[])
    app.dependency_overrides[get_mapping_repo] = lambda: mock_repo
    client = TestClient(app)
    resp = client.get("/query-term-mappings")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Meta event / stop endpoint tests
# ---------------------------------------------------------------------------

def test_chat_stream_first_event_is_meta():
    """流的第一个 data 事件 type 必须是 meta 且含 task_id"""
    app = _make_app_with_mock_pipeline()
    client = TestClient(app)
    resp = client.post(
        "/chat/stream",
        json={"query": "hi", "conversation_id": "c1"},
        headers={"Accept": "text/event-stream"},
    )
    assert resp.status_code == 200
    lines = [l for l in resp.text.split("\n") if l.startswith("data:")]
    first = json.loads(lines[0][5:])
    assert first["type"] == "meta"
    assert "task_id" in first
    assert isinstance(first["task_id"], str)


def test_chat_stop_returns_200():
    """stop 端点对已注册 task_id 返回 200"""
    import backend.api.routers.chat as chat_mod
    import asyncio
    app = _make_app_with_mock_pipeline()
    client = TestClient(app)
    fake_task_id = "test-task-id-200"
    mock_task = MagicMock(spec=asyncio.Task)
    mock_task.done.return_value = False
    chat_mod._task_registry[fake_task_id] = mock_task
    stop_resp = client.post("/chat/stop", json={"task_id": fake_task_id})
    assert stop_resp.status_code == 200
    mock_task.cancel.assert_called_once()  # 验证 cancel 被调用


def test_chat_stop_unknown_task_id_returns_404():
    app = _make_app_with_mock_pipeline()
    client = TestClient(app)
    resp = client.post("/chat/stop", json={"task_id": "nonexistent-id"})
    assert resp.status_code == 404
