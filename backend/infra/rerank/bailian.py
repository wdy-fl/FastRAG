from __future__ import annotations
import logging
import httpx
from backend.core.models.chat import RetrievedChunk

logger = logging.getLogger("backend.rag.rerank")


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
            logger.debug("重排序 | 无chunks，跳过")
            return chunks
        logger.info("重排序开始 | query=%r | input_chunks=%d | top_n=%d", query, len(chunks), top_n)
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
        result = [
            RetrievedChunk(
                content=chunks[r["index"]].content,
                score=r["relevance_score"],
                metadata=chunks[r["index"]].metadata,
                document_id=chunks[r["index"]].document_id,
            )
            for r in ranked[:top_n]
        ]
        logger.info(
            "重排序完成 | %d → %d chunks | top_score=%.4f",
            len(chunks), len(result),
            ranked[0]["relevance_score"] if ranked else 0.0,
        )
        return result

    @staticmethod
    def _build_doc_text(chunk: RetrievedChunk) -> str:
        summary = chunk.metadata.get("summary", "")
        if summary:
            return f"{summary}\n\n{chunk.content}"
        return chunk.content
