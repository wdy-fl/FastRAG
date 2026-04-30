import json
from backend.core.models.chat import LLMEvent


def parse_sse_line(line: str) -> LLMEvent | None:
    """Parse a single SSE data line into an LLMEvent. Returns None for non-content lines."""
    if not line.startswith("data: ") or line == "data: [DONE]":
        return None
    payload = json.loads(line[6:])
    delta = payload["choices"][0].get("delta", {})
    if "content" in delta and delta["content"]:
        return LLMEvent(type="content", content=delta["content"])
    if "reasoning_content" in delta and delta["reasoning_content"]:
        return LLMEvent(type="thinking", content=delta["reasoning_content"])
    return None
