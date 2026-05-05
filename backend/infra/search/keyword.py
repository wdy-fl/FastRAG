from __future__ import annotations
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from backend.core.models.chat import RetrievedChunk
from backend.core.models.intent import IntentResult
from backend.db.models.knowledge import KnowledgeChunkORM

logger = logging.getLogger("backend.rag.keyword")


class KeywordSearchChannel:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def search(
        self, query: str, intent: IntentResult, top_k: int = 10,
        query_vector: list[float] | None = None,
    ) -> list[RetrievedChunk]:
        kb_id = None
        if intent.matched_node:
            if intent.matched_node.intent_type == "kb" and intent.matched_node.knowledge_base_id:
                kb_id = intent.matched_node.knowledge_base_id

        async with self._session_factory() as session:
            tsquery = func.plainto_tsquery('simple', query)
            rank_col = func.ts_rank(KnowledgeChunkORM.keywords_tsv, tsquery).label("rank")
            stmt = select(KnowledgeChunkORM, rank_col).where(
                KnowledgeChunkORM.keywords_tsv.op("@@")(tsquery)
            )
            if kb_id is not None:
                stmt = stmt.where(KnowledgeChunkORM.knowledge_base_id == kb_id)
            stmt = stmt.order_by(rank_col.desc()).limit(top_k)
            result = await session.execute(stmt)
            rows = result.all()
            logger.debug("KeywordSearch | query=%r | kb=%s | results=%d", query, kb_id, len(rows))
            return [
                RetrievedChunk(
                    content=row.KnowledgeChunkORM.content,
                    score=float(row.rank),
                    metadata=row.KnowledgeChunkORM.metadata_ or {},
                    document_id=row.KnowledgeChunkORM.document_id,
                )
                for row in rows
            ]
