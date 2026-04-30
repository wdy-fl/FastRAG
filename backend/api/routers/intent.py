from __future__ import annotations
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from backend.api.deps import get_intent_repo
from backend.db.repos.intent import IntentRepo

router = APIRouter()


class IntentNodeResponse(BaseModel):
    id: str
    name: str
    level: str
    parent_id: str | None
    intent_type: str
    keywords: list
    description: str


class CreateIntentNodeRequest(BaseModel):
    name: str
    level: str
    parent_id: str | None = None
    intent_type: str = "kb"
    keywords: list[str] = []
    description: str = ""


@router.get("/nodes", response_model=list[IntentNodeResponse])
async def get_intent_tree(
    repo: IntentRepo = Depends(get_intent_repo),
) -> list[IntentNodeResponse]:
    nodes = await repo.list_intent_nodes()
    return [
        IntentNodeResponse(
            id=n.id, name=n.name, level=n.level, parent_id=n.parent_id,
            intent_type=n.intent_type, keywords=n.keywords, description=n.description,
        )
        for n in nodes
    ]


@router.post("/nodes", status_code=status.HTTP_201_CREATED, response_model=IntentNodeResponse)
async def add_intent_node(
    body: CreateIntentNodeRequest,
    repo: IntentRepo = Depends(get_intent_repo),
) -> IntentNodeResponse:
    node = await repo.create_intent_node(**body.model_dump())
    return IntentNodeResponse(
        id=node.id, name=node.name, level=node.level, parent_id=node.parent_id,
        intent_type=node.intent_type, keywords=node.keywords, description=node.description,
    )


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_intent_node(
    node_id: str,
    repo: IntentRepo = Depends(get_intent_repo),
) -> None:
    await repo.delete_intent_node(node_id)
