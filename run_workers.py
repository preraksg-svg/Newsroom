import asyncio
import logging
import os
from backend.db.queries import init_db
from learning_engine import initialize_learning_engine
from training_engine import initialize_training_engine
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
    
    # AUTO-RESET: clear circuit breakers on every startup so stale quarantine state
    # from a previous crash/deploy never blocks scraping indefinitely.
    try:
        import json
        from backend.db.queries import get_db
        _cb_path = os.path.join(os.path.dirname(__file__), 'scratch', 'circuit_breakers.json')
        with get_db() as _conn:
            _conn.execute("UPDATE source_scores SET failure_count=0 WHERE activity_status='active'")
            _conn.commit()
        if os.path.exists(_cb_path):
            with open(_cb_path, 'w') as _f:
                json.dump({}, _f)
        print("[INIT] Circuit breakers reset. All active sources unblocked.")
    except Exception as _ce:
        print(f"[INIT] Warning: circuit breaker reset failed: {_ce}")
    
    # Upsert/Sync sources on start to update domains and sync registry changes
    try:
        print("[WORKERS] Syncing/Upserting reliable sources registry...")
        from seed_reliable_sources import seed
        seed()
    except Exception as se:
        print(f"[WORKERS] Syncing sources failed or skipped: {se}")

    initialize_learning_engine()
    initialize_training_engine()
    
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
        # Let other workers complete their initial cycle before running diagnostics (1 hour delay)
        await asyncio.sleep(3600)
        while True:
            try:
                logger.info("[DIAGNOSTICS] Triggering sources verification loop...")
                await verify_sources_main()
            except Exception as e:
                logger.error(f"[DIAGNOSTICS] Error in verify_sources loop: {e}")
            await asyncio.sleep(1800) # Run every 30 minutes
            
    diagnostics_task = asyncio.create_task(diagnostics_loop())
    
    tasks = [ingestion_task, ai_task, media_task, cleanup_task, diagnostics_task]

    # Periodic DB snapshot to GitHub (free persistence). No-op without GITHUB_TOKEN.
    try:
        from db_persistence import backup_loop, enabled as _persist_enabled
        if _persist_enabled():
            print("[INIT] Initializing DB persistence backup task...")
            tasks.append(asyncio.create_task(backup_loop()))
    except Exception as _be:
        print(f"[INIT] DB backup task skipped: {_be}")

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
