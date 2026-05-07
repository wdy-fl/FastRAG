from __future__ import annotations
import logging
from backend.core.models.chat import ConversationHistory
from backend.core.rag.protocols import LLMProvider

logger = logging.getLogger("backend.rag.rewrite")

_REWRITE_PROMPT = (
    "你是一个查询改写器。根据对话历史，将当前查询改写为独立、完整的查询。\n\n"
    "改写原则：\n"
    "- 最小必要改写：只补充历史中明确的指代信息，不添加、不推断、不回答\n"
    "- 解析代词（它/他/这/那/上面/之前等）为历史中提到的具体实体\n"
    "- 补全省略（如「还有呢」→「年假还有哪些规定」）\n"
    "- 无代词且无省略时，原样返回查询，不做任何修改\n\n"
    "示例：\n"
    "历史: user: 公司的年假政策是什么？\nassistant: 入职满一年可享5天年假。\n"
    "当前查询: 它和病假有什么区别？\n"
    "改写: 公司年假和病假有什么区别？\n\n"
    "历史: user: 报销流程是怎样的？\nassistant: 需填写报销单并附发票，提交给部门主管审批。\n"
    "当前查询: 审批要多久？\n"
    "改写: 报销审批要多久？\n\n"
    "历史: none\n"
    "当前查询: 公司有哪些福利？\n"
    "改写: 公司有哪些福利？\n\n"
    "只输出改写后的查询，不要解释。\n"
    "对话历史:\n{history}\n当前查询: {query}"
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
        result = (await self._llm.chat([{"role": "user", "content": prompt}])).strip() or query
        logger.info("查询改写完成 | %r → %r", query, result)
        return result

