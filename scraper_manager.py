"""
ZAPWAY Multi-Channel Scraper Manager (Self-Learning)
=====================================================
6 parallel workers with dynamic poll intervals driven by the learning engine.
High-score sources get polled MORE, low-score sources get throttled.
"""
import asyncio
import json
import os
import time
import hashlib
from queue_manager import global_queue
from workers.twitter_worker import scrape_twitter
from workers.youtube_worker import scrape_youtube
from workers.website_worker import scrape_website
from workers.reddit_worker import scrape_reddit
from workers.instagram_worker import scrape_instagram
from workers.facebook_worker import scrape_facebook
from workers.newsapi_worker import scrape_newsapi
from workers.newsdata_worker import scrape_newsdata
from workers.gnews_worker import scrape_gnews
from backend.db.queries import get_db, log_source_fetch
from learning_engine import (
    record_worker_ingestion, should_skip_content,
    get_poll_multiplier, record_trend_signal, should_use_llm
)


async def worker_loop(worker_id: int):
    """Parallel worker with learning-aware skip logic."""
    print(f"[Worker {worker_id}] Online (Self-Learning Mode)")
    while True:
        task = await global_queue.get_task()
        url = task.get("url")
        stype = task.get("type", "").lower()
        source_id = task.get("source_id", url)

        print(f"[Worker {worker_id}] Engaging: {stype} -> {url}")
        
        try:
            results = []
            # RETRY MECHANISM (BUG 22)
            for attempt in range(3):
                try:
                    if stype == "twitter":
                        results = await scrape_twitter(url)
                    elif stype == "youtube":
                        results = await scrape_youtube(url)
                    elif stype == "reddit":
                        results = await scrape_reddit(url)
                    elif stype == "instagram":
                        results = await scrape_instagram(url)
                    elif stype == "facebook":
                        results = await scrape_facebook(url)
                    elif stype == "newsapi":
                        results = await scrape_newsapi(url)
                    elif stype == "newsdata":
                        results = await scrape_newsdata(url)
                    elif stype == "gnews":
                        results = await scrape_gnews(url)
                    else:
                        results = await scrape_website(url)
                    break
                except Exception as e:
                    if attempt < 2:
                        print(f"[Worker {worker_id}][RETRY {attempt+1}/3] Error for {url}: {e}")
                        await asyncio.sleep(2)
                    else:
                        raise e

            # MANDATORY LOG
            print("Fetched items:", len(results) if results else 0)

            if results:
                from discovery_engine import extract_candidate_sources
                saved_count = 0
                skipped_count = 0

                for r in results:
                    # ── Learning: Skip low-value content ──────
                    if should_skip_content(source_id, r.get("title", "")):
                        skipped_count += 1
                        record_worker_ingestion(source_id, was_selected=False)
                        continue
                        
                    # ── Freshness: Skip news older than 24 hours ──────
                    import time
                    if int(time.time()) - r.get("timestamp", int(time.time())) > 86400:
                        skipped_count += 1
                        continue

                    # Pre-Cluster Deduplication
                    url_hash = hashlib.md5(r['url'].encode()).hexdigest()
                    rid = f"raw_{url_hash}"

                    is_duplicate = False
                    with get_db() as conn:
                        cur = conn.cursor()
                        cur.execute("SELECT id FROM scraped_raw WHERE id=?", (rid,))
                        if cur.fetchone():
                            is_duplicate = True
                            
                    if is_duplicate:
                        continue

                    engagement_json = json.dumps(r.get("engagement", {}))
                    
                    with get_db() as conn:
                        cur = conn.cursor()
                        cur.execute('''
                            INSERT OR IGNORE INTO scraped_raw 
                            (id, title, content, url, source_id, source_type, author, timestamp, engagement_data)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (rid, r['title'], r['content_raw'], r['url'],
                              source_id, r['source_type'], r.get("author", "Unknown"),
                              r['timestamp'], engagement_json))
                        conn.commit()

                    # ── Learning: Record successful ingestion ──
                    record_worker_ingestion(source_id, was_selected=True)

                    # ── Trend Detection: Cross-source signal ──
                    record_trend_signal(r.get("title", ""), source_id)

                    saved_count += 1
                
                # Continuous source discovery (moved outside transaction to avoid nested DB locks)
                for r in results:
                    extract_candidate_sources(r['content_raw'])
                
                log_source_fetch(source_id, 'success', saved_count)
                print(f"[Worker {worker_id}][SUCCESS] Saved {saved_count} items | Skipped {skipped_count} from {url}", flush=True)
                if saved_count > 0:
                    print(f"[Worker {worker_id}] Sample result: {results[0]['title'][:50]}...", flush=True)
                else:
                    print(f"[Worker {worker_id}][EMPTY] No new content found for {url}", flush=True)
            else:
                log_source_fetch(source_id, 'empty', 0)
                print(f"[Worker {worker_id}][EMPTY] No results returned for {url}", flush=True)
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            log_source_fetch(source_id, 'failed', 0, str(e))
            print(f"[Worker {worker_id}][FAILURE] Error scraping {url}: {e}", flush=True)

        global_queue.task_done()


async def dispatcher_loop():
    """
    Reads from DB dynamically, adjusting poll intervals per source
    based on learned worker_memory scores.
    """
    print("[DISPATCHER] Active (Learning-Adaptive Mode)")

    BASE_INTERVALS = {
        "twitter":   21600,
        "youtube":   21600,
        "website":   21600,
        "reddit":    21600,
        "instagram": 21600,
        "facebook":  21600
    }

    last_run = {}

    while True:
        try:
            with get_db() as conn:
                cur = conn.cursor()
                # Only poll active sources
                cur.execute("SELECT source_id, domain, type FROM sources WHERE activity_status = 'active'")
                db_sources = cur.fetchall()

            now = time.time()
            dispatched = 0
            
            if not db_sources:
                print("[DISPATCHER] Warning: No active sources found in database.")

            for src in db_sources:
                source_id = src["source_id"]
                domain = src["domain"]
                
                # Determine channel type based on URL / domain
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
                else:
                    stype = "website"

                base_interval = BASE_INTERVALS.get(stype, 300)

                # ── Learning: Dynamic interval from worker_memory ──
                poll_mult = get_poll_multiplier(source_id)
                actual_interval = base_interval * poll_mult

                if now - last_run.get(domain, 0) > actual_interval:
                    print(f"[DISPATCHER] Queueing: {stype} -> {domain}")
                    await global_queue.push_task({
                        "url": domain,
                        "type": stype,
                        "source_id": source_id
                    })
                    last_run[domain] = now
                    dispatched += 1

            if dispatched > 0:
                print(f"[DISPATCHER] Dispatched {dispatched} tasks this cycle")
            else:
                print(f"[DISPATCHER] No tasks to dispatch (already polled recently or none due)")

        except Exception as e:
            print(f"[DISPATCHER] Error: {e}")

        await asyncio.sleep(15)


async def start_scraping_engine():
    """Boots workers and learning-adaptive dispatcher."""
    WORKER_COUNT = 6
    tasks = []
    for i in range(WORKER_COUNT):
        tasks.append(asyncio.create_task(worker_loop(i)))
    tasks.append(asyncio.create_task(dispatcher_loop()))
    print("[ENGINE] Multi-Channel Self-Learning Scraper Engine fully active.")
    await asyncio.gather(*tasks, return_exceptions=True)
