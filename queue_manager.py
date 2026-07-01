import asyncio

class QueueManager:
    """
    Abstract Queue layer handling tasks for scraper workers.
    Currently using asyncio.Queue for MVP, but structurally designed 
    to be replaced with Redis/BullMQ (aioredis, etc.) without altering workers.
    """
    def __init__(self):
        self.queue = asyncio.Queue()

    async def push_task(self, task: dict):
        """Push a scraping job into the queue."""
        await self.queue.put(task)

    async def get_task(self) -> dict:
        """Fetch a scraping job from the queue. Blocks if empty."""
        task = await self.queue.get()
        return task
        
    def task_done(self):
        """Mark task as complete."""
        self.queue.task_done()

# Singleton instance to be exported and used across the app
global_queue = QueueManager()
