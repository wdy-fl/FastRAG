from __future__ import annotations
from fastrag.core.models.chat import ConversationHistory
from fastrag.core.rag.protocols import LLMProvider

_REWRITE_PROMPT = (
    "You are a query optimizer. Given the conversation history and the current query, "
    "rewrite the query to be more specific and self-contained. "
    "Return only the rewritten query, no explanations.\n"
    "Conversation history: {history}\nCurrent query: {query}"
)

_SPLIT_PROMPT = (
    "You are a query analyzer. If the following query contains multiple distinct questions, "
    "split it into a numbered list of sub-questions. If it is a single question, return it as '1. <query>'.\n"
    "Return only the numbered list.\nQuery: {query}"
)


class LLMQueryRewriter:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def rewrite(self, query: str, history: ConversationHistory) -> str:
        history_text = "\n".join(
            f"{m.role}: {m.content}" for m in history.messages[-4:]
        )
        prompt = _REWRITE_PROMPT.format(history=history_text or "none", query=query)
        parts: list[str] = []
        async for event in await self._llm.stream(
            [{"role": "user", "content": prompt}]
        ):
            if event.type == "content":
                parts.append(event.content)
        return "".join(parts).strip() or query

    async def split(self, query: str) -> list[str]:
        prompt = _SPLIT_PROMPT.format(query=query)
        parts: list[str] = []
        async for event in await self._llm.stream(
            [{"role": "user", "content": prompt}]
        ):
            if event.type == "content":
                parts.append(event.content)
        raw = "".join(parts).strip()
        lines = [
            line.lstrip("0123456789. ").strip()
            for line in raw.splitlines()
            if line.strip()
        ]
        return [q for q in lines if q] or [query]
