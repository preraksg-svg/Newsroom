import asyncio
import time
import logging
import random
import traceback
import sys
import os
import json
# Ensure parent directory is in sys.path
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import hashlib
from backend.db.queries import get_db, log_source_fetch
from scraper_manager import global_queue

# Setup logging
logger = logging.getLogger("ingestion_daemon")

# Circuit breaker config
MAX_CONSECUTIVE_FAILURES = 3
QUARANTINE_DURATION = 1800  # 30 minutes

# In-memory circuit breaker status mapping
# Format: { source_id: { "state": "CLOSED"/"OPEN"/"HALF-OPEN", "failures": int, "quarantined_until": float } }
circuit_breakers = {}

def get_redis_client():
    """Dynamically try to import and connect to local Redis. Fallback to mock if down."""
    # Force MockRedis to prevent blocking socket connect hangs
    class MockRedis:
        def __init__(self):
            self.store = {}
        def set(self, key, value, ex=None):
            self.store[key] = value
            return True
        def get(self, key):
            return self.store.get(key)
    return MockRedis()

# Global Redis instance / mock
redis_client = get_redis_client()

def record_heartbeat():
    """Record worker active pulse in Redis with 120-second expiration."""
    try:
        redis_client.set("health:layer1:heartbeat", "OK", ex=120)
        logger.debug("Redis heartbeat pulse updated successfully.")
    except Exception as e:
        logger.warning(f"Failed to record Redis heartbeat: {e}")

def get_active_registry_sources():
    """Query target sources strictly from the source_scores table."""
    try:
        with get_db() as conn:
            cur = conn.cursor()
            # Fetch only active sources in source_scores registry with country = 'IN'
            cur.execute("""
                SELECT source_id, domain, type, access_method, failure_count 
                FROM source_scores 
                WHERE activity_status = 'active' AND COALESCE(country, 'IN') = 'IN'
            """)
            return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"Error querying source_scores registry: {e}")
        return []

def save_circuit_breaker_states():
    """Persist current circuit breaker states to Redis and a local file for shared access."""
    try:
        redis_client.set("health:layer1:circuit_breakers", json.dumps(circuit_breakers))
    except Exception as e:
        logger.debug(f"Could not save circuit breakers to Redis: {e}")
        
    try:
        scratch_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../scratch"))
        os.makedirs(scratch_dir, exist_ok=True)
        with open(os.path.join(scratch_dir, "circuit_breakers.json"), "w") as f:
            json.dump(circuit_breakers, f)
    except Exception as e:
        logger.warning(f"Could not save circuit breakers to local file: {e}")

def evaluate_circuit_breaker(source_id):
    """Evaluate and update the circuit breaker state for a source."""
    now = time.time()
    cb = circuit_breakers.setdefault(source_id, {"state": "CLOSED", "failures": 0, "quarantined_until": 0.0})
    
    if cb["state"] == "OPEN":
        if now >= cb["quarantined_until"]:
            cb["state"] = "HALF-OPEN"
            logger.info(f"[CIRCUIT-BREAKER] Source {source_id} entered HALF-OPEN state (quarantine expired).")
            save_circuit_breaker_states()
            return "HALF-OPEN"
        return "OPEN"
    return cb["state"]

def record_source_outcome(source_id, success):
    """Record scrape outcome to update circuit breaker state and db failure count."""
    cb = circuit_breakers.setdefault(source_id, {"state": "CLOSED", "failures": 0, "quarantined_until": 0.0})
    state_changed = False
    
    with get_db() as conn:
        cur = conn.cursor()
        
        if success:
            if cb["failures"] > 0 or cb["state"] != "CLOSED":
                state_changed = True
            cb["failures"] = 0
            if cb["state"] == "HALF-OPEN":
                cb["state"] = "CLOSED"
                logger.info(f"[CIRCUIT-BREAKER] Source {source_id} successfully restored to CLOSED state.")
            
            # Reset database failures
            cur.execute("UPDATE source_scores SET failure_count = 0, fetch_status = 'success' WHERE source_id = ?", (source_id,))
            conn.commit()
        else:
            cb["failures"] += 1
            state_changed = True
            logger.warning(f"[CIRCUIT-BREAKER] Source {source_id} failure count: {cb['failures']}/{MAX_CONSECUTIVE_FAILURES}")
            
            cur.execute("UPDATE source_scores SET failure_count = failure_count + 1, fetch_status = 'failed' WHERE source_id = ?", (source_id,))
            conn.commit()
            
            if cb["failures"] >= MAX_CONSECUTIVE_FAILURES:
                cb["state"] = "OPEN"
                cb["quarantined_until"] = time.time() + QUARANTINE_DURATION
                logger.error(f"[CIRCUIT-BREAKER] Tripped circuit breaker for source {source_id}! Quarantined for 30 minutes.")
                
    if state_changed:
        save_circuit_breaker_states()

