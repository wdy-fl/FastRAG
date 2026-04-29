import pytest
from unittest.mock import AsyncMock, MagicMock
from fastrag.core.rag.tracer import RagTracer


@pytest.mark.asyncio
async def test_trace_node_calls_fn_and_saves_node():
    mock_repo = AsyncMock()
    tracer = RagTracer(repo=mock_repo)

    run_id = await tracer.start_run(conversation_id="c1", query="test?")
    assert run_id is not None

    async def my_fn(x: int) -> int:
        return x + 1

    wrapped = tracer.trace_node("test_node")(my_fn)
    result = await wrapped(5)

    assert result == 6
    mock_repo.save_node.assert_awaited_once()
    call_kwargs = mock_repo.save_node.call_args.kwargs
    assert call_kwargs["node_name"] == "test_node"
    assert call_kwargs["status"] == "success"


@pytest.mark.asyncio
async def test_trace_node_records_failure():
    mock_repo = AsyncMock()
    tracer = RagTracer(repo=mock_repo)
    await tracer.start_run(conversation_id="c1", query="q")

    async def failing_fn() -> None:
        raise ValueError("oops")

    wrapped = tracer.trace_node("fail_node")(failing_fn)
    with pytest.raises(ValueError, match="oops"):
        await wrapped()

    call_kwargs = mock_repo.save_node.call_args.kwargs
    assert call_kwargs["status"] == "failed"


@pytest.mark.asyncio
async def test_no_run_id_skips_tracing():
    mock_repo = AsyncMock()
    tracer = RagTracer(repo=mock_repo)
    # Don't start a run

    async def my_fn() -> str:
        return "ok"

    wrapped = tracer.trace_node("node")(my_fn)
    result = await wrapped()
    assert result == "ok"
    mock_repo.save_node.assert_not_awaited()
