from fastrag.core.rag.protocols import (
    LLMProvider, VectorStore, ConversationMemory,
    QueryRewriter, IntentClassifier,
)
from typing import runtime_checkable, Protocol


def test_protocols_are_protocols():
    import inspect
    assert inspect.isclass(LLMProvider)
    assert inspect.isclass(VectorStore)