async def process_task_safe(worker_id, src, traceparent):
    """Process a single scraping task with trace preservation and circuit breaker wrapping."""
    source_id = src["source_id"]
    domain = src["domain"]
    # Map type correctly from domain if it's an abstract category
    stype = src["type"].lower()
    domain_lower = domain.lower()
    
    if "twitter.com" in domain_lower:
        stype = "twitter"
    elif "youtube.com" in domain_lower or "youtu.be" in domain_lower:
        stype = "youtube"
    elif "reddit.com" in domain_lower:
        stype = "reddit"
    elif "instagram.com" in domain_lower:
        stype = "instagram"
    elif "facebook.com" in domain_lower:
        stype = "facebook"
    elif stype in ["news_api", "newsapi"]:
        stype = "newsapi"
    elif stype == "newsdata":
        stype = "newsdata"
    elif stype == "gnews":
        stype = "gnews"
    else:
        stype = "website"
    # Import scraping modules dynamically
    from workers.twitter_worker import scrape_twitter
    from workers.youtube_worker import scrape_youtube
    from workers.reddit_worker import scrape_reddit
    from workers.instagram_worker import scrape_instagram
    from workers.facebook_worker import scrape_facebook
    from workers.website_worker import scrape_website
    from workers.newsapi_worker import scrape_newsapi
    from workers.newsdata_worker import scrape_newsdata
    from workers.gnews_worker import scrape_gnews
    import hashlib
    
    logger.info(f"[Worker {worker_id}][Trace: {traceparent}] Polling: {stype} -> {domain}")
    
    results = []
    success = False
    
    try:
        # Perform scraper call based on type with timeout
        if stype == "twitter":
            results = await asyncio.wait_for(scrape_twitter(domain), timeout=45.0)
        elif stype == "youtube":
            results = await asyncio.wait_for(scrape_youtube(domain), timeout=45.0)
        elif stype == "reddit":
            results = await asyncio.wait_for(scrape_reddit(domain), timeout=45.0)
        elif stype == "instagram":
            results = await asyncio.wait_for(scrape_instagram(domain), timeout=45.0)
        elif stype == "facebook":
            results = await asyncio.wait_for(scrape_facebook(domain), timeout=45.0)
        elif stype == "newsapi":
            results = await asyncio.wait_for(scrape_newsapi(domain), timeout=45.0)
        elif stype == "newsdata":
            results = await asyncio.wait_for(scrape_newsdata(domain), timeout=45.0)
        elif stype == "gnews":
            results = await asyncio.wait_for(scrape_gnews(domain), timeout=45.0)
        else:
            results = await asyncio.wait_for(scrape_website(domain), timeout=45.0)
            
        success = True
    except Exception as e:
        logger.error(f"[Worker {worker_id}][Trace: {traceparent}] Scraper error for {source_id}: {e}")
        traceback.print_exc()
        
    # Process scraped results to raw signals table
    saved_count = 0
    if results:
        for r in results:
            # Skip results older than 7 days
            try:
                ts_val = int(r.get('timestamp', 0))
                if ts_val < time.time() - 604800:
                    continue
            except (ValueError, TypeError):
                pass

            from backend.llm import is_india_relevant
            if not is_india_relevant(r.get('title', ''), r.get('content_raw', '')):
                continue

            url_hash = hashlib.md5(r['url'].encode()).hexdigest()
            rid = f"raw_{url_hash}"
            
            is_duplicate = False
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT id FROM scraped_raw WHERE id=?", (rid,))
                if cur.fetchone():
                    is_duplicate = True
                    
            if not is_duplicate:
                engagement_json = json.dumps(r.get("engagement", {}))
                with get_db() as conn:
                    cur = conn.cursor()
                    cur.execute('''
                        INSERT OR IGNORE INTO scraped_raw 
                        (id, title, content, url, source_id, source_type, author, timestamp, engagement_data, clustered)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    ''', (rid, r['title'], r['content_raw'], r['url'],
                          source_id, r['source_type'], r.get("author", "Unknown"),
                          r['timestamp'], engagement_json))
                    conn.commit()
                saved_count += 1
                
    # Synchronize outcomes with metrics database and circuit breaker state
    record_source_outcome(source_id, success)
    
    if saved_count > 0:
        log_source_fetch(source_id, 'success', saved_count)
        logger.info(f"[Worker {worker_id}][Trace: {traceparent}] Successfully saved {saved_count} new raw signals.")
    else:
        log_source_fetch(source_id, 'empty', 0)

