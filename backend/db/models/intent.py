from __future__ import annotations
from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.db.models.base import Base


class IntentNodeORM(Base):
    __tablename__ = "intent_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    level: Mapped[str] = mapped_column(String(20))
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("intent_nodes.id"), nullable=True
    )
    intent_type: Mapped[str] = mapped_column(String(10), default="kb")
    keywords: Mapped[list] = mapped_column(JSON, default=[])
    description: Mapped[str] = mapped_column(Text, default="")
