import asyncio
import json
from typing import AsyncGenerator


class SSEManager:
    def __init__(self):
        self._queues: list[asyncio.Queue] = []

    async def subscribe(self) -> AsyncGenerator[str, None]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._queues.append(queue)
        try:
            while True:
                message = await queue.get()
                if message is None:
                    break
                yield f"data: {json.dumps(message)}\n\n"
        finally:
            if queue in self._queues:
                self._queues.remove(queue)

    def publish(self, message: dict):
        dead_queues = []
        for queue in self._queues:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                dead_queues.append(queue)
        for q in dead_queues:
            try:
                self._queues.remove(q)
            except ValueError:
                pass

    async def publish_async(self, message: dict):
        self.publish(message)


# 全局 SSE 管理器实例
sse_manager = SSEManager()
