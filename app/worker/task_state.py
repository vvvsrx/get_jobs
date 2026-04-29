import asyncio


class DeliveryState:
    def __init__(self):
        self.running: bool = False
        self.cancel_event: asyncio.Event = asyncio.Event()
        self.current_platform: str | None = None
        self.current_job: str | None = None
        self.delivered_count: int = 0
        self.filtered_count: int = 0

    def start(self, platform: str):
        self.running = True
        self.cancel_event.clear()
        self.current_platform = platform
        self.current_job = None
        self.delivered_count = 0
        self.filtered_count = 0

    def stop(self):
        self.running = False
        self.cancel_event.set()

    def should_stop(self) -> bool:
        return not self.running or self.cancel_event.is_set()


task_state = DeliveryState()
