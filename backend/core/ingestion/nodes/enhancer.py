from __future__ import annotations
from backend.core.models.ingestion import EnhancerSettings, EnhanceTaskType, IngestionContext
from backend.core.ingestion.util.json_response_parser import parse_string_list, parse_object
from backend.core.ingestion.util.template import render_template
from backend.core.ingestion.prompt.enhancer_prompts import ENHANCER_SYSTEM_PROMPTS
from backend.infra.llm.client import OpenAICompatClient


class EnhancerNode:
    name = "enhancer"

    def __init__(self, llm: OpenAICompatClient) -> None:
        self._llm = llm

    async def execute(
        self, context: IngestionContext, config: EnhancerSettings
    ) -> IngestionContext:
        if not config.tasks:
            return context

        for task in config.tasks:
            if task.type is None:
                continue

            # CONTEXT_ENHANCE 始终用原始文本；其他 task 优先用 enhanced_text
            if task.type == EnhanceTaskType.CONTEXT_ENHANCE:
                input_text = context.parsed_text or ""
            else:
                input_text = context.enhanced_text or context.parsed_text or ""

            if not input_text:
                continue

            system = task.system_prompt or ENHANCER_SYSTEM_PROMPTS.get(task.type, "")
            user = render_template(
                task.user_prompt_template,
                text=input_text,
                mime_type=context.metadata.get("mime_type", ""),
            )
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
            response = await self._llm.chat(messages, model=config.model_id)

            if task.type == EnhanceTaskType.CONTEXT_ENHANCE:
                context.enhanced_text = response.strip()
            elif task.type == EnhanceTaskType.KEYWORDS:
                context.keywords = parse_string_list(response)
            elif task.type == EnhanceTaskType.QUESTIONS:
                context.questions = parse_string_list(response)
            elif task.type == EnhanceTaskType.METADATA:
                context.metadata.update(parse_object(response))

        return context
