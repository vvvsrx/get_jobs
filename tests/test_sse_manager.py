import pytest
import asyncio
from app.worker.sse_manager import SSEManager


@pytest.mark.asyncio
async def test_sse_publish_and_receive():
    manager = SSEManager()
    received = []

    async def consumer():
        async for msg in manager.subscribe():
            received.append(msg)
            if len(received) >= 1:
                break

    task = asyncio.create_task(consumer())
    await asyncio.sleep(0.05)
    manager.publish({"type": "test", "message": "hello"})
    await asyncio.wait_for(task, timeout=1.0)

    assert len(received) == 1
    assert '"type": "test"' in received[0]


@pytest.mark.asyncio
async def test_sse_multiple_subscribers():
    manager = SSEManager()
    received1 = []
    received2 = []

    async def consumer1():
        async for msg in manager.subscribe():
            received1.append(msg)
            if len(received1) >= 1:
                break

    async def consumer2():
        async for msg in manager.subscribe():
            received2.append(msg)
            if len(received2) >= 1:
                break

    t1 = asyncio.create_task(consumer1())
    t2 = asyncio.create_task(consumer2())
    await asyncio.sleep(0.05)
    manager.publish({"type": "broadcast", "message": "all"})
    await asyncio.wait_for(t1, timeout=1.0)
    await asyncio.wait_for(t2, timeout=1.0)

    assert len(received1) == 1
    assert len(received2) == 1


@pytest.mark.asyncio
async def test_sse_queue_full_cleanup():
    manager = SSEManager()
    # subscribe but don't consume
    gen = manager.subscribe()
    # advance the generator just enough to create the queue and append it
    task = asyncio.create_task(gen.__anext__())
    await asyncio.sleep(0)  # let the generator reach queue.get()

    # fill the queue to maxsize (100) without consuming
    for i in range(150):
        manager.publish({"index": i})

    # the full queue should have been removed
    assert len(manager._queues) == 0

    # clean up the hanging generator task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
