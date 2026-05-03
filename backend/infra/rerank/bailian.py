from __future__ import annotations
import httpx
from backend.core.models.chat import RetrievedChunk


class BailianRerankClient:
    _URL = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"

    def __init__(self, api_key: str, model: str = "gte-rerank") -> None:
        self._api_key = api_key
        self._model = model

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_n: int = 5,
    ) -> list[RetrievedChunk]:
        if not chunks:
            return chunks
        documents = [self._build_doc_text(c) for c in chunks]
        payload = {
            "model": self._model,
            "input": {"query": query, "documents": documents},
            "parameters": {"top_n": top_n, "return_documents": False},
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            resp.raise_for_status()
        data = resp.json()
        ranked = sorted(
            data["output"]["results"],
            key=lambda r: r["relevance_score"],
            reverse=True,
        )
        return [
            RetrievedChunk(
                content=chunks[r["index"]].content,
                score=r["relevance_score"],
                metadata=chunks[r["index"]].metadata,
                document_id=chunks[r["index"]].document_id,
            )
            for r in ranked[:top_n]
        ]

    @staticmethod
    def _build_doc_text(chunk: RetrievedChunk) -> str:
        summary = chunk.metadata.get("summary", "")
        if summary:
            return f"{summary}\n\n{chunk.content}"
        return chunk.content
