from __future__ import annotations
import json
from backend.core.models.intent import IntentNode, IntentResult
from backend.core.rag.protocols import LLMProvider

_CLASSIFY_PROMPT = (
    "You are an intent classifier. Given the following user query and the available intent nodes, "
    "identify the best matching intent node.\n"
    "Available nodes:\n{nodes}\n\n"
    "Query: {query}\n\n"
    "Respond with JSON only: {{\"confidence\": <0.0-1.0>, \"matched_id\": <node_id or null>}}"
)


class LLMIntentClassifier:
    def __init__(
        self,
        llm: LLMProvider,
        intent_nodes: list[IntentNode],
        confidence_threshold: float = 0.6,
    ) -> None:
        self._llm = llm
        self._nodes = intent_nodes
        self._threshold = confidence_threshold
        self._nodes_by_id: dict[str, IntentNode] = {n.id: n for n in intent_nodes}

    async def classify(self, query: str) -> IntentResult:
        nodes_text = "\n".join(
            f"- id={n.id} name={n.name} level={n.level} keywords={n.keywords}"
            for n in self._nodes
        )
        prompt = _CLASSIFY_PROMPT.format(nodes=nodes_text or "none", query=query)
        parts: list[str] = []
        async for event in await self._llm.stream(
            [{"role": "user", "content": prompt}]
        ):
            if event.type == "content":
                parts.append(event.content)
        raw = "".join(parts).strip()
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return IntentResult(needs_guidance=True, guidance_message="Intent classification failed.")

        confidence = float(data.get("confidence", 0.0))
        matched_id = data.get("matched_id")
        matched_node = self._nodes_by_id.get(matched_id) if matched_id else None

        if confidence < self._threshold:
            return IntentResult(
                confidence=confidence,
                needs_guidance=True,
                guidance_message="Please clarify your question.",
                candidates=list(self._nodes[:3]),
            )

        return IntentResult(
            matched_node=matched_node,
            confidence=confidence,
            needs_guidance=False,
        )
