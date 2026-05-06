from backend.db.models.knowledge import KnowledgeDocQuestionORM


def test_knowledge_doc_question_orm_has_required_fields():
    q = KnowledgeDocQuestionORM(
        id="q-1",
        document_id="doc-1",
        knowledge_base_id="kb-1",
        question="What is the refund policy?",
        embedding=[0.1] * 1024,
    )
    assert q.id == "q-1"
    assert q.document_id == "doc-1"
    assert q.knowledge_base_id == "kb-1"
    assert q.question == "What is the refund policy?"
    assert q.embedding == [0.1] * 1024
