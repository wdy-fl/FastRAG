from __future__ import annotations
import time
from backend.core.models.ingestion import IngestionConfig, IngestionContext, NodeResult

_STEPS = ["fetcher", "parser", "enhancer", "chunker", "enricher", "indexer"]


class IngestionEngine:
    def __init__(self, nodes: dict) -> None:
        self._nodes = nodes

    async def execute(
        self, config: IngestionConfig, context: IngestionContext
    ) -> IngestionContext:
        for step_name in _STEPS:
            step_config = getattr(config, step_name, None)
            node = self._nodes.get(step_name)

            if step_config is None or node is None:
                context.node_results.append(
                    NodeResult(node_name=step_name, status="skipped")
                )
                continue

            start = time.monotonic()
            try:
                context = await node.execute(context, step_config)
                context.node_results.append(
                    NodeResult(
                        node_name=step_name,
                        status="success",
                        duration_ms=int((time.monotonic() - start) * 1000),
                    )
                )
            except Exception as exc:
                context.node_results.append(
                    NodeResult(
                        node_name=step_name,
                        status="failed",
                        error=str(exc),
                        duration_ms=int((time.monotonic() - start) * 1000),
                    )
                )
                raise
        return context
