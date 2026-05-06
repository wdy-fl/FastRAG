from __future__ import annotations
import logging
from backend.core.models.chat import ConversationHistory
from backend.core.rag.protocols import LLMProvider

logger = logging.getLogger("backend.rag.rewrite")

_REWRITE_PROMPT = (
    "你是一个查询改写器。你的唯一任务是改写查询，使其更清晰、更完整。严格规则：\n"
    "- 只做改写，绝对不要回答或回应查询的内容\n"
    "- 只使用查询或历史中明确提到的信息\n"
    "- 修正语法、解析代词、澄清模糊引用\n"
    "- 如果没有历史记录或歧义，原样返回查询，不做任何修改\n"
    "只返回改写后的查询，不要解释。\n"
    "对话历史: {history}\n当前查询: {query}"
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
        logger.debug("查询改写 | query=%r | history_lines=%d", query, len(history.messages[-4:]))
        parts: list[str] = []
        async for event in self._llm.stream(
            [{"role": "user", "content": prompt}]
        ):
            if event.type == "content":
                parts.append(event.content)
        result = "".join(parts).strip() or query
        logger.info("查询改写完成 | %r → %r", query, result)
        return result

    async def split(self, query: str) -> list[str]:
        prompt = _SPLIT_PROMPT.format(query=query)
        logger.debug("查询拆分 | query=%r", query)
        parts: list[str] = []
        async for event in self._llm.stream(
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
        result = [q for q in lines if q] or [query]
        logger.info("查询拆分完成 | count=%d | sub_queries=%s", len(result), result)
        return result
