import asyncio
import logging
import time
from backend.db.queries import get_db

logging.basicConfig(level=logging.INFO, format='[CLEANUP-WORKER] %(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("cleanup_worker")

async def cleanup_loop():
    """Layer 4: Self-Correction Cleanup Worker. Archives stale drafts and signals (>48 hours old) every 30 minutes."""
    logger.info("Initializing Layer 4: Self-Correction Cleanup Worker...")
    while True:
        try:
            logger.info("Running stale signals & drafts cleanup query...")
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute('''
                    UPDATE stories 
                    SET status = 'Archived' 
                    WHERE (status = 'Signal' OR status = 'Draft') 
                      AND created_at < datetime('now', '-48 hours')
                ''')
                archived_count = cur.rowcount
                conn.commit()
            logger.info(f"Cleanup finished. Stale stories archived: {archived_count}")
        except Exception as e:
            logger.error(f"Cleanup loop error: {e}")
            
        # Run every 30 minutes (1800 seconds)
        await asyncio.sleep(1800)

if __name__ == "__main__":
    asyncio.run(cleanup_loop())
