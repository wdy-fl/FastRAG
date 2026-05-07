import pytest
from uuid import uuid4
from backend.db.repos.conversation import ConversationRepo
from backend.db.repos.knowledge import KnowledgeRepo
from backend.db.repos.trace import TraceRepo
from backend.db.models.conversation import ConversationORM


@pytest.mark.asyncio
async def test_save_and_get_messages(db_session):
    repo = ConversationRepo(db_session)
    conv_id = str(uuid4())

    # Create conversation first
    db_session.add(ConversationORM(id=conv_id, title="Test conv"))
    await db_session.commit()

    await repo.save_message(conv_id, role="user", content="hello")
    await repo.save_message(conv_id, role="assistant", content="hi there")

    messages = await repo.get_recent_messages(conv_id, limit=10)
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"


@pytest.mark.asyncio
async def test_count_messages(db_session):
    repo = ConversationRepo(db_session)
    conv_id = str(uuid4())
    db_session.add(ConversationORM(id=conv_id, title="Count test"))
    await db_session.commit()

    count_before = await repo.count_messages(conv_id)
    assert count_before == 0

    await repo.save_message(conv_id, role="user", content="msg1")
    count_after = await repo.count_messages(conv_id)
    assert count_after == 1


@pytest.mark.asyncio
async def test_get_summary_none_initially(db_session):
    repo = ConversationRepo(db_session)
    conv_id = str(uuid4())
    db_session.add(ConversationORM(id=conv_id, title="Summary test"))
    await db_session.commit()

    summary = await repo.get_summary(conv_id)
    assert summary is None


@pytest.mark.asyncio
async def test_upsert_summary(db_session):
    repo = ConversationRepo(db_session)
    conv_id = str(uuid4())
    db_session.add(ConversationORM(id=conv_id, title="Upsert test"))
    await db_session.commit()

    await repo.upsert_summary(conv_id, content="Summary text", up_to_seq=5)
    summary = await repo.get_summary(conv_id)
    assert summary is not None
    assert summary.content == "Summary text"
    assert summary.summarized_up_to_seq == 5

    # Upsert again — should update
    await repo.upsert_summary(conv_id, content="Updated summary", up_to_seq=10)
    summary2 = await repo.get_summary(conv_id)
    assert summary2.content == "Updated summary"


@pytest.mark.asyncio
async def test_create_and_update_document(db_session):
    from backend.db.models.knowledge import KnowledgeBaseORM
    from uuid import uuid4

    kb_id = str(uuid4())
    db_session.add(KnowledgeBaseORM(
        id=kb_id, name=f"KB-{kb_id[:8]}", ingestion_config={}
    ))
    await db_session.commit()

    repo = KnowledgeRepo(db_session)
    doc = await repo.create_document(
        knowledge_base_id=kb_id,
        filename="report.pdf",
        source_type="local",
        source_uri="/tmp/report.pdf",
    )
    assert doc.status == "pending"

    await repo.update_document_status(doc.id, status="completed", chunk_count=42)
    updated = await repo.get_document(doc.id)
    assert updated.status == "completed"
    assert updated.chunk_count == 42


@pytest.mark.asyncio
async def test_trace_run_lifecycle(db_session):
    from backend.db.models.conversation import ConversationORM
    from uuid import uuid4

    conv_id = str(uuid4())
    db_session.add(ConversationORM(id=conv_id, title="Trace test"))
    await db_session.commit()

    repo = TraceRepo(db_session)
    run_id = str(uuid4())
    await repo.create_run(run_id=run_id, conversation_id=conv_id, query="test query")

    node_id = str(uuid4())
    await repo.save_node(
        run_id=run_id,
        node_id=node_id,
        node_name="memory_load",
        status="success",
        duration_ms=12,
    )
    await repo.update_run(run_id=run_id, status="success", total_duration_ms=150)

    run = await repo.get_run(run_id)
    assert run.status == "success"
    assert run.total_duration_ms == 150
    assert len(run.nodes) == 1
    assert run.nodes[0].node_name == "memory_load"


@pytest.mark.asyncio
async def test_update_message_feedback(db_session):
    repo = ConversationRepo(db_session)
    conv_id = str(uuid4())
    db_session.add(ConversationORM(id=conv_id, title="Feedback test"))
    await db_session.commit()

    msg = await repo.save_message(conv_id, role="assistant", content="answer")
    assert msg.feedback is None

    # 点赞
    fetched = await repo.get_message(msg.id)
    await repo.update_message_feedback(fetched, "up")
    fetched = await repo.get_message(msg.id)
    assert fetched.feedback == "up"

    # 点踩
    fetched = await repo.get_message(msg.id)
    await repo.update_message_feedback(fetched, "down")
    fetched = await repo.get_message(msg.id)
    assert fetched.feedback == "down"

    # 取消
    fetched = await repo.get_message(msg.id)
    await repo.update_message_feedback(fetched, None)
    fetched = await repo.get_message(msg.id)
    assert fetched.feedback is None


@pytest.mark.asyncio
async def test_get_message_not_found(db_session):
    repo = ConversationRepo(db_session)
    result = await repo.get_message("nonexistent-id")
    assert result is None