async def ingestion_loop():
    """Resilient, self-healing Infinite Ingestion Daemon."""
    logger.info("Initializing Layer 1: Resilient Infinite Ingestion Daemon...")
    
    attempt = 0
    last_heartbeat_time = 0.0
    
    while True:
        try:
            # 1. Update diagnostic heartbeat every 60s
            now = time.time()
            if now - last_heartbeat_time >= 60.0:
                record_heartbeat()
                last_heartbeat_time = now
                
            # Generate request W3C trace identifiers
            trace_id = hashlib.md5(f"trace_{now}".encode()).hexdigest()
            parent_id = hashlib.md5(f"parent_{now}".encode()).hexdigest()[:16]
            traceparent = f"00-{trace_id}-{parent_id}-01"
            
            # 2. Fetch authorized targets registry dynamically
            active_sources = get_active_registry_sources()
            
            if not active_sources:
                logger.warning("No active sources configured in source_scores registry database. Sleeping...")
                await asyncio.sleep(30)
                continue
                
            # Filter targets through source-level circuit breakers
            eligible_sources = []
            for src in active_sources:
                state = evaluate_circuit_breaker(src["source_id"])
                if state != "OPEN":
                    eligible_sources.append(src)
                else:
                    logger.debug(f"Source {src['source_id']} is quarantined. Skipping.")
            
            if not eligible_sources:
                logger.warning("All registered sources are currently quarantined by circuit breakers. Cooling...")
                await asyncio.sleep(30)
                continue
                
            logger.info(f"[DAEMON-RUN] Dispatched cycle starting with {len(eligible_sources)} active sources.")
            
            # 3. Dynamic Parallel Processing via Workers
            semaphore = asyncio.Semaphore(5)
            
            async def worker_wrapper(worker_idx, src_obj):
                async with semaphore:
                    await process_task_safe(worker_idx, src_obj, traceparent)
            
            tasks = [worker_wrapper(idx % 5, src) for idx, src in enumerate(eligible_sources)]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Reset loops retry parameters on successful execution cycle
            attempt = 0
            
            # Sleep for 30 minutes (1800 seconds) before the next cycle
            jitter = random.uniform(-30.0, 30.0)
            sleep_sec = 1800.0 + jitter
            logger.info(f"[CYCLE-END] Completed ingestion pass. Sleeping for {sleep_sec:.2f}s (30 min) before next cycle...")
            await asyncio.sleep(sleep_sec)
            
        except Exception as global_err:
            # Highest level try-except wrapper catches all database drops, network failures, etc.
            attempt += 1
            tb = traceback.format_exc()
            logger.critical(f"[DAEMON-CRASH] Ingestion daemon execution crashed: {global_err}")
            logger.critical(tb)
            
            # Log failure to task registry if possible
            try:
                with get_db() as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO tasks (id, task_type, status, error, created_at) 
                        VALUES (?, 'daemon_crash', 'failed', ?, CURRENT_TIMESTAMP)
                    """, (f"crash_{int(time.time())}", f"Daemon loop crashed: {str(global_err)}\n{tb}"))
                    conn.commit()
            except Exception as db_log_err:
                logger.error(f"Failed to record daemon loop crash to database tasks: {db_log_err}")
                
            # Calculate backoff value incorporating randomized jitter
            t_base = 5.0
            t_max = 300.0
            jitter = random.uniform(-5.0, 5.0)
            backoff_delay = min(t_max, t_base * (2 ** attempt)) + jitter
            backoff_delay = max(5.0, backoff_delay)
            
            logger.info(f"[SELF-HEALING] Retrying infinite execution cycle in {backoff_delay:.2f} seconds...")
            await asyncio.sleep(backoff_delay)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='[INGESTION-DAEMON] %(asctime)s - %(levelname)s - %(message)s')
    asyncio.run(ingestion_loop())
