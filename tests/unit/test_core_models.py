import pytest
from pydantic import ValidationError
from backend.core.models.intent import IntentNode, IntentResult
from backend.core.models.knowledge import (
    KnowledgeBase, Document, DocumentChunk, ChunkWithEmbedding,
)
from backend.core.models.chat import (
    ChatRequest, ChatMessage, ConversationHistory,
    LLMEvent, GuidanceEvent, MetaEvent, RetrievedChunk,
    ChatEvent,
)
from backend.core.models.ingestion import (
    IngestionConfig, IngestionContext, NodeResult,
    FetcherSettings, ChunkerSettings,
)


def test_intent_node():
    node = IntentNode(id="n1", name="Finance")
    assert node.intent_type == "kb"
    assert node.keywords == []


def test_intent_result_defaults():
    r = IntentResult()
    assert r.confidence == 0.0
    assert r.needs_guidance is False


def test_chat_request():
    req = ChatRequest(query="hello", conversation_id="conv-1")
    assert req.query == "hello"


def test_conversation_history_empty():
    h = ConversationHistory()
    assert h.messages == []
    assert h.summary is None


def test_llm_event():
    e = LLMEvent(type="content", content="Hello")
    assert e.content == "Hello"


def test_guidance_event_has_intent():
    intent = IntentResult(needs_guidance=True, guidance_message="Which domain?")
    event = GuidanceEvent(intent=intent)
    assert event.type == "guidance"
    assert event.intent.needs_guidance is True


def test_retrieved_chunk():
    c = RetrievedChunk(content="text", score=0.95, document_id="doc-1")
    assert c.score == 0.95


def test_document_chunk():
    dc = DocumentChunk(content="chunk text", chunk_index=0)
    assert dc.metadata == {}


def test_chunk_with_embedding():
    dc = DocumentChunk(content="text", chunk_index=0)
    cwe = ChunkWithEmbedding(chunk=dc, embedding=[0.1, 0.2, 0.3])
    assert len(cwe.embedding) == 3


def test_ingestion_config_defaults():
    cfg = IngestionConfig(
        fetcher=FetcherSettings(source_type="local", source_uri="/tmp/file.pdf"),
        parser={"parser_type": "unstructured"},
        chunker=ChunkerSettings(),
    )
    assert cfg.enhancer is None
    assert cfg.chunker.chunk_size == 500


def test_conversation_orm_instantiation():
    from backend.db.models.conversation import ConversationORM
    c = ConversationORM(id="c1", title="Test")
    assert c.id == "c1"


def test_knowledge_chunk_orm_has_embedding_column():
    from backend.db.models.knowledge import KnowledgeChunkORM
    cols = {c.name for c in KnowledgeChunkORM.__table__.columns}
    assert "embedding" in cols
    assert "content" in cols


def test_ingestion_task_orm():
    from backend.db.models.ingestion import IngestionTaskORM
    t = IngestionTaskORM(id="t1", knowledge_base_id="kb1", document_id="d1")
    assert t.status == "pending"


def test_ingestion_context_fields():
    from backend.core.models.ingestion import ParserSettings
    cfg = IngestionConfig(
        fetcher=FetcherSettings(source_type="local", source_uri="/tmp/a.pdf"),
        parser=ParserSettings(),
        chunker=ChunkerSettings(),
    )
    ctx = IngestionContext(pipeline_id="p1", task_id="t1", config=cfg)
    assert ctx.chunks == []
    assert ctx.node_results == []


def test_chat_request_deep_thinking_default_false():
    req = ChatRequest(query="hello", conversation_id="c1")
    assert req.deep_thinking is False


def test_chat_request_deep_thinking_can_be_true():
    req = ChatRequest(query="hello", conversation_id="c1", deep_thinking=True)
    assert req.deep_thinking is True


def test_meta_event_has_task_id():
    e = MetaEvent(task_id="abc-123")
    assert e.type == "meta"
    assert e.task_id == "abc-123"


def test_done_event_has_title():
    e = LLMEvent(type="done", content="", title="测试标题")
    assert e.title == "测试标题"


def test_title_only_on_done_raises():
    with pytest.raises(ValidationError):
        LLMEvent(type="content", title="oops")


def test_intent_node_has_knowledge_base_id():
    from backend.core.models.intent import IntentNode
    node = IntentNode(id="n1", name="test", knowledge_base_id="kb-1")
    assert node.knowledge_base_id == "kb-1"

def test_intent_node_knowledge_base_id_defaults_none():
    from backend.core.models.intent import IntentNode
    node = IntentNode(id="n1", name="test")
    assert node.knowledge_base_id is None

def test_intent_node_intent_type_includes_system():
    from backend.core.models.intent import IntentNode
    node = IntentNode(id="n1", name="chitchat", intent_type="system")
    assert node.intent_type == "system"

def test_intent_node_intent_type_defaults_kb():
    from backend.core.models.intent import IntentNode
    node = IntentNode(id="n1", name="test")
    assert node.intent_type == "kb"
