from __future__ import annotations
import logging
from backend.core.models.chat import ConversationHistory, RetrievedChunk
from backend.core.models.intent import IntentResult

logger = logging.getLogger("backend.rag.prompt")

_DEFAULT_SYSTEM = (
    "你是一个基于知识库的智能问答助手。你只能根据检索到的知识库内容回答用户的问题，"
    "不能凭空编造上下文中没有的信息。当用户询问你的身份时，请告知你是基于知识库的智能问答助手。\n\n"
    "回答要求：\n"
    "- 使用中文回答\n"
    "- 当你引用某个上下文片段时，在陈述末尾用方括号标注编号，如 [1]、[2]\n"
    "- 可在同一处引用多个来源，如 [1][2]\n"
    "- 如果上下文中没有相关信息，请如实告知，不要编造\n\n"
    "回答示例：\n"
    "用户问题：公司的年假政策是什么？\n"
    "上下文：\n"
    "[1] 员工入职满一年后可享受5天年假，每增加一年工龄年假增加1天，上限为15天。\n"
    "[2] 年假需提前3个工作日申请，经直属主管审批后方可生效。\n\n"
    "回答：根据公司规定，员工入职满一年后可享受5天年假，每增加一年工龄年假增加1天，上限为15天[1]。"
    "年假需提前3个工作日申请，经直属主管审批后方可生效[2]。"
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
                "content": f"历史对话摘要：\n{history.summary}",
            })

        for msg in history.messages:
            messages.append({"role": msg.role, "content": msg.content})

        if retrieved:
            context_text = "\n\n".join(
                f"[{i+1}] {chunk.content}" for i, chunk in enumerate(retrieved)
            )
            messages.append({
                "role": "system",
                "content": f"<retrieved_context>\n{context_text}\n</retrieved_context>",
            })

        messages.append({"role": "user", "content": query})
        logger.info(
            "构建Prompt | messages=%d | history=%d | chunks=%d | has_summary=%s",
            len(messages), len(history.messages), len(retrieved),
            "是" if history.summary else "否",
        )
        return messages
