import pytest
import asyncio
from app.worker.task_state import DeliveryState, task_state


@pytest.mark.asyncio
async def test_task_state_lifecycle():
    state = DeliveryState()
    assert state.running is False
    assert state.current_job is None
    assert state.delivered_count == 0
    assert state.filtered_count == 0

    state.start("boss")
    assert state.running is True
    assert state.current_platform == "boss"
    assert state.current_job is None
    assert state.should_stop() is False

    state.delivered_count = 5
    state.filtered_count = 3
    state.current_job = "Java开发"

    state.stop()
    assert state.running is False
    assert state.should_stop() is True

    # restart resets counters
    state.start("boss")
    assert state.delivered_count == 0
    assert state.filtered_count == 0
    assert state.current_job is None


def test_task_state_singleton():
    from app.worker.task_state import task_state as ts2
    assert task_state is ts2
    assert isinstance(task_state, DeliveryState)
