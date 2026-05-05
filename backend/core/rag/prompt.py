from __future__ import annotations
import logging
from backend.core.models.chat import ConversationHistory, RetrievedChunk
from backend.core.models.intent import IntentResult

logger = logging.getLogger("backend.rag.prompt")

_DEFAULT_SYSTEM = (
    "You are a helpful assistant. Answer the user's question based on the provided context. "
    "If the context does not contain relevant information, say so honestly.\n\n"
    "When you use information from a specific context fragment, cite it using the bracket number, "
    "e.g. [1], [2]. Place the citation immediately after the statement it supports. "
    "You may cite multiple sources for a single statement, e.g. [1][2]."
)


class PromptBuilder:
    def __init__(self, system_prompt: str = _DEFAULT_SYSTEM) -> None:
        self._system = system_prompt

    def build(
        self,
        query: str,
        history: ConversationHistory,
        retrieved: list[RetrievedChunk],
        intents: list[IntentResult],
    ) -> list[dict]:
        messages: list[dict] = [{"role": "system", "content": self._system}]

        if history.summary:
            messages.append({
                "role": "system",
                "content": f"Previous conversation summary: {history.summary}",
            })

        for msg in history.messages:
            messages.append({"role": msg.role, "content": msg.content})

        if retrieved:
            context_text = "\n\n".join(
                f"[{i+1}] {chunk.content}" for i, chunk in enumerate(retrieved)
            )
            messages.append({
                "role": "system",
                "content": f"Relevant context:\n{context_text}",
            })

        messages.append({"role": "user", "content": query})
        logger.info(
            "构建Prompt | messages=%d | history=%d | chunks=%d | has_summary=%s",
            len(messages), len(history.messages), len(retrieved),
            "是" if history.summary else "否",
        )
        return messages
