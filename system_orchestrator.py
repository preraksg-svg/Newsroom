import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import asyncio
import time
import json
import uuid
import hashlib
from datetime import datetime
from backend.db.queries import get_db, create_draft, init_db
from backend.llm import rewrite_article, generate_ai_summary
from backend.headline_engine import generate_headline_variations, pick_best_headline
from content_scoring import compute_content_score
from seo_engine import generate_seo_metadata, generate_faq
from keyword_engine import KeywordEngine
from backend.social_engine import generate_viral_bundle, schedule_social_campaign
from growth_engine import init_growth_metrics
from bandit_engine import initialize_bandit_engine, trigger_bandit_sync
from backend.thumbnail_engine import generate_thumbnail_prompts
from thumbnail_ab_testing import initialize_thumbnail_ab_testing, create_thumbnail_test
from learning_engine import initialize_learning_engine
from scraper_manager import dispatcher_loop

class NewsroomOrchestrator:
    def __init__(self):
        import uuid
        self.cycle_id = str(uuid.uuid4())[:8]
        self.trace_id = uuid.uuid4().hex
        self.parent_id = uuid.uuid4().hex[:16]
        self.traceparent = f"00-{self.trace_id}-{self.parent_id}-01"
        print(f"[ORCHESTRATOR] Initializing cycle {self.cycle_id}...")
        print(f"[OBSERVABILITY][W3C-TRACE] traceparent: {self.traceparent}")
        init_db()
        initialize_learning_engine()
        initialize_bandit_engine()
        initialize_thumbnail_ab_testing()

    async def run_full_pipeline(self):
        """Execute the 22-step strict order pipeline."""
        print(f"[PIPELINE] Starting orchestration at {datetime.now()}")
        
        try:
            # 1-4: Ingestion Layer (Async Dispatcher)
            print("[PIPELINE][STEP 1-4] Starting Multi-Channel Ingestion...")
            
            # Import scrapers dynamically
            from workers.website_worker import scrape_website
            from workers.twitter_worker import scrape_twitter
            from workers.youtube_worker import scrape_youtube
            from workers.reddit_worker import scrape_reddit
            from workers.instagram_worker import scrape_instagram
            from workers.facebook_worker import scrape_facebook
            import hashlib
            import random
            
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT source_id, domain, type FROM sources WHERE activity_status = 'active'")
                all_sources = [dict(row) for row in cur.fetchall()]
            
            sources_to_scrape = all_sources
            
            sem = asyncio.Semaphore(5)
            
            async def scrape_source_safe(src):
                source_id = src['source_id']
                domain = src['domain']
                
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
                
                async with sem:
                    results = []
                    try:
                        print(f"[PIPELINE] Fetching {source_id} via {stype}...")
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
                        else:
                            results = await asyncio.wait_for(scrape_website(domain), timeout=45.0)
                    except Exception as scrape_err:
                        print(f"[PIPELINE] Error fetching {source_id}: {scrape_err}")
                        
                    saved_count = 0
                    if results:
                        for r in results:
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
                                
                    from backend.db.queries import log_source_fetch
                    if saved_count > 0:
                        log_source_fetch(source_id, 'success', saved_count)
                    else:
                        log_source_fetch(source_id, 'empty', 0)
                    print(f"[PIPELINE] Source {source_id}: Saved {saved_count} new raw signals.")

            print(f"[PIPELINE] Scraping {len(sources_to_scrape)} sources with concurrency limit 2...")
            sem = asyncio.Semaphore(2)
            async def scrape_sem(s):
                async with sem:
                    return await scrape_source_safe(s)
            await asyncio.gather(*(scrape_sem(s) for s in sources_to_scrape), return_exceptions=True)
            
            # 5-7: Normalization, Dedup, Clustering
            print("[STEP 5-7] Normalizing and Clustering Raw Signals...")
            raw_signals = self.get_latest_raw_signals(limit=5)
            # MANDATORY LOG
            print("Fetched signals for processing:", len(raw_signals) if raw_signals else 0)
            
            if not raw_signals:
                print("[PIPELINE] No new signals found. Returning early without generating fallback news.")
                return {"success": True, "cycle_id": self.cycle_id, "processed": 0}

            # 8-21: Process each cluster
            processed_count = 0
            for signal in raw_signals:
                try:
                    await self.process_signal(signal)
                except Exception as sig_err:
                    print(f"[PIPELINE] Error processing signal {signal['id']}: {sig_err}")
                processed_count += 1
            
            print(f"[PIPELINE] Processed {processed_count} signals.")
            
            # 22: Daily Maintenance
            print("[STEP 22] Executing Maintenance...")
            trigger_bandit_sync()
            
            # VALIDATION LOG
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM stories")
                print("TOTAL STORIES IN DB:", cur.fetchone()[0])

            print(f"[PIPELINE] Cycle {self.cycle_id} completed.")
            return {"success": True, "cycle_id": self.cycle_id}
            
        except Exception as e:
            print(f"[PIPELINE] CRITICAL FAILURE: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def get_latest_raw_signals(self, limit=10):
        """Fetch unclustered signals from scraped_raw for strictly India (IN) sources."""
        current_time = int(time.time())
        # Look back up to 7 days to ensure only recent signals are processed
        cutoff = current_time - 604800
        with get_db() as conn:
            cur = conn.cursor()
            
            # 1) Auto-reject non-Indian signals to avoid processing them (Global EV news rejected)
            cur.execute("""
                UPDATE scraped_raw 
                SET clustered = 1 
                WHERE id IN (
                    SELECT r.id FROM scraped_raw r
                    LEFT JOIN sources s ON r.source_id = s.source_id
                    WHERE r.clustered = 0 AND COALESCE(s.country, 'IN') != 'IN'
                )
            """)
            
            # 2) Fetch only Indian signals
            cur.execute("""
                SELECT r.*, COALESCE(s.country, 'IN') as country 
                FROM scraped_raw r
                LEFT JOIN sources s ON r.source_id = s.source_id
                WHERE r.clustered = 0 AND CAST(r.timestamp AS INTEGER) >= ? 
                AND COALESCE(s.country, 'IN') = 'IN'
                ORDER BY r.timestamp DESC
                LIMIT ?
            """, (cutoff, limit))
            selected_signals = [dict(row) for row in cur.fetchall()]
            
            # Mark selected as clustered
            for sig in selected_signals:
                cur.execute("UPDATE scraped_raw SET clustered = 1 WHERE id = ?", (sig['id'],))
            conn.commit()
            return selected_signals

    async def process_signal(self, signal):
        """Steps 8-21 for a single signal."""
        print(f"[SIGNAL] Processing: {signal['title'][:50]}...")
        
        # Verify raw content is present and is at least 150 words (or 15 words for social media channels)
        raw_content = signal.get('content', '') or ''
        word_count = len(raw_content.split())
        min_words = 15 if signal.get('source_type') in ['twitter', 'reddit', 'instagram', 'facebook', 'youtube', 'Social', 'Video'] else 150
        if not raw_content.strip() or word_count < min_words:
            print(f"[OBSERVABILITY][{self.traceparent}] [GROUNDING_GATE_BLOCK] Signal contains insufficient data ({word_count} words). Aborting.")
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE scraped_raw SET clustered = 2 WHERE id = ?", (signal['id'],))
                conn.commit()
            return

        # 8: Mode Selection (FAST if Priority > 80)
        priority = self.calculate_priority(signal)
        mode = "FAST" if priority > 80 else "NORMAL"
        print(f"[MODE] Selected: {mode} (Priority: {priority})")

        # 8.5: LLM Noise Filtering (Moved from ingestion layer to ensure fast intake)
        from backend.llm import filter_article
        filter_res = await asyncio.to_thread(filter_article, signal.get('title', ''), signal.get('content', ''))
        if not filter_res.get('relevant', True):
             print(f"[FILTER] Signal rejected by AI Gatekeeper: {filter_res.get('reason', 'Irrelevant content')}")
             return

        # 9-11: Content Generation (Article, Summary, Media)
        try:
            # Generate Article via LLM
            content_pkg = await self.generate_article_via_llm(signal, mode)
            
            # 12: Content Scoring (PRE-PUBLISH)
            score_res = await asyncio.to_thread(
                compute_content_score,
                headline=content_pkg['title'],
                content=content_pkg['body'],
                source_url=signal['url'],
                sections=content_pkg['sections']
            )
            
            if score_res['decision'] == "REJECT" and score_res['content_score'] < 50:
                print(f"[SCORING] REJECTED ({score_res['content_score']}). Skipping.")
                return

            # 13: Keyword + SEO Engine
            seo_pkg = await asyncio.to_thread(generate_seo_metadata, content_pkg['title'], content_pkg['body'])
            seo_faq = await asyncio.to_thread(generate_faq, content_pkg['body'], seo_pkg['keywords'])
            
            # 14-15: Variant Generation (Bandit Ready)
            h_variants = await asyncio.to_thread(generate_headline_variations, content_pkg['title'], content_pkg['body'])
            
            # 16-18: Publication & DB Storage
            # Resolve actual source/publisher name from sources database
            publisher_name = signal.get('source_id') or signal.get('source_type', 'Zapway')
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT name FROM sources WHERE source_id = ?", (publisher_name,))
                row = cur.fetchone()
                if row:
                    publisher_name = row['name']
                else:
                    # Clean up identifier format (e.g. tata_motors -> Tata Motors)
                    publisher_name = publisher_name.replace('_', ' ').title()

            res = create_draft(
                url=signal['url'],
                title=content_pkg['title'],
                original_content=signal['content'],
                meta_title=seo_pkg['meta_title'],
                meta_desc=seo_pkg['meta_desc'],
                keywords=seo_pkg['keywords'],
                publisher=publisher_name,
                published_date=str(time.time()),
                scores_dict={
                    "final_score": score_res['content_score'],
                    "sections": content_pkg['sections'],
                    "ai_summary": content_pkg['summary']
                },
                seo_strategy=json.dumps(seo_pkg.get('strategy', {})),
                seo_faq=json.dumps(seo_faq)
            )
            story_id = res
            if not story_id:
                print("[PIPELINE] Story creation skipped (duplicate detected).")
                return
            
            # Layer 3 tasks (Images, Audio, Social) are now ONLY on-demand.
            # No automatic generation here.
            
            # 20-21: Learning System Init
            init_growth_metrics(story_id)
            print(f"[PIPELINE][SUCCESS] Story {story_id} generated and saved to DB (Layer 2 Complete).")
            
            # Send Email Notification
            try:
                from email_utils import send_alert_email
                asyncio.create_task(asyncio.to_thread(send_alert_email, content_pkg['title']))
            except Exception as email_err:
                print(f"[PIPELINE] Failed to send email notification: {email_err}")
            
        except Exception as e:
            print(f"[SIGNAL ERROR] Failed to process signal: {e}")
            try:
                with get_db() as conn:
                    cur = conn.cursor()
                    cur.execute("UPDATE scraped_raw SET clustered = 2 WHERE id = ?", (signal['id'],))
                    conn.commit()
            except Exception as db_err:
                print(f"Failed to archive failed signal: {db_err}")

    def calculate_priority(self, signal):
        import math
        import time
        from backend.intelligence_engine import calculate_priority_score, get_source_credibility

        try:
            source_cred = get_source_credibility(signal.get("source_id", ""))
            try:
                ts = float(signal.get("timestamp", time.time()))
            except:
                ts = time.time()
            source_type = signal.get("source_type", "website").lower()
            priority = calculate_priority_score(source_type, ts, source_cred)
            return priority * 100
        except Exception as e:
            print(f"[PRIORITY] Calculation failed, defaulting to 60: {e}")
            return 60

    async def generate_article_via_llm(self, signal, mode):
        """Call LLM with orchestration prompts."""
        print(f"[PIPELINE] Generating article for: {signal['title'][:50]}...")
        
        # Use run_microtask_a_with_retry from layer3_generation.generation_fanout
        from layer3_generation.generation_fanout import run_microtask_a_with_retry
        result = await run_microtask_a_with_retry(signal['content'], url=signal.get('url'), trace_id=self.trace_id, title=signal.get('title'))
        
        if not result or result == "ABORT_INSUFFICIENT_DATA":
            print(f"[OBSERVABILITY][{self.traceparent}] [GROUNDING] LLM returned ABORT_INSUFFICIENT_DATA or empty response.")
            raise Exception("ABORT_INSUFFICIENT_DATA")
            
        # Provenance verification: Every provenance_url must match input signal['url']
        allowed_urls = [signal['url']]
        provenance_urls = []
        
        def extract_provenance(d):
            if isinstance(d, dict):
                for k, v in d.items():
                    if k == 'provenance_url':
                        provenance_urls.append(v)
                    else:
                        extract_provenance(v)
            elif isinstance(d, list):
                for item in d:
                    extract_provenance(item)
                    
        extract_provenance(result)
        
        for url in provenance_urls:
            if not url or url not in allowed_urls:
                print(f"[OBSERVABILITY][{self.traceparent}] [PROVENANCE_FAIL] Hallucinated/invalid provenance url: {url}")
                raise Exception("PROVENANCE_FAIL")

        # Convert sections' list of dicts to string body for backward compatibility
        body_parts = []
        for s in result.get("sections", []):
            content_val = s.get("content", "")
            if isinstance(content_val, list):
                facts = [item.get("fact", "") for item in content_val if isinstance(item, dict)]
                body_parts.append("\n".join(facts))
            else:
                body_parts.append(str(content_val))
        result["body"] = "\n\n".join(body_parts)
        
        # Ensure summary is in the expected format for orchestrator, checking if microtask A returned ai_summary directly
        if "ai_summary" in result and isinstance(result["ai_summary"], str) and result["ai_summary"].strip():
            result["summary"] = {
                "headline": result.get("title", signal["title"]),
                "summary": result["ai_summary"],
                "key_points": result.get("keywords", [])[:3]
            }
        else:
            try:
                from backend.llm import generate_ai_summary
                ai_summary_pkg = generate_ai_summary(result["title"], result["body"], result.get("sections"))
                result["summary"] = {
                    "headline": ai_summary_pkg.get("headline", result["title"]),
                    "summary": ai_summary_pkg.get("summary", result.get("meta_description", "")),
                    "key_points": ai_summary_pkg.get("key_points", [])
                }
            except Exception as summary_err:
                print(f"[SUMMARY ERROR] Failed to generate AI summary: {summary_err}")
                result["summary"] = {
                    "headline": result.get("title", signal["title"]),
                    "summary": result.get("meta_description", ""),
                    "key_points": [item.get("fact", "") for item in result.get("key_points", []) if isinstance(item, dict)] if isinstance(result.get("key_points"), list) else result.get("keywords", [])[:3]
                }
            
        return result

if __name__ == "__main__":
    orchestrator = NewsroomOrchestrator()
    asyncio.run(orchestrator.run_full_pipeline())
