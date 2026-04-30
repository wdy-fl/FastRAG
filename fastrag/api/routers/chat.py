from __future__ import annotations
import asyncio
import json
import uuid
from typing import AsyncIterator
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastrag.api.deps import get_rag_pipeline, get_llm_provider
from fastrag.core.models.chat import ChatRequest, LLMEvent, GuidanceEvent, MetaEvent
from fastrag.core.rag.pipeline import RAGPipeline
from fastrag.infra.llm.client import OpenAICompatClient

router = APIRouter()

# 进程内 task 注册表：task_id -> asyncio.Task
_task_registry: dict[str, asyncio.Task] = {}  # type: ignore[type-arg]


async def _event_stream(
    request: ChatRequest,
    pipeline: RAGPipeline,
    task_id: str,
    llm: OpenAICompatClient,
) -> AsyncIterator[str]:
    # 1. 发送 meta 事件
    meta = MetaEvent(task_id=task_id)
    yield f"data: {json.dumps(meta.model_dump(), ensure_ascii=False)}\n\n"

    # 2. 流式返回 pipeline 事件
    async for event in pipeline.chat(request):
        if isinstance(event, LLMEvent):
            if event.type == "done":
                continue  # done 在最后统一发送（加 title）
            payload = {"type": event.type, "content": event.content}
        elif isinstance(event, GuidanceEvent):
            payload = {
                "type": "guidance",
                "intent": event.intent.model_dump(),
            }
        else:
            continue
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    # 3. 生成会话标题
    title = await _generate_title(request.query, llm)

    # 4. 发送 done 事件（含 title）
    done_payload = {"type": "done", "content": "", "title": title}
    yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"


async def _generate_title(query: str, llm: OpenAICompatClient) -> str:
    """用 LLM 为会话生成 10 字以内的标题，失败时降级。"""
    try:
        messages = [
            {
                "role": "user",
                "content": f"请用10字以内总结以下问题作为对话标题，只输出标题文字：{query}",
            }
        ]
        title_parts: list[str] = []
        async for event in llm.stream(messages, max_tokens=30):
            if event.type == "content":
                title_parts.append(event.content)
        title = "".join(title_parts).strip()
        return title if title else query[:30]
    except Exception:
        return query[:30]


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    pipeline: RAGPipeline = Depends(get_rag_pipeline),
    llm: OpenAICompatClient = Depends(get_llm_provider),
) -> StreamingResponse:
    task_id = str(uuid.uuid4())

    async def _managed_stream():
        try:
            async for chunk in _event_stream(request, pipeline, task_id, llm):
                yield chunk
        except asyncio.CancelledError:
            pass
        finally:
            _task_registry.pop(task_id, None)

    _task_registry[task_id] = asyncio.current_task()  # type: ignore[assignment]
    return StreamingResponse(
        _managed_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class StopRequest(BaseModel):
    task_id: str


@router.post("/stop")
async def chat_stop(body: StopRequest) -> dict:
    if body.task_id not in _task_registry:
        raise HTTPException(status_code=404, detail="task not found")
    task = _task_registry.pop(body.task_id)
    if not task.done():
        task.cancel()
    return {"status": "cancelled", "task_id": body.task_id}
