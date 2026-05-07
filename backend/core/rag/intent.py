from __future__ import annotations
import json
import logging
from backend.core.models.intent import IntentMatch, IntentNode, IntentResult
from backend.core.rag.protocols import LLMProvider
from backend.infra.cache.redis import RedisCache

logger = logging.getLogger("backend.rag.intent")

_CLASSIFY_PROMPT = (
    "你是一个意图分类器。根据用户查询和可用的意图节点，识别匹配的意图节点。\n\n"
    "规则：\n"
    "- 对每个可能匹配的节点，给出 confidence 等级：high（几乎确定相关）、medium（可能相关）、low（不太相关）\n"
    "- 只返回 medium 及以上的匹配，忽略 low\n"
    "- 如果没有任何节点相关，返回空列表\n"
    "- 一个查询可以匹配多个节点\n\n"
    "示例：\n"
    "可用节点:\n"
    "- id=n1 name=年假政策 keywords=['年假','假期'] description=公司年假相关规定\n"
    "- id=n2 name=报销流程 keywords=['报销','费用'] description=费用报销流程指南\n\n"
    '查询: 年假怎么申请？→ {{"matches": [{{"id": "n1", "confidence": "high"}}]}}\n'
    '查询: 年假和报销的区别？→ {{"matches": [{{"id": "n1", "confidence": "high"}}, {{"id": "n2", "confidence": "high"}}]}}\n'
    '查询: 今天天气怎么样？→ {{"matches": []}}\n\n'
    "可用节点:\n{nodes}\n\n"
    "查询: {query}\n\n"
    '仅以JSON格式回复，不要解释: {{"matches": [{{"id": "<节点id>", "confidence": "high|medium"}}]}}'
)


class LLMIntentClassifier:
    def __init__(
        self,
        llm: LLMProvider,
        intent_repo: "IntentRepo | None" = None,
        cache: RedisCache | None = None,
        intent_nodes: list[IntentNode] | None = None,
    ) -> None:
        self._llm = llm
        self._repo = intent_repo
        self._cache = cache
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
            return IntentResult()

        nodes_text = "\n".join(
            f"- id={n.id} name={n.name} keywords={n.keywords} description={n.description}"
            for n in nodes
        )
        prompt = _CLASSIFY_PROMPT.format(nodes=nodes_text or "none", query=query)
        raw = await self._llm.chat([{"role": "user", "content": prompt}])
        raw = raw.strip()
        logger.debug("意图分类 | LLM响应 | %s", raw)
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            logger.warning("意图分类 | JSON解析失败 | raw=%s", raw[:200])
            return IntentResult(needs_guidance=True, guidance_message="意图分类失败。")

        raw_matches = data.get("matches", [])
        if not isinstance(raw_matches, list):
            raw_matches = []
        nodes_by_id = {n.id: n for n in nodes}

        matches: list[IntentMatch] = []
        for item in raw_matches:
            mid = item.get("id")
            conf = item.get("confidence", "medium")
            if mid and mid in nodes_by_id and conf in ("high", "medium", "low"):
                matches.append(IntentMatch(node=nodes_by_id[mid], confidence=conf))

        # 只保留 medium 及以上
        matches = [m for m in matches if m.confidence in ("high", "medium")]

        if not matches:
            logger.info("意图分类 | 无匹配节点 → system回退 | query=%r", query)
            return IntentResult()

        # 有 medium 但没有 high → 需要引导
        has_high = any(m.confidence == "high" for m in matches)
        if not has_high:
            logger.info(
                "意图分类 | 仅有medium匹配 → 引导 | query=%r | matches=%s",
                query, [(m.node.name, m.confidence) for m in matches],
            )
            return IntentResult(
                matches=matches,
                needs_guidance=True,
                guidance_message="请进一步澄清您的问题。",
                candidates=[m.node for m in matches[:3]],
            )

        logger.info(
            "意图分类 | 命中 | query=%r | matches=%s",
            query, [(m.node.name, m.confidence, m.node.knowledge_base_id) for m in matches],
        )
        return IntentResult(matches=matches, needs_guidance=False)
