import asyncio
import logging
from backend.db.queries import init_db
from bandit_engine import initialize_bandit_engine
from learning_engine import initialize_learning_engine
from training_engine import initialize_training_engine
from ab_testing import initialize_ab_testing
from thumbnail_ab_testing import initialize_thumbnail_ab_testing
from workers.ingestion_worker import ingestion_loop
from workers.ai_worker import ai_processing_loop
from workers.media_worker import media_worker_loop
from workers.cleanup_worker import cleanup_loop

# Setup logging
logging.basicConfig(level=logging.INFO, format='[SYSTEM] %(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    print("[INIT] Starting ZAPWAY Production-Grade Worker Engine...")

    init_db()
    
    # Upsert/Sync sources on start to update domains and sync registry changes
    try:
        from backend.db.queries import get_db
        with get_db() as conn:
            print("[WORKERS] Syncing/Upserting reliable sources registry...")
            from seed_reliable_sources import seed
            seed()
    except Exception as se:
        print(f"[WORKERS] Syncing sources failed or skipped: {se}")

    initialize_learning_engine()
    initialize_training_engine()
    initialize_bandit_engine()
    initialize_ab_testing()
    initialize_thumbnail_ab_testing()
    
    print("[INIT] Initializing Ingestion task...")
    ingestion_task = asyncio.create_task(ingestion_loop())
    
    print("[INIT] Initializing AI task...")
    ai_task = asyncio.create_task(ai_processing_loop())
    
    print("[INIT] Initializing Media task...")
    media_task = asyncio.create_task(media_worker_loop())
    
    print("[INIT] Initializing Cleanup task...")
    cleanup_task = asyncio.create_task(cleanup_loop())
    
    print("[INIT] Initializing Diagnostics task...")
    async def diagnostics_loop():
        from scripts.verify_sources import main as verify_sources_main
        while True:
            try:
                logger.info("[DIAGNOSTICS] Triggering sources verification loop...")
                await verify_sources_main()
            except Exception as e:
                logger.error(f"[DIAGNOSTICS] Error in verify_sources loop: {e}")
            await asyncio.sleep(1800) # Run every 30 minutes
            
    diagnostics_task = asyncio.create_task(diagnostics_loop())
    
    tasks = [ingestion_task, ai_task, media_task, cleanup_task, diagnostics_task]
    
    print("[INIT] All tasks created. Entering gather loop...")
    
    try:
        # Keep the main process alive
        await asyncio.gather(*tasks)
    except Exception as e:
        print(f"[CRITICAL] System-level worker failure: {e}")
    finally:
        print("[SHUTDOWN] ZAPWAY Worker Engine shutting down.")

if __name__ == "__main__":
    asyncio.run(main())
