from __future__ import annotations
import asyncio
import logging
from backend.core.models.chat import ConversationHistory, ChatMessage
from backend.core.rag.protocols import LLMProvider

logger = logging.getLogger("backend.rag.memory")


class SlidingWindowMemory:
    def __init__(
        self,
        repo: object,  # ConversationRepo — avoided direct import to keep core clean
        llm: LLMProvider,
        window_size: int = 4,
        summary_threshold: int = 5,
    ) -> None:
        self._repo = repo
        self._llm = llm
        self._window_size = window_size
        self._summary_threshold = summary_threshold

    async def load(self, conversation_id: str) -> ConversationHistory:
        recent, summary_orm = await asyncio.gather(
            self._repo.get_recent_messages(conversation_id, limit=self._window_size),
            self._repo.get_summary(conversation_id),
        )
        messages = [
            ChatMessage(role=msg.role, content=msg.content) for msg in recent
        ]
        summary_text = summary_orm.content if summary_orm else None
        logger.info(
            "加载会话历史 | conv=%s | messages=%d | summary=%s",
            conversation_id, len(messages), "有" if summary_text else "无",
        )
        return ConversationHistory(messages=messages, summary=summary_text)

    async def save(
        self, conversation_id: str, query: str, answer: str
    ) -> None:
        await self._repo.save_message(conversation_id, role="user", content=query)
        await self._repo.save_message(
            conversation_id, role="assistant", content=answer
        )
        total = await self._repo.count_messages(conversation_id)
        logger.info(
            "保存会话记忆 | conv=%s | total_messages=%d | answer_len=%d",
            conversation_id, total, len(answer),
        )
        if total >= self._summary_threshold:
            logger.info("触发摘要压缩 | conv=%s | total=%d >= threshold=%d", conversation_id, total, self._summary_threshold)
            asyncio.create_task(self._compress_summary(conversation_id))

    async def _compress_summary(self, conversation_id: str) -> None:
        logger.info("摘要压缩开始 | conv=%s", conversation_id)
        recent = await self._repo.get_recent_messages(
            conversation_id, limit=self._window_size * 2
        )
        existing = await self._repo.get_summary(conversation_id)
        existing_text = existing.content if existing else ""
        history_text = "\n".join(
            f"{msg.role}: {msg.content}" for msg in recent
        )
        prompt = (
            f"Summarize this conversation history concisely.\n"
            f"Previous summary: {existing_text}\n"
            f"Recent messages:\n{history_text}"
        )
        parts: list[str] = []
        async for event in self._llm.stream(
            [{"role": "user", "content": prompt}]
        ):
            if event.type == "content":
                parts.append(event.content)
        new_summary = "".join(parts)
        if recent:
            up_to_seq = max(msg.seq for msg in recent)
        else:
            up_to_seq = 0
        await self._repo.upsert_summary(
            conversation_id, content=new_summary, up_to_seq=up_to_seq
        )
        logger.info("摘要压缩完成 | conv=%s | summary_len=%d", conversation_id, len(new_summary))
