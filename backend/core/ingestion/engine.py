from __future__ import annotations
import time
from collections.abc import Awaitable, Callable
from backend.core.models.ingestion import IngestionConfig, IngestionContext, NodeResult

_STEPS = ["fetcher", "parser", "enhancer", "chunker", "enricher", "indexer"]


class IngestionEngine:
    def __init__(self, nodes: dict) -> None:
        self._nodes = nodes

    async def execute(
        self,
        config: IngestionConfig,
        context: IngestionContext,
        on_node_complete: Callable[[str, NodeResult], Awaitable[None]] | None = None,
    ) -> IngestionContext:
        for step_name in _STEPS:
            step_config = getattr(config, step_name, None)
            node = self._nodes.get(step_name)

            if step_config is None or node is None:
                result = NodeResult(node_name=step_name, status="skipped")
                context.node_results.append(result)
                if on_node_complete:
                    await on_node_complete(step_name, result)
                continue

            start = time.monotonic()
            try:
                context = await node.execute(context, step_config)
                result = NodeResult(
                    node_name=step_name,
                    status="success",
                    duration_ms=int((time.monotonic() - start) * 1000),
                )
                context.node_results.append(result)
                if on_node_complete:
                    await on_node_complete(step_name, result)
            except Exception as exc:
                result = NodeResult(
                    node_name=step_name,
                    status="failed",
                    error=str(exc),
                    duration_ms=int((time.monotonic() - start) * 1000),
                )
                context.node_results.append(result)
                if on_node_complete:
                    await on_node_complete(step_name, result)
                raise
        return context
