from backend.core.models.ingestion import EnhanceTaskType

ENHANCER_SYSTEM_PROMPTS: dict[EnhanceTaskType, str] = {
    EnhanceTaskType.CONTEXT_ENHANCE: (
        "你是一个文档增强助手。"
        "重写提供的文本，使其更清晰、更丰富，"
        "同时保留所有原始信息。只返回重写后的文本。"
    ),
    EnhanceTaskType.KEYWORDS: (
        "从提供的文本中提取最重要的关键词和关键短语。"
        '以JSON字符串数组格式返回，例如 ["关键词1", "关键词2"]。'
        "只返回JSON数组，不要解释。"
    ),
    EnhanceTaskType.QUESTIONS: (
        "生成该文档能够回答的问题列表。"
        '以JSON字符串数组格式返回。'
        "只返回JSON数组，不要解释。"
    ),
    EnhanceTaskType.METADATA: (
        "从文档中提取结构化元数据，例如作者、日期、主题、"
        "文档类型及其他相关字段。"
        "以JSON对象格式返回。只返回JSON对象，不要解释。"
    ),
}
