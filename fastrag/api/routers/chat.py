from __future__ import annotations
import json
from typing import AsyncIterator
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from fastrag.api.deps import get_rag_pipeline
from fastrag.core.models.chat import ChatRequest, LLMEvent, GuidanceEvent
from fastrag.core.rag.pipeline import RAGPipeline

router = APIRouter()


async def _event_stream(
    request: ChatRequest, pipeline: RAGPipeline
) -> AsyncIterator[str]:
    async for event in pipeline.chat(request):
        if isinstance(event, LLMEvent):
            payload = {"type": event.type, "content": event.content}
        elif isinstance(event, GuidanceEvent):
            payload = {
                "type": "guidance",
                "intent": event.intent.model_dump(),
            }
        else:
            continue
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    pipeline: RAGPipeline = Depends(get_rag_pipeline),
) -> StreamingResponse:
    return StreamingResponse(
        _event_stream(request, pipeline),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
