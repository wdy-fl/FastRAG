from __future__ import annotations
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from backend.core.models.chat import RetrievedChunk
from backend.core.models.intent import IntentResult
from backend.db.models.knowledge import KnowledgeChunkORM


class KeywordSearchChannel:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def search(
        self, query: str, intent: IntentResult, top_k: int = 10
    ) -> list[RetrievedChunk]:
        knowledge_base_id = intent.matched_node.id if intent.matched_node else None
        async with self._session_factory() as session:
            tsquery = func.plainto_tsquery('simple', query)
            rank_col = func.ts_rank(KnowledgeChunkORM.keywords_tsv, tsquery).label("rank")
            # 先构建所有 where 条件，最后再 limit，确保在正确范围内取 top_k
            stmt = select(KnowledgeChunkORM, rank_col).where(
                KnowledgeChunkORM.keywords_tsv.op("@@")(tsquery)
            )
            if knowledge_base_id is not None:
                stmt = stmt.where(KnowledgeChunkORM.knowledge_base_id == knowledge_base_id)
            stmt = stmt.order_by(rank_col.desc()).limit(top_k)
            result = await session.execute(stmt)
            return [
                RetrievedChunk(
                    content=row.KnowledgeChunkORM.content,
                    score=float(row.rank),
                    metadata=row.KnowledgeChunkORM.metadata_ or {},
                    document_id=row.KnowledgeChunkORM.document_id,
                )
                for row in result.all()
            ]
