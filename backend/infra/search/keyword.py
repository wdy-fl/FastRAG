from __future__ import annotations
import logging
from backend.core.models.chat import RetrievedChunk
from backend.core.models.intent import IntentResult
from backend.infra.search.bm25_index import Bm25IndexManager

logger = logging.getLogger("backend.search.keyword")


class Bm25KeywordChannel:
    def __init__(self, bm25_manager: Bm25IndexManager) -> None:
        self._bm25_manager = bm25_manager

    async def search(
        self,
        query: str,
        intent: IntentResult,
        top_k: int = 10,
        query_vector: list[float] | None = None,
    ) -> list[RetrievedChunk]:
        await self._bm25_manager.ensure_ready()

        kb_ids = [
            m.node.knowledge_base_id
            for m in intent.matches
            if m.node.intent_type == "kb" and m.node.knowledge_base_id
        ] or [None]

        all_results: list[RetrievedChunk] = []
        for kb_id in kb_ids:
            results = self._bm25_manager.search(query=query, kb_id=kb_id, top_k=top_k)
            all_results.extend(results)
            logger.debug(
                "Bm25Keyword | query=%r | kb=%s | results=%d",
                query, kb_id, len(results),
            )
        return all_results
