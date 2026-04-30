from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from backend.api.deps import get_knowledge_repo
from backend.db.repos.knowledge import KnowledgeRepo

router = APIRouter()


class CreateKnowledgeBaseRequest(BaseModel):
    name: str
    description: str = ""
    ingestion_config: dict = {}


class KnowledgeBaseResponse(BaseModel):
    id: str
    name: str
    description: str


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
    return KnowledgeBaseResponse(id=kb.id, name=kb.name, description=kb.description)


@router.get("", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(
    repo: KnowledgeRepo = Depends(get_knowledge_repo),
) -> list[KnowledgeBaseResponse]:
    kbs = await repo.list_knowledge_bases()
    return [KnowledgeBaseResponse(id=kb.id, name=kb.name, description=kb.description) for kb in kbs]


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: str,
    repo: KnowledgeRepo = Depends(get_knowledge_repo),
) -> KnowledgeBaseResponse:
    kb = await repo.get_knowledge_base(kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return KnowledgeBaseResponse(id=kb.id, name=kb.name, description=kb.description)


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    kb_id: str,
    repo: KnowledgeRepo = Depends(get_knowledge_repo),
) -> None:
    await repo.delete_knowledge_base(kb_id)
