from backend.core.models.ingestion import ChunkEnrichType

ENRICHER_SYSTEM_PROMPTS: dict[ChunkEnrichType, str] = {
    ChunkEnrichType.KEYWORDS: (
        "Extract the most important keywords from the provided text chunk. "
        "Return a JSON array of strings, e.g. [\"keyword1\", \"keyword2\"]. "
        "Return only the JSON array, no explanation."
    ),
    ChunkEnrichType.SUMMARY: (
        "Write a concise one or two sentence summary of the provided text chunk. "
        "Return only the summary text, no labels or explanation."
    ),
    ChunkEnrichType.METADATA: (
        "Extract any structured information from the text chunk such as entities, "
        "dates, locations, or other relevant fields. "
        "Return a JSON object. Return only the JSON object, no explanation."
    ),
}
