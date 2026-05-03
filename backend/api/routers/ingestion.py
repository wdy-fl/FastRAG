from __future__ import annotations
import asyncio
import os
import tempfile
from fastapi import APIRouter, Depends, File, Form, UploadFile
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
    file: UploadFile = File(...),
    parser_type: str = Form("markdown"),
    chunker_type: str = Form("structure_aware"),
    chunk_size: int = Form(500),
    overlap: int = Form(50),
    repo: KnowledgeRepo = Depends(get_knowledge_repo),
    engine: IngestionEngine = Depends(get_ingestion_engine),
) -> TriggerIngestionResponse:
    # Write uploaded file to a temp path for the local fetcher
    suffix = os.path.splitext(file.filename or "")[1]
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        content = await file.read()
        os.write(fd, content)
    finally:
        os.close(fd)

    source_type = "local"
    filename = file.filename or os.path.basename(tmp_path)

    doc = await repo.create_document(
        knowledge_base_id=kb_id,
        filename=filename,
        source_type=source_type,
        source_uri=tmp_path,
    )

    config = IngestionConfig(
        fetcher=FetcherSettings(
            source_type=source_type, source_uri=tmp_path
        ),
        parser=ParserSettings(parser_type=parser_type),
        chunker=ChunkerSettings(
            chunker_type=chunker_type,
            chunk_size=chunk_size,
            overlap=overlap,
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
            "filename": filename,
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
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    asyncio.create_task(_run())
    return TriggerIngestionResponse(document_id=doc.id, status=doc.status)


@router.get("/knowledge-bases/{kb_id}/documents")
async def list_documents(
    kb_id: str,
    repo: KnowledgeRepo = Depends(get_knowledge_repo),
):
    docs = await repo.list_documents(kb_id)
    return [{"id": d.id, "filename": d.filename, "status": d.status} for d in docs]
