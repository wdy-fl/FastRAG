from __future__ import annotations
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from backend.api.deps import get_mapping_repo
from backend.db.repos.mapping import MappingRepo

router = APIRouter()


class MappingResponse(BaseModel):
    id: str
    source_term: str
    target_term: str
    knowledge_base_id: str | None


class CreateMappingRequest(BaseModel):
    source_term: str
    target_term: str
    knowledge_base_id: str | None = None


@router.get("", response_model=list[MappingResponse])
async def list_mappings(
    repo: MappingRepo = Depends(get_mapping_repo),
) -> list[MappingResponse]:
    mappings = await repo.list_mappings()
    return [
        MappingResponse(
            id=m.id, source_term=m.source_term,
            target_term=m.target_term, knowledge_base_id=m.knowledge_base_id,
        )
        for m in mappings
    ]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=MappingResponse)
async def create_mapping(
    body: CreateMappingRequest,
    repo: MappingRepo = Depends(get_mapping_repo),
) -> MappingResponse:
    m = await repo.create_mapping(**body.model_dump())
    return MappingResponse(
        id=m.id, source_term=m.source_term,
        target_term=m.target_term, knowledge_base_id=m.knowledge_base_id,
    )


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(
    mapping_id: str,
    repo: MappingRepo = Depends(get_mapping_repo),
) -> None:
    await repo.delete_mapping(mapping_id)
