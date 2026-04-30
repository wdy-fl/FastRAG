from __future__ import annotations
import asyncio
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.api.deps import get_knowledge_repo, get_ingestion_engine
from backend.db.repos.knowledge import KnowledgeRepo
from backend.core.ingestion.engine import IngestionEngine
from backend.core.models.ingestion import (
    IngestionConfig, IngestionContext, FetcherSettings,
    ParserSettings, ChunkerSettings, IndexerSettings,
)
from fastapi import status
from uuid import uuid4

router = APIRouter()


class TriggerIngestionRequest(BaseModel):
    filename: str
    source_type: str
    source_uri: str
    parser_type: str = "unstructured"
    chunker_type: str = "structure_aware"
    chunk_size: int = 500
    overlap: int = 50


class TriggerIngestionResponse(BaseModel):
    document_id: str
    status: str


@router.post(
    "/knowledge-bases/{kb_id}/documents",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TriggerIngestionResponse,
)
async def trigger_ingestion(
    kb_id: str,
    body: TriggerIngestionRequest,
    repo: KnowledgeRepo = Depends(get_knowledge_repo),
    engine: IngestionEngine = Depends(get_ingestion_engine),
) -> TriggerIngestionResponse:
    doc = await repo.create_document(
        knowledge_base_id=kb_id,
        filename=body.filename,
        source_type=body.source_type,
        source_uri=body.source_uri,
    )

    config = IngestionConfig(
        fetcher=FetcherSettings(
            source_type=body.source_type, source_uri=body.source_uri
        ),
        parser=ParserSettings(parser_type=body.parser_type),
        chunker=ChunkerSettings(
            chunker_type=body.chunker_type,
            chunk_size=body.chunk_size,
            overlap=body.overlap,
        ),
        indexer=IndexerSettings(),
    )
    context = IngestionContext(
        pipeline_id=str(uuid4()),
        task_id=str(uuid4()),
        config=config,
        metadata={
            "knowledge_base_id": kb_id,
            "document_id": doc.id,
            "filename": body.filename,
        },
    )

    async def _run():
        try:
            await engine.execute(config, context)
            await repo.update_document_status(
                doc.id,
                status="completed",
                chunk_count=len(context.embedded_chunks),
            )
        except Exception as exc:
            await repo.update_document_status(
                doc.id, status="failed", error_message=str(exc)
            )

    asyncio.create_task(_run())
    return TriggerIngestionResponse(document_id=doc.id, status="processing")


@router.get("/knowledge-bases/{kb_id}/documents")
async def list_documents(
    kb_id: str,
    repo: KnowledgeRepo = Depends(get_knowledge_repo),
):
    docs = await repo.list_documents(kb_id)
    return [{"id": d.id, "filename": d.filename, "status": d.status} for d in docs]
