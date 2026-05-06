from __future__ import annotations
from functools import lru_cache
from backend.config.settings import Settings
from backend.db.session import create_session_factory
from backend.infra.llm.client import OpenAICompatClient
from backend.infra.vector.pgvector import PgVectorStore
from backend.infra.cache.redis import RedisCache
from backend.db.repos.conversation import ConversationRepo
from backend.db.repos.intent import IntentRepo
from backend.db.repos.knowledge import KnowledgeRepo
from backend.db.repos.mapping import MappingRepo
from backend.db.repos.trace import TraceRepo
from backend.db.repos.ingestion_task import IngestionTaskRepo
from backend.core.rag.memory import SlidingWindowMemory
from backend.core.rag.rewrite import LLMQueryRewriter
from backend.core.rag.intent import LLMIntentClassifier
from backend.core.rag.retrieve import MultiChannelRetriever, VectorSearchChannel, QuestionSearchChannel
from backend.infra.search.keyword import Bm25KeywordChannel
from backend.infra.search.bm25_index import Bm25IndexManager
from backend.core.rag.protocols import Reranker
from backend.infra.rerank.bailian import BailianRerankClient
from backend.core.rag.prompt import PromptBuilder
from backend.core.rag.pipeline import RAGPipeline
from backend.core.rag.term_mapper import QueryTermMapper
from backend.core.rag.tracer import RagTracer
from backend.core.ingestion.engine import IngestionEngine
from backend.core.ingestion.nodes.fetcher import FetcherNode
from backend.core.ingestion.nodes.parser import ParserNode
from backend.core.ingestion.nodes.chunker import ChunkerNode
from backend.core.ingestion.nodes.indexer import IndexerNode
from backend.core.ingestion.nodes.enhancer import EnhancerNode
from backend.core.ingestion.nodes.enricher import EnricherNode
from backend.core.ingestion.strategies.fetcher.local import LocalFileFetcher
from backend.core.ingestion.strategies.fetcher.http import HttpUrlFetcher
from backend.core.ingestion.strategies.parser.markdown import MarkdownParser
from backend.core.ingestion.strategies.parser.unstructured import UnstructuredParser
from backend.core.ingestion.strategies.chunker.fixed import FixedSizeChunker
from backend.core.ingestion.strategies.chunker.paragraph import ParagraphChunker
from backend.core.ingestion.strategies.chunker.sentence import SentenceChunker
from backend.core.ingestion.strategies.chunker.structure_aware import StructureAwareChunker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from fastapi import Depends


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return create_session_factory(get_settings().database_url)


@lru_cache
def get_llm_provider() -> OpenAICompatClient:
    s = get_settings()
    return OpenAICompatClient(
        base_url=s.llm.base_url,
        api_key=s.llm.api_key,
        model=s.llm.chat_model,
    )


@lru_cache
def get_embedding_provider() -> OpenAICompatClient:
    s = get_settings()
    return OpenAICompatClient(
        base_url=s.embedding.base_url,
        api_key=s.embedding.api_key,
        model=s.embedding.model,
    )


@lru_cache
def get_vector_store() -> PgVectorStore:
    return PgVectorStore(session_factory=get_session_factory())


@lru_cache
def get_redis_cache() -> RedisCache:
    return RedisCache(url=get_settings().redis_url)


@lru_cache
def get_bm25_index_manager() -> Bm25IndexManager:
    return Bm25IndexManager(session_factory=get_session_factory())


@lru_cache
def get_reranker() -> Reranker | None:
    s = get_settings()
    if s.rerank.api_key:
        return BailianRerankClient(api_key=s.rerank.api_key, model=s.rerank.model, top_n=s.rerank.top_n)
    return None


async def get_db_session() -> AsyncSession:
    factory = get_session_factory()
    async with factory() as session:
        yield session


def get_conversation_repo(
    session: AsyncSession = Depends(get_db_session),
) -> ConversationRepo:
    return ConversationRepo(session)


def get_knowledge_repo(
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeRepo:
    return KnowledgeRepo(session)


def get_trace_repo(
    session: AsyncSession = Depends(get_db_session),
) -> TraceRepo:
    return TraceRepo(session)


def get_intent_repo(
    session: AsyncSession = Depends(get_db_session),
) -> IntentRepo:
    return IntentRepo(session)


def get_mapping_repo(
    session: AsyncSession = Depends(get_db_session),
) -> MappingRepo:
    return MappingRepo(session, cache=get_redis_cache())


def get_rag_pipeline(
    conv_repo: ConversationRepo = Depends(get_conversation_repo),
    trace_repo: TraceRepo = Depends(get_trace_repo),
    intent_repo: IntentRepo = Depends(get_intent_repo),
    mapping_repo: MappingRepo = Depends(get_mapping_repo),
    knowledge_repo: KnowledgeRepo = Depends(get_knowledge_repo),
) -> RAGPipeline:
    s = get_settings()
    llm = get_llm_provider()
    embedding_llm = get_embedding_provider()
    redis = get_redis_cache()
    session_factory = get_session_factory()
    return RAGPipeline(
        llm=llm,
        memory=SlidingWindowMemory(
            repo=conv_repo,
            llm=llm,
            window_size=s.rag_window_size,
            summary_threshold=s.rag_summary_threshold,
        ),
        rewriter=LLMQueryRewriter(llm=llm),
        intent_classifier=LLMIntentClassifier(
            llm=llm,
            intent_repo=intent_repo,
            cache=redis,
            confidence_threshold=s.rag_intent_confidence_threshold,
        ),
        retriever=MultiChannelRetriever(
            channels=[
                VectorSearchChannel(vector_store=get_vector_store(), llm=embedding_llm),
                QuestionSearchChannel(vector_store=get_vector_store(), llm=embedding_llm),
                Bm25KeywordChannel(bm25_manager=get_bm25_index_manager()),
            ],
            llm=embedding_llm,
            chat_llm=llm,
        ),
        prompt_builder=PromptBuilder(),
        tracer=RagTracer(repo=trace_repo),
        doc_repo=knowledge_repo,
        reranker=get_reranker(),
        term_mapper=QueryTermMapper(
            mapping_repo=mapping_repo,
            cache=redis,
        ),
    )


def get_ingestion_engine() -> IngestionEngine:
    llm = get_llm_provider()
    return IngestionEngine(
        nodes={
            "fetcher": FetcherNode(
                strategies={
                    "local": LocalFileFetcher(),
                    "http": HttpUrlFetcher(),
                }
            ),
            "parser": ParserNode(
                strategies={
                    "unstructured": UnstructuredParser(),
                    "markdown": MarkdownParser(),
                }
            ),
            "enhancer": EnhancerNode(llm=llm),
            "chunker": ChunkerNode(
                strategies={
                    "fixed": FixedSizeChunker(),
                    "paragraph": ParagraphChunker(),
                    "sentence": SentenceChunker(),
                    "structure_aware": StructureAwareChunker(),
                }
            ),
            "enricher": EnricherNode(llm=llm),
            "indexer": IndexerNode(
                llm=get_embedding_provider(),
                vector_store=get_vector_store(),
                session_factory=get_session_factory(),
                bm25_manager=get_bm25_index_manager(),
            ),
        }
    )


def get_ingestion_task_repo(
    session: AsyncSession = Depends(get_db_session),
) -> IngestionTaskRepo:
    return IngestionTaskRepo(session)
