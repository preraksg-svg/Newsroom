import asyncio
import logging
import json
import time
import random
import traceback
import sys
import os
import hashlib

# Ensure parent directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db.queries import get_next_pending_task, update_task_status
from backend.services.news_service import NewsService

# Setup logging
logging.basicConfig(level=logging.INFO, format='[MEDIA-WORKER] %(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("media_worker")

def get_redis_client():
    """Dynamically try to import and connect to local Redis. Fallback to mock if down."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, socket_timeout=2)
        return r
    except Exception:
        class MockRedis:
            def __init__(self):
                self.store = {}
            def set(self, key, value, ex=None):
                self.store[key] = value
                return True
            def get(self, key):
                return self.store.get(key)
        return MockRedis()

redis_client = get_redis_client()

def record_heartbeat():
    """Record media worker active pulse in Redis with 120-second expiration."""
    try:
        redis_client.set("health:layer3:heartbeat", "OK", ex=120)
        logger.debug("Redis heartbeat pulse updated successfully.")
    except Exception as e:
        logger.warning(f"Failed to record Redis heartbeat: {e}")

async def media_worker_loop():
    """Layer 3: Media Worker. Handles heavy on-demand tasks (Images, Audio, Social)."""
    logger.info("Initializing Layer 3: Media Worker (On-Demand)...")
    
    attempt = 0
    last_heartbeat_time = 0.0
    
    while True:
        try:
            # 1. Update diagnostic heartbeat every 60s
            now = time.time()
            if now - last_heartbeat_time >= 60.0:
                record_heartbeat()
                last_heartbeat_time = now
                
            # 2. Polling the tasks table for pending actions
            task = get_next_pending_task()
            
            if not task:
                attempt = 0  # Reset backoff if we successfully poll and find nothing
                await asyncio.sleep(2)
                continue
                
            # Generate request W3C trace identifiers for this task processing
            trace_id = hashlib.md5(f"trace_{task.id}_{now}".encode()).hexdigest()
            parent_id = hashlib.md5(f"parent_{task.id}_{now}".encode()).hexdigest()[:16]
            traceparent = f"00-{trace_id}-{parent_id}-01"
            
            logger.info(f"[Trace: {traceparent}] Picked task {task.id} ({task.task_type}) for article {task.article_id}")
            update_task_status(task.id, "processing")
            
            try:
                task_type = task.task_type
                article_id = task.article_id
                params = json.loads(task.params) if task.params else {}
                
                # Map task types to NewsService actions
                if task_type == "audio":
                    result = await NewsService.handle_action("generate_audio", article_id, params, internal=True)
                elif task_type == "image":
                    result = await NewsService.handle_action("generate_thumbnails", article_id, params, internal=True)
                elif task_type == "social":
                    result = await NewsService.handle_action("generate_social", article_id, params, internal=True)
                else:
                    raise ValueError(f"Unknown task type: {task_type}")
                
                if result and "error" not in result:
                    update_task_status(task.id, "completed")
                    logger.info(f"[Trace: {traceparent}] Completed task {task.id}")
                else:
                    error_msg = result.get("error", "Unknown error") if result else "No result returned"
                    update_task_status(task.id, "failed", error_msg)
                    logger.error(f"[Trace: {traceparent}] Failed task {task.id}: {error_msg}")
                    
            except Exception as e:
                tb = traceback.format_exc()
                logger.error(f"[Trace: {traceparent}] Media processing error for task {task.id}: {e}")
                logger.error(tb)
                update_task_status(task.id, "failed", f"{str(e)}\n{tb}")
                
            attempt = 0  # Reset backoff on successful execution loop pass
            await asyncio.sleep(1)
            
        except Exception as global_err:
            attempt += 1
            tb = traceback.format_exc()
            logger.critical(f"[MEDIA-DAEMON-CRASH] Media worker loop crashed: {global_err}")
            logger.critical(tb)
            
            # Calculate backoff delay with randomized jitter
            t_base = 2.0
            t_max = 60.0
            jitter = random.uniform(-1.0, 1.0)
            backoff_delay = min(t_max, t_base * (2 ** attempt)) + jitter
            backoff_delay = max(2.0, backoff_delay)
            
            logger.info(f"[SELF-HEALING] Retrying infinite media loop in {backoff_delay:.2f} seconds...")
            await asyncio.sleep(backoff_delay)

if __name__ == "__main__":
    asyncio.run(media_worker_loop())
