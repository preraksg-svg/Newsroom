import asyncio
import sys
import os

sys.path.append(os.getcwd())

from scraper_manager import worker_loop
from queue_manager import global_queue

async def test():
    print("Pushing test task...")
    await global_queue.push_task({
        "url": "https://twitter.com/TataMotors",
        "type": "twitter",
        "source_id": "tata_motors"
    })
    print("Running worker...")
    # Run a timeout task to cancel the loop after 40 seconds
    try:
        await asyncio.wait_for(worker_loop(99), timeout=40.0)
    except asyncio.TimeoutError:
        print("Worker loop timed out as expected.")
    except Exception as e:
        print(f"Worker loop error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
