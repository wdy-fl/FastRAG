from __future__ import annotations
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from backend.api.deps import get_intent_repo
from backend.db.repos.intent import IntentRepo

router = APIRouter()


class IntentNodeResponse(BaseModel):
    id: str
    name: str
    intent_type: str
    knowledge_base_id: str | None
    keywords: list
    description: str


class CreateIntentNodeRequest(BaseModel):
    name: str
    intent_type: str = "kb"
    keywords: list[str] = []
    description: str = ""
    knowledge_base_id: str | None = None


class UpdateIntentNodeRequest(BaseModel):
    name: str | None = None
    intent_type: str | None = None
    keywords: list[str] | None = None
    description: str | None = None
    knowledge_base_id: str | None = None


def _orm_to_response(n) -> IntentNodeResponse:
    return IntentNodeResponse(
        id=n.id, name=n.name,
        intent_type=n.intent_type, knowledge_base_id=n.knowledge_base_id,
        keywords=n.keywords, description=n.description,
    )


@router.get("/nodes", response_model=list[IntentNodeResponse])
async def get_intent_tree(
    repo: IntentRepo = Depends(get_intent_repo),
) -> list[IntentNodeResponse]:
    nodes = await repo.list_intent_nodes()
    return [_orm_to_response(n) for n in nodes]


@router.post("/nodes", status_code=status.HTTP_201_CREATED, response_model=IntentNodeResponse)
async def add_intent_node(
    body: CreateIntentNodeRequest,
    repo: IntentRepo = Depends(get_intent_repo),
) -> IntentNodeResponse:
    node = await repo.create_intent_node(**body.model_dump())
    return _orm_to_response(node)


@router.put("/nodes/{node_id}", response_model=IntentNodeResponse)
async def update_intent_node(
    node_id: str,
    body: UpdateIntentNodeRequest,
    repo: IntentRepo = Depends(get_intent_repo),
) -> IntentNodeResponse:
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    node = await repo.update_intent_node(node_id, **fields)
    return _orm_to_response(node)


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_intent_node(
    node_id: str,
    repo: IntentRepo = Depends(get_intent_repo),
) -> None:
    await repo.delete_intent_node(node_id)
