import json
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from backend.infra.llm.client import OpenAICompatClient
from backend.core.models.chat import LLMEvent


@pytest.mark.asyncio
async def test_embed_returns_vectors():
    client = OpenAICompatClient(
        base_url="http://localhost:11434/v1",
        api_key=None,
        model="qwen3-embedding",
    )
    mock_response = {
        "data": [
            {"embedding": [0.1, 0.2, 0.3]},
            {"embedding": [0.4, 0.5, 0.6]},
        ]
    }
    with patch.object(client._http, "post") as mock_post:
        mock_resp = AsyncMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value=mock_response)
        mock_post.return_value = mock_resp

        result = await client.embed(["text1", "text2"])

    assert len(result) == 2
    assert result[0] == [0.1, 0.2, 0.3]
    await client.close()


@pytest.mark.asyncio
async def test_stream_yields_content_events():
    client = OpenAICompatClient(
        base_url="http://localhost:11434/v1",
        api_key="test-key",
        model="qwen3:8b",
    )
    sse_lines = [
        'data: {"choices":[{"delta":{"content":"Hello"}}]}',
        'data: {"choices":[{"delta":{"content":" world"}}]}',
        "data: [DONE]",
    ]

    async def fake_aiter_lines():
        for line in sse_lines:
            yield line

    mock_stream_ctx = MagicMock()
    mock_response = AsyncMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.aiter_lines = fake_aiter_lines
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch.object(client._http, "stream", return_value=mock_stream_ctx):
        events = []
        async for event in client.stream([{"role": "user", "content": "hi"}]):
            events.append(event)

    assert len(events) == 2
    assert events[0] == LLMEvent(type="content", content="Hello")
    assert events[1] == LLMEvent(type="content", content=" world")
    await client.close()


@pytest.mark.asyncio
async def test_stream_yields_thinking_events():
    client = OpenAICompatClient(
        base_url="http://localhost:11434/v1",
        api_key=None,
        model="qwen3:8b",
    )
    sse_lines = [
        'data: {"choices":[{"delta":{"reasoning_content":"thinking..."}}]}',
        "data: [DONE]",
    ]

    async def fake_aiter_lines():
        for line in sse_lines:
            yield line

    mock_stream_ctx = MagicMock()
    mock_response = AsyncMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.aiter_lines = fake_aiter_lines
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch.object(client._http, "stream", return_value=mock_stream_ctx):
        events = []
        async for event in client.stream([{"role": "user", "content": "think"}]):
            events.append(event)

    assert events[0] == LLMEvent(type="thinking", content="thinking...")
    await client.close()


@pytest.mark.asyncio
async def test_chat_returns_content():
    client = OpenAICompatClient(base_url="http://test", api_key="k", model="m")
    response_body = {"choices": [{"message": {"content": "hello"}}]}
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=response_body))
    client._http = httpx.AsyncClient(transport=transport)
    result = await client.chat([{"role": "user", "content": "hi"}])
    assert result == "hello"
    await client.close()
