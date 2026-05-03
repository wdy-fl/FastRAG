from __future__ import annotations
from backend.core.models.ingestion import EnricherSettings, ChunkEnrichType, IngestionContext
from backend.core.ingestion.util.json_response_parser import parse_string_list, parse_object
from backend.core.ingestion.util.template import render_template
from backend.core.ingestion.prompt.enricher_prompts import ENRICHER_SYSTEM_PROMPTS
from backend.infra.llm.client import OpenAICompatClient


class EnricherNode:
    name = "enricher"

    def __init__(self, llm: OpenAICompatClient) -> None:
        self._llm = llm

    async def execute(
        self, context: IngestionContext, config: EnricherSettings
    ) -> IngestionContext:
        if not config.tasks:
            return context

        for chunk in context.chunks:
            if not chunk.content:
                continue

            if config.attach_document_metadata and context.metadata:
                chunk.metadata.update(context.metadata)

            for task in config.tasks:
                if task.type is None:
                    continue

                system = task.system_prompt or ENRICHER_SYSTEM_PROMPTS.get(task.type, "")
                user = render_template(
                    task.user_prompt_template,
                    text=chunk.content,
                    chunk_index=chunk.chunk_index,
                )
                messages = [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ]
                response = await self._llm.chat(messages, model=config.model_id)

                if task.type == ChunkEnrichType.KEYWORDS:
                    chunk.metadata["keywords"] = parse_string_list(response)
                elif task.type == ChunkEnrichType.SUMMARY:
                    chunk.metadata["summary"] = response.strip()
                elif task.type == ChunkEnrichType.METADATA:
                    chunk.metadata.update(parse_object(response))

        return context
