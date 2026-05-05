from __future__ import annotations
from pydantic import BaseModel


class QueryTermMapping(BaseModel):
    id: str
    source_term: str
    target_term: str
    knowledge_base_id: str | None = None
