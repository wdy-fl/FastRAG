import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from backend.infra.rerank.bailian import BailianRerankClient
from backend.core.models.chat import RetrievedChunk


def _make_chunks():
    return [
        RetrievedChunk(content="chunk A", score=0.9, metadata={"summary": "摘要A"}, document_id="d1"),
        RetrievedChunk(content="chunk B", score=0.8, metadata={}, document_id="d2"),
        RetrievedChunk(content="chunk C", score=0.7, metadata={"summary": "摘要C"}, document_id="d3"),
    ]


@pytest.mark.asyncio
async def test_rerank_returns_reordered_chunks():
    client = BailianRerankClient(api_key="test-key")
    chunks = _make_chunks()

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "output": {
            "results": [
                {"index": 2, "relevance_score": 0.95},
                {"index": 0, "relevance_score": 0.88},
                {"index": 1, "relevance_score": 0.72},
            ]
        }
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        result = await client.rerank("退款政策", chunks, top_n=3)

    assert len(result) == 3
    assert result[0].content == "chunk C"   # index 2, highest score
    assert result[1].content == "chunk A"   # index 0
    assert result[2].content == "chunk B"   # index 1
    assert result[0].score == 0.95


@pytest.mark.asyncio
async def test_rerank_builds_doc_text_with_summary():
    client = BailianRerankClient(api_key="test-key")
    chunk = RetrievedChunk(content="原文内容", score=0.9, metadata={"summary": "摘要"})
    doc_text = client._build_doc_text(chunk)
    assert doc_text == "摘要\n\n原文内容"


def test_rerank_builds_doc_text_without_summary():
    client = BailianRerankClient(api_key="test-key")
    chunk = RetrievedChunk(content="原文内容", score=0.9, metadata={})
    doc_text = client._build_doc_text(chunk)
    assert doc_text == "原文内容"


@pytest.mark.asyncio
async def test_rerank_returns_empty_for_empty_input():
    client = BailianRerankClient(api_key="test-key")
    result = await client.rerank("query", [], top_n=5)
    assert result == []
