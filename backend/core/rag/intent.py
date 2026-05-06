from __future__ import annotations
import json
import logging
from backend.core.models.intent import IntentNode, IntentResult
from backend.core.rag.protocols import LLMProvider
from backend.infra.cache.redis import RedisCache

logger = logging.getLogger("backend.rag.intent")

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
        intent_repo: "IntentRepo | None" = None,
        cache: RedisCache | None = None,
        confidence_threshold: float = 0.6,
        intent_nodes: list[IntentNode] | None = None,
    ) -> None:
        self._llm = llm
        self._repo = intent_repo
        self._cache = cache
        self._threshold = confidence_threshold
        self._static_nodes: list[IntentNode] = intent_nodes or []

    async def _load_nodes(self) -> list[IntentNode]:
        if self._repo is not None:
            CACHE_KEY = "intent:nodes"
            if self._cache:
                try:
                    cached = await self._cache.get(CACHE_KEY)
                    if cached:
                        return [IntentNode.model_validate_json(n) for n in json.loads(cached)]
                except Exception:
                    pass

            from backend.db.repos.intent import IntentRepo
            orm_nodes = await self._repo.list_intent_nodes()
            nodes = [
                IntentNode(
                    id=n.id, name=n.name,
                    intent_type=n.intent_type, keywords=n.keywords or [],
                    description=n.description or "",
                    knowledge_base_id=n.knowledge_base_id,
                )
                for n in orm_nodes
            ]

            if self._cache:
                try:
                    payload = json.dumps([n.model_dump_json() for n in nodes])
                    await self._cache.set(CACHE_KEY, payload, ttl=7200)
                except Exception:
                    pass

            return nodes

        return self._static_nodes

    async def classify(self, query: str) -> IntentResult:
        nodes = await self._load_nodes()
        if not nodes:
            logger.info("意图分类 | 无意图节点配置，跳过分类 | query=%r", query)
            return IntentResult(needs_guidance=False, confidence=1.0)

        nodes_text = "\n".join(
            f"- id={n.id} name={n.name} keywords={n.keywords} description={n.description}"
            for n in nodes
        )
        prompt = _CLASSIFY_PROMPT.format(nodes=nodes_text or "none", query=query)
        parts: list[str] = []
        async for event in self._llm.stream(
            [{"role": "user", "content": prompt}]
        ):
            if event.type == "content":
                parts.append(event.content)
        raw = "".join(parts).strip()
        logger.debug("意图分类 | LLM原始响应 | %s", raw)
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            logger.warning("意图分类 | JSON解析失败 | raw=%s", raw[:200])
            return IntentResult(needs_guidance=True, guidance_message="Intent classification failed.")

        confidence = float(data.get("confidence", 0.0))
        matched_id = data.get("matched_id")
        nodes_by_id = {n.id: n for n in nodes}
        matched_node = nodes_by_id.get(matched_id) if matched_id else None

        if matched_id is None:
            logger.info(
                "意图分类 | 无匹配节点 → system回退 | query=%r | confidence=%.2f",
                query, confidence,
            )
            return IntentResult(
                matched_node=None,
                confidence=confidence,
                needs_guidance=False,
            )

        if confidence < self._threshold:
            logger.info(
                "意图分类 | 低置信度 → 引导 | query=%r | confidence=%.2f < threshold=%.2f | matched_id=%s",
                query, confidence, self._threshold, matched_id,
            )
            return IntentResult(
                confidence=confidence,
                needs_guidance=True,
                guidance_message="Please clarify your question.",
                candidates=list(nodes[:3]),
            )

        logger.info(
            "意图分类 | 命中 | query=%r | confidence=%.2f | matched=%s (type=%s, kb=%s)",
            query, confidence,
            matched_node.name if matched_node else None,
            matched_node.intent_type if matched_node else None,
            matched_node.knowledge_base_id if matched_node else None,
        )
        return IntentResult(
            matched_node=matched_node,
            confidence=confidence,
            needs_guidance=False,
        )
