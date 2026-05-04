from __future__ import annotations
import asyncio
import os
import tempfile
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from backend.api.deps import (
    get_ingestion_engine,
    get_ingestion_task_repo,
    get_knowledge_repo,
    get_session_factory,
    get_settings,
)
from backend.db.repos.knowledge import KnowledgeRepo
from backend.db.repos.ingestion_task import IngestionTaskRepo
from backend.core.ingestion.engine import IngestionEngine
from backend.core.models.ingestion import (
    IngestionConfig, IngestionContext,
    FetcherSettings, ParserSettings, ChunkerSettings, IndexerSettings,
    EnhancerSettings, EnricherSettings,
    NodeResult,
)
from uuid import uuid4

router = APIRouter()

# 节点完成后对应的文档下一步状态
_NODE_TO_DOC_STATUS: dict[str, str] = {
    "fetcher": "parsing",
    "parser": "chunking",
    "enhancer": "chunking",
    "chunker": "embedding",
    "enricher": "embedding",
}

# 系统默认摄入配置（KB 未配置时使用）
_DEFAULT_INGESTION_CONFIG: dict = {
    "parser": {"parser_type": "markdown"},
    "chunker": {"chunker_type": "structure_aware", "chunk_size": 500, "overlap": 50},
    "indexer": {"batch_size": 100},
}


class TriggerIngestionResponse(BaseModel):
    document_id: str
    task_id: str
    status: str


class IngestionTaskResponse(BaseModel):
    task_id: str
    document_id: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    chunk_count: int | None
    error: str | None
    node_timings: dict[str, int]


def _build_config(kb_ingestion_config: dict, tmp_path: str) -> IngestionConfig:
    """从 KB 配置 + 运行时信息构建 IngestionConfig。"""
    merged = {**_DEFAULT_INGESTION_CONFIG, **kb_ingestion_config}

    parser_cfg = merged.get("parser", {})
    chunker_cfg = merged.get("chunker", {})
    indexer_cfg = merged.get("indexer", {})
    enhancer_cfg = merged.get("enhancer")
    enricher_cfg = merged.get("enricher")

    enhancer = None
    if enhancer_cfg is not None:
        enhancer = EnhancerSettings.model_validate(enhancer_cfg)

    enricher = None
    if enricher_cfg is not None:
        enricher = EnricherSettings.model_validate(enricher_cfg)

    return IngestionConfig(
        fetcher=FetcherSettings(source_type="local", source_uri=tmp_path),
        parser=ParserSettings.model_validate(parser_cfg),
        chunker=ChunkerSettings.model_validate(chunker_cfg),
        indexer=IndexerSettings.model_validate(indexer_cfg),
        enhancer=enhancer,
        enricher=enricher,
    )


