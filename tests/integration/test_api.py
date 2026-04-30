import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastrag.core.models.chat import LLMEvent


def _make_app_with_mock_pipeline():
    from fastrag.main import app
    from fastrag.api import deps
    from fastrag.core.rag.pipeline import RAGPipeline

    mock_pipeline = MagicMock(spec=RAGPipeline)

    async def fake_chat(request):
        yield LLMEvent(type="content", content="Hello")
        yield LLMEvent(type="done", content="")

    mock_pipeline.chat = fake_chat

    app.dependency_overrides[deps.get_rag_pipeline] = lambda: mock_pipeline
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
    from fastrag.main import app
    from fastrag.api import deps
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
    from fastrag.main import app
    from fastrag.api import deps
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
    from fastrag.main import app
    from fastrag.api import deps
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
