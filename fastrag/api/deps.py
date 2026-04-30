from __future__ import annotations
from functools import lru_cache
from fastrag.config.settings import Settings
from fastrag.db.session import create_session_factory
from fastrag.infra.llm.client import OpenAICompatClient
from fastrag.infra.vector.pgvector import PgVectorStore
from fastrag.infra.cache.redis import RedisCache
from fastrag.db.repos.conversation import ConversationRepo
from fastrag.db.repos.knowledge import KnowledgeRepo
from fastrag.db.repos.trace import TraceRepo
from fastrag.core.rag.memory import SlidingWindowMemory
from fastrag.core.rag.rewrite import LLMQueryRewriter
from fastrag.core.rag.intent import LLMIntentClassifier
from fastrag.core.rag.retrieve import MultiChannelRetriever, VectorSearchChannel, DeduplicationProcessor
from fastrag.core.rag.prompt import PromptBuilder
from fastrag.core.rag.pipeline import RAGPipeline
from fastrag.core.rag.tracer import RagTracer
from fastrag.core.ingestion.engine import IngestionEngine
from fastrag.core.ingestion.nodes.fetcher import FetcherNode
from fastrag.core.ingestion.nodes.parser import ParserNode
from fastrag.core.ingestion.nodes.chunker import ChunkerNode
from fastrag.core.ingestion.nodes.indexer import IndexerNode
from fastrag.core.ingestion.strategies.fetcher.local import LocalFileFetcher
from fastrag.core.ingestion.strategies.fetcher.http import HttpUrlFetcher
from fastrag.core.ingestion.strategies.parser.markdown import MarkdownParser
from fastrag.core.ingestion.strategies.parser.unstructured import UnstructuredParser
from fastrag.core.ingestion.strategies.chunker.fixed import FixedSizeChunker
from fastrag.core.ingestion.strategies.chunker.paragraph import ParagraphChunker
from fastrag.core.ingestion.strategies.chunker.sentence import SentenceChunker
from fastrag.core.ingestion.strategies.chunker.structure_aware import StructureAwareChunker
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


def get_rag_pipeline(
    conv_repo: ConversationRepo = Depends(get_conversation_repo),
    trace_repo: TraceRepo = Depends(get_trace_repo),
) -> RAGPipeline:
    s = get_settings()
    llm = get_llm_provider()
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
            intent_nodes=[],
            confidence_threshold=s.rag_intent_confidence_threshold,
        ),
        retriever=MultiChannelRetriever(
            channels=[VectorSearchChannel(vector_store=get_vector_store(), llm=get_embedding_provider())],
            post_processors=[DeduplicationProcessor()],
        ),
        prompt_builder=PromptBuilder(),
        tracer=RagTracer(repo=trace_repo),
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
            "enhancer": None,
            "chunker": ChunkerNode(
                strategies={
                    "fixed": FixedSizeChunker(),
                    "paragraph": ParagraphChunker(),
                    "sentence": SentenceChunker(),
                    "structure_aware": StructureAwareChunker(),
                }
            ),
            "enricher": None,
            "indexer": IndexerNode(llm=get_embedding_provider(), vector_store=get_vector_store()),
        }
    )


from fastrag.db.repos.intent import IntentRepo  # noqa: E402
from fastrag.db.repos.mapping import MappingRepo  # noqa: E402


def get_intent_repo(
    session: AsyncSession = Depends(get_db_session),
) -> IntentRepo:
    return IntentRepo(session)


def get_mapping_repo(
    session: AsyncSession = Depends(get_db_session),
) -> MappingRepo:
    return MappingRepo(session)