@router.post(
    "/knowledge-bases/{kb_id}/documents",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TriggerIngestionResponse,
)
async def trigger_ingestion(
    kb_id: str,
    file: UploadFile = File(...),
    kb_repo: KnowledgeRepo = Depends(get_knowledge_repo),
    task_repo: IngestionTaskRepo = Depends(get_ingestion_task_repo),
    engine: IngestionEngine = Depends(get_ingestion_engine),
) -> TriggerIngestionResponse:
    kb = await kb_repo.get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    suffix = os.path.splitext(file.filename or "")[1]
    _TMP_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "temp")
    os.makedirs(_TMP_DIR, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(suffix=suffix, dir=_TMP_DIR)
    try:
        content = await file.read()
        os.write(fd, content)
    finally:
        os.close(fd)

    filename = file.filename or os.path.basename(tmp_path)

    doc = await kb_repo.create_document(
        knowledge_base_id=kb_id,
        filename=filename,
        source_type="local",
        source_uri=tmp_path,
    )

    task = await task_repo.create(kb_id=kb_id, document_id=doc.id)

    config = _build_config(kb.ingestion_config or {}, tmp_path)
    context = IngestionContext(
        pipeline_id=str(uuid4()),
        task_id=task.id,
        config=config,
        metadata={
            "knowledge_base_id": kb_id,
            "document_id": doc.id,
            "filename": filename,
        },
    )

    settings = get_settings()
    session_factory = get_session_factory()
    timeout = settings.ingestion.task_timeout_seconds

    async def _run() -> None:
        try:
            async with session_factory() as session:
                _doc_repo = KnowledgeRepo(session)
                _task_repo = IngestionTaskRepo(session)

                await _task_repo.update_started(task.id)
                await _doc_repo.update_document_status(doc.id, status="fetching")

                async def on_node_complete(node_name: str, result: NodeResult) -> None:
                    if result.status == "success":
                        next_status = _NODE_TO_DOC_STATUS.get(node_name)
                        if next_status:
                            await _doc_repo.update_document_status(doc.id, status=next_status)
                    await _task_repo.append_node_result(
                        task.id,
                        node_name=node_name,
                        status=result.status,
                        duration_ms=result.duration_ms,
                    )

                try:
                    await asyncio.wait_for(
                        engine.execute(config, context, on_node_complete=on_node_complete),
                        timeout=timeout,
                    )
                    chunk_count = len(context.embedded_chunks)
                    await _doc_repo.update_document_status(
                        doc.id, status="completed", chunk_count=chunk_count
                    )
                    await _task_repo.update_completed(task.id, chunk_count=chunk_count)
                except asyncio.TimeoutError:
                    await _doc_repo.update_document_status(doc.id, status="failed",
                                                            error_message="Ingestion timeout")
                    await _task_repo.update_failed(task.id, error="Ingestion timeout")
                except Exception as exc:
                    await _doc_repo.update_document_status(doc.id, status="failed",
                                                            error_message=str(exc))
                    await _task_repo.update_failed(task.id, error=str(exc))
        except Exception as exc:
            import logging
            logging.getLogger(__name__).exception("Ingestion task %s failed before session: %s", task.id, exc)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    asyncio.create_task(_run())
    return TriggerIngestionResponse(document_id=doc.id, task_id=task.id, status=doc.status)


@router.delete(
    "/knowledge-bases/{kb_id}/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    kb_id: str,
    doc_id: str,
    kb_repo: KnowledgeRepo = Depends(get_knowledge_repo),
    task_repo: IngestionTaskRepo = Depends(get_ingestion_task_repo),
) -> None:
    doc = await kb_repo.get_document(doc_id)
    if not doc or doc.knowledge_base_id != kb_id:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status not in ("completed", "failed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is still being processed, please wait until ingestion finishes",
        )
    await task_repo.delete_by_document(doc_id)
    _ = await kb_repo.delete_document(doc_id)


@router.get("/knowledge-bases/{kb_id}/documents")
async def list_documents(
    kb_id: str,
    repo: KnowledgeRepo = Depends(get_knowledge_repo),
):
    docs = await repo.list_documents(kb_id)
    return [{"id": d.id, "filename": d.filename, "status": d.status} for d in docs]


@router.get(
    "/knowledge-bases/{kb_id}/documents/{doc_id}/ingestion-task",
    response_model=IngestionTaskResponse,
)
async def get_ingestion_task(
    kb_id: str,
    doc_id: str,
    task_repo: IngestionTaskRepo = Depends(get_ingestion_task_repo),
) -> IngestionTaskResponse:
    task = await task_repo.get_by_document(doc_id)
    if not task:
        raise HTTPException(status_code=404, detail="Ingestion task not found")

    node_timings = {
        r["node_name"]: r["duration_ms"]
        for r in (task.node_results or [])
        if r.get("status") == "success"
    }

    return IngestionTaskResponse(
        task_id=task.id,
        document_id=task.document_id,
        status=task.status,
        started_at=task.started_at,
        finished_at=task.finished_at,
        chunk_count=task.chunk_count,
        error=task.error_message,
        node_timings=node_timings,
    )
