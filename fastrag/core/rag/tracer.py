from __future__ import annotations
import time
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable, Protocol
from uuid import uuid4


class TraceRepoProtocol(Protocol):
    async def create_run(
        self, run_id: str, conversation_id: str, query: str
    ) -> Any: ...

    async def update_run(
        self, run_id: str, status: str, total_duration_ms: int
    ) -> None: ...

    async def save_node(
        self,
        run_id: str,
        node_id: str,
        node_name: str,
        status: str,
        duration_ms: int,
        detail: dict | None = None,
    ) -> None: ...


class RagTracer:
    def __init__(self, repo: TraceRepoProtocol) -> None:
        self._repo = repo
        self._current_run_id: ContextVar[str | None] = ContextVar(
            "trace_run_id", default=None
        )

    async def start_run(self, conversation_id: str, query: str) -> str:
        run_id = str(uuid4())
        self._current_run_id.set(run_id)
        await self._repo.create_run(
            run_id=run_id, conversation_id=conversation_id, query=query
        )
        return run_id

    async def finish_run(self, status: str, total_duration_ms: int) -> None:
        run_id = self._current_run_id.get()
        if run_id:
            await self._repo.update_run(
                run_id=run_id,
                status=status,
                total_duration_ms=total_duration_ms,
            )
            self._current_run_id.set(None)

    def trace_node(self, node_name: str) -> Callable:
        def decorator(fn: Callable) -> Callable:
            @wraps(fn)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                run_id = self._current_run_id.get()
                if not run_id:
                    return await fn(*args, **kwargs)
                start = time.monotonic()
                node_id = str(uuid4())
                try:
                    result = await fn(*args, **kwargs)
                    await self._repo.save_node(
                        run_id=run_id,
                        node_id=node_id,
                        node_name=node_name,
                        status="success",
                        duration_ms=int((time.monotonic() - start) * 1000),
                    )
                    return result
                except Exception as exc:
                    await self._repo.save_node(
                        run_id=run_id,
                        node_id=node_id,
                        node_name=node_name,
                        status="failed",
                        duration_ms=int((time.monotonic() - start) * 1000),
                        detail={"error": str(exc)},
                    )
                    raise

            return wrapper

        return decorator
