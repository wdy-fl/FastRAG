from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any
import jieba
from rank_bm25 import BM25Plus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from backend.core.models.chat import RetrievedChunk
from backend.db.models.knowledge import KnowledgeChunkORM

logger = logging.getLogger("backend.search.bm25")


@dataclass
class _CorpusItem:
    content: str
    document_id: str
    knowledge_base_id: str
    metadata: dict[str, Any]


@dataclass
class _Bm25Corpus:
    bm25: BM25Plus
    items: list[_CorpusItem]


def _tokenize(text: str) -> list[str]:
    """使用 jieba 搜索引擎模式分词，适合检索场景。"""
    return [w for w in jieba.cut_for_search(text) if w.strip()]


class Bm25IndexManager:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._kb_indexes: dict[str, _Bm25Corpus] = {}
        self._global_index: _Bm25Corpus | None = None
        self._dirty = True

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def has_index(self, kb_id: str | None) -> bool:
        if kb_id is None:
            return self._global_index is not None
        return kb_id in self._kb_indexes

    def mark_dirty(self) -> None:
        self._dirty = True
        logger.info("BM25索引标记为脏，下次查询时重建")

    async def ensure_ready(self) -> None:
        if not self._dirty:
            return
        await self.build()

    async def build(self) -> None:
        logger.info("BM25索引构建开始...")
        chunks = await self._load_chunks()
        kb_groups: dict[str, list[_CorpusItem]] = {}
        all_items: list[_CorpusItem] = []

        for c in chunks:
            item = _CorpusItem(
                content=c.content,
                document_id=c.document_id,
                knowledge_base_id=c.knowledge_base_id,
                metadata=dict(c.metadata_) if c.metadata_ else {},
            )
            kb_groups.setdefault(c.knowledge_base_id, []).append(item)
            all_items.append(item)

        new_kb_indexes: dict[str, _Bm25Corpus] = {}
        for kb_id, items in kb_groups.items():
            new_kb_indexes[kb_id] = self._build_corpus(items)

        new_global = self._build_corpus(all_items) if all_items else None

        self._kb_indexes = new_kb_indexes
        self._global_index = new_global
        self._dirty = False

        logger.info(
            "BM25索引构建完成 | kb_count=%d | total_chunks=%d",
            len(new_kb_indexes), len(all_items),
        )

    def search(
        self,
        query: str,
        kb_id: str | None = None,
        top_k: int = 10,
    ) -> list[RetrievedChunk]:
        corpus = self._get_corpus(kb_id)
        if corpus is None:
            return []

        tokenized_query = _tokenize(query)
        if not tokenized_query:
            return []

        scores = corpus.bm25.get_scores(tokenized_query)
        # 过滤零分，按分数降序
        scored = [
            (i, float(scores[i]))
            for i in range(len(scores))
            if scores[i] > 0
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:top_k]

        return [
            RetrievedChunk(
                content=corpus.items[idx].content,
                score=score,
                metadata={
                    **corpus.items[idx].metadata,
                    "_knowledge_base_id": corpus.items[idx].knowledge_base_id,
                },
                document_id=corpus.items[idx].document_id,
            )
            for idx, score in top
        ]

    def _get_corpus(self, kb_id: str | None) -> _Bm25Corpus | None:
        if kb_id is not None:
            return self._kb_indexes.get(kb_id)
        return self._global_index

    @staticmethod
    def _build_corpus(items: list[_CorpusItem]) -> _Bm25Corpus:
        tokenized = [_tokenize(item.content) for item in items]
        bm25 = BM25Plus(tokenized)
        return _Bm25Corpus(bm25=bm25, items=items)

    async def _load_chunks(self) -> list[KnowledgeChunkORM]:
        async with self._session_factory() as session:
            stmt = select(KnowledgeChunkORM).order_by(KnowledgeChunkORM.created_at)
            result = await session.execute(stmt)
            chunks = list(result.scalars().all())
            logger.debug("BM25加载chunks | count=%d", len(chunks))
            return chunks
