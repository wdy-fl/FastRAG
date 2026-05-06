from backend.core.models.ingestion import ChunkEnrichType

ENRICHER_SYSTEM_PROMPTS: dict[ChunkEnrichType, str] = {
    ChunkEnrichType.KEYWORDS: (
        "从提供的文本块中提取最重要的关键词。"
        '以JSON字符串数组格式返回，例如 ["关键词1", "关键词2"]。'
        "只返回JSON数组，不要解释。"
    ),
    ChunkEnrichType.SUMMARY: (
        "为提供的文本块写一两句简洁的摘要。"
        "只返回摘要文本，不要加标签或解释。"
    ),
    ChunkEnrichType.METADATA: (
        "从文本块中提取结构化信息，例如实体、"
        "日期、地点或其他相关字段。"
        "以JSON对象格式返回。只返回JSON对象，不要解释。"
    ),
}
