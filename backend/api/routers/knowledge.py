from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from backend.api.deps import get_knowledge_repo
from backend.db.repos.knowledge import KnowledgeRepo

router = APIRouter()


class CreateKnowledgeBaseRequest(BaseModel):
    name: str
    description: str = ""
    ingestion_config: dict = {}


class UpdateKnowledgeBaseRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    ingestion_config: dict | None = None


class KnowledgeBaseResponse(BaseModel):
    id: str
    name: str
    description: str
    ingestion_config: dict
    created_at: datetime


def _to_response(kb) -> KnowledgeBaseResponse:
    return KnowledgeBaseResponse(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        ingestion_config=kb.ingestion_config or {},
        created_at=kb.created_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    body: CreateKnowledgeBaseRequest,
    repo: KnowledgeRepo = Depends(get_knowledge_repo),
) -> KnowledgeBaseResponse:
    kb = await repo.create_knowledge_base(
        name=body.name,
        description=body.description,
        ingestion_config=body.ingestion_config,
    )
    return _to_response(kb)


@router.get("", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(
    repo: KnowledgeRepo = Depends(get_knowledge_repo),
) -> list[KnowledgeBaseResponse]:
    kbs = await repo.list_knowledge_bases()
    return [_to_response(kb) for kb in kbs]


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: str,
    repo: KnowledgeRepo = Depends(get_knowledge_repo),
) -> KnowledgeBaseResponse:
    kb = await repo.get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return _to_response(kb)


@router.patch("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: str,
    body: UpdateKnowledgeBaseRequest,
    repo: KnowledgeRepo = Depends(get_knowledge_repo),
) -> KnowledgeBaseResponse:
    kb = await repo.get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if body.name is not None:
        kb.name = body.name
    if body.description is not None:
        kb.description = body.description
    if body.ingestion_config is not None:
        kb.ingestion_config = body.ingestion_config
    await repo._session.commit()
    await repo._session.refresh(kb)
    return _to_response(kb)


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    kb_id: str,
    repo: KnowledgeRepo = Depends(get_knowledge_repo),
) -> None:
    await repo.delete_knowledge_base(kb_id)
