from __future__ import annotations
import json
from typing import AsyncIterator

import httpx

from backend.core.models.chat import LLMEvent
from backend.infra.llm.stream import parse_sse_line


class OpenAICompatClient:
    """Unified LLM client — compatible with DashScope / SiliconFlow / Ollama OpenAI-style APIs."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        model: str = "",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=5.0)
        )

    def _auth_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def stream(
        self, messages: list[dict], **kwargs
    ) -> AsyncIterator[LLMEvent]:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": kwargs.pop("model", self.model),
            "messages": messages,
            "stream": True,
            **kwargs,
        }
        async with self._http.stream(
            "POST", url, json=payload, headers=self._auth_headers()
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                event = parse_sse_line(line)
                if event is not None:
                    yield event

    async def embed(
        self, texts: list[str], model: str | None = None
    ) -> list[list[float]]:
        url = f"{self.base_url}/embeddings"
        payload = {"model": model or self.model, "input": texts}
        resp = await self._http.post(
            url, json=payload, headers=self._auth_headers()
        )
        resp.raise_for_status()
        return [item["embedding"] for item in resp.json()["data"]]

    async def close(self) -> None:
        await self._http.aclose()
