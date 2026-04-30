from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.api.deps import get_trace_repo
from backend.db.repos.trace import TraceRepo

router = APIRouter()


class TraceRunResponse(BaseModel):
    id: str
    conversation_id: str
    query: str
    status: str
    total_duration_ms: int


@router.get("", response_model=list[TraceRunResponse])
async def list_traces(
    repo: TraceRepo = Depends(get_trace_repo),
) -> list[TraceRunResponse]:
    runs = await repo.list_runs()
    return [
        TraceRunResponse(
            id=r.id, conversation_id=r.conversation_id,
            query=r.query, status=r.status, total_duration_ms=r.total_duration_ms,
        )
        for r in runs
    ]


@router.get("/{run_id}", response_model=TraceRunResponse)
async def get_trace(
    run_id: str,
    repo: TraceRepo = Depends(get_trace_repo),
) -> TraceRunResponse:
    run = await repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Trace not found")
    return TraceRunResponse(
        id=run.id, conversation_id=run.conversation_id,
        query=run.query, status=run.status, total_duration_ms=run.total_duration_ms,
    )
