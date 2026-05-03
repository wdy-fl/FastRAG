from backend.core.models.ingestion import EnhanceTaskType

ENHANCER_SYSTEM_PROMPTS: dict[EnhanceTaskType, str] = {
    EnhanceTaskType.CONTEXT_ENHANCE: (
        "You are a document enhancement assistant. "
        "Rewrite the provided text to be clearer and more informative, "
        "preserving all original information. Return only the rewritten text."
    ),
    EnhanceTaskType.KEYWORDS: (
        "Extract the most important keywords and key phrases from the provided text. "
        "Return a JSON array of strings, e.g. [\"keyword1\", \"keyword2\"]. "
        "Return only the JSON array, no explanation."
    ),
    EnhanceTaskType.QUESTIONS: (
        "Generate a list of questions that this document can answer. "
        "Return a JSON array of question strings. "
        "Return only the JSON array, no explanation."
    ),
    EnhanceTaskType.METADATA: (
        "Extract structured metadata from the document such as author, date, topic, "
        "document type, and any other relevant fields. "
        "Return a JSON object. Return only the JSON object, no explanation."
    ),
}
