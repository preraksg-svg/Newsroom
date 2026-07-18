from fastapi import APIRouter, HTTPException, Query, Body, BackgroundTasks
from fastapi.responses import Response
from typing import Optional, Dict, Any
import aiohttp
import re
from backend.services.news_service import NewsService, AnalyticsService, IntelligenceService

router = APIRouter(prefix="/api")

import time

LAST_FAST_SCRAPE_TIME = 0.0

async def run_fast_scrape_background():
    try:
        from workers.website_worker import scrape_website
        from system_orchestrator import NewsroomOrchestrator
        from backend.db.queries import get_db
        
        targets = [
            ("evo_india_ev", "https://www.evoindia.com/news"),
            ("autocar_india_website", "https://www.autocarindia.com/car-news"),
            ("overdrive_india_website", "https://www.overdrive.in/news-cars")
        ]
        
        print("[FAST-SCRAPE] Starting fast-path background scrape...")
        orchestrator = NewsroomOrchestrator()
        
        for source_id, url in targets:
            try:
                results = await scrape_website(url)
                if results:
                    saved_count = 0
                    for r in results:
                        import hashlib
                        import json
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
                    print(f"[FAST-SCRAPE] Source {source_id}: saved {saved_count} new raw signals.")
            except Exception as e:
                print(f"[FAST-SCRAPE] Error scraping {source_id}: {e}")
                
        signals = orchestrator.get_latest_raw_signals(limit=5)
        for sig in signals:
            try:
                await orchestrator.process_signal(sig)
            except Exception as e:
                print(f"[FAST-SCRAPE] Error processing signal {sig.get('id')}: {e}")
                
    except Exception as global_err:
        print(f"[FAST-SCRAPE] Error in fast scrape background task: {global_err}")

@router.get("/migrate-drafts")
async def api_migrate_drafts():
    try:
        import os
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from scratch.regenerate_drafts import regenerate_all_drafts
        import asyncio
        asyncio.create_task(regenerate_all_drafts())
        return {"status": "success", "message": "Drafts regeneration migration started in the background."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/news")
def get_news(
    background_tasks: BackgroundTasks,
    status: Optional[str] = None, 
    search: Optional[str] = None, 
    limit: int = 100,
    page: int = 1
):
    global LAST_FAST_SCRAPE_TIME
    try:
        current_time = time.time()
        if current_time - LAST_FAST_SCRAPE_TIME > 21600.0:
            LAST_FAST_SCRAPE_TIME = current_time
            background_tasks.add_task(run_fast_scrape_background)
            
        data = NewsService.get_news(status, search, limit, page)
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/news/{id}")
def get_article(id: str):
    try:
        data = NewsService.get_article(id)
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/news/update")
def update_article(record_id: str, data: Dict[str, Any]):
    try:
        NewsService.update_article(record_id, data)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/action")
async def handle_action(payload: Dict[str, Any] = Body(...)):
    action = payload.get("action")
    article_id = payload.get("article_id")
    if not action or not article_id:
        return {"success": False, "error": "Missing action or article_id"}
    params = payload.get("params") or {}
    try:
        result = await NewsService.handle_action(action, article_id, params)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/analytics")
def get_analytics():
    try:
        data = AnalyticsService.get_global_stats()
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/groq-usage")
def get_groq():
    try:
        data = AnalyticsService.get_groq_usage()
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/sources")
def get_sources():
    try:
        data = IntelligenceService.get_sources()
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/orchestrate")
async def trigger_orchestrate(background_tasks: BackgroundTasks):
    try:
        from system_orchestrator import NewsroomOrchestrator
        orchestrator = NewsroomOrchestrator()
        background_tasks.add_task(orchestrator.run_full_pipeline)
        return {"success": True, "data": "Orchestration started in background"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/orchestrate")
async def trigger_orchestrate_get(background_tasks: BackgroundTasks):
    try:
        from system_orchestrator import NewsroomOrchestrator
        orchestrator = NewsroomOrchestrator()
        background_tasks.add_task(orchestrator.run_full_pipeline)
        return {"success": True, "data": "Orchestration started in background via GET"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/raw-source/{id}")
def get_raw_source(id: str):
    try:
        data = NewsService.get_raw_source(id)
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/publish-log/{id}")
def get_publish_log(id: str):
    """Return real-time Playwright publisher log for an article."""
    from backend.services.news_service import PUBLISH_LOGS
    logs = PUBLISH_LOGS.get(id, [])
    return {"logs": logs}

@router.get("/proxy")
async def proxy_url(
    url: str,
    title: Optional[str] = None,
    meta_title: Optional[str] = None,
    meta_desc: Optional[str] = None,
    source: Optional[str] = None,
    source_url: Optional[str] = None,
    sections: Optional[str] = None
):
    try:
        if not url.startswith("http"):
            url = "https://" + url
            
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Encoding': 'gzip, deflate, identity',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status in (401, 403, 406, 503):
                    # Fallback to public CORS proxy if blocked (e.g. Cloudflare)
                    fallback_url = f"https://api.allorigins.win/raw?url={url}"
                    async with session.get(fallback_url, timeout=15) as fb_resp:
                        content_type = fb_resp.headers.get("Content-Type", "text/html")
                        content_bytes = await fb_resp.read()
                else:
                    content_type = resp.headers.get("Content-Type", "")
                    content_bytes = await resp.read()
                    
                if "text/html" in content_type.lower():
                    try:
                        content_str = content_bytes.decode('utf-8', errors='ignore')
                        
                        # Neutralize frame-busting scripts
                        content_str = re.sub(r'top\.location', 'self.location', content_str, flags=re.IGNORECASE)
                        content_str = re.sub(r'window\.top', 'window.self', content_str, flags=re.IGNORECASE)
                        content_str = re.sub(r'window\.frameElement', 'null', content_str, flags=re.IGNORECASE)
                        
                        # Rewrite relative asset paths to absolute zapway.app paths so SPA resources load correctly
                        content_str = content_str.replace('src="/assets/', 'src="https://zapway.app/assets/')
                        content_str = content_str.replace('href="/assets/', 'href="https://zapway.app/assets/')
                        content_str = content_str.replace('href="/vite.svg"', 'href="https://zapway.app/vite.svg"')
                        content_str = content_str.replace('href="/font.css"', 'href="https://zapway.app/font.css"')
                        content_str = content_str.replace('src="/fonts/', 'src="https://zapway.app/fonts/')
                        content_str = content_str.replace('href="/fonts/', 'href="https://zapway.app/fonts/')
                        
                        base_tag = f"<base href='{url}'>"
                        
                        # Inject auto-login and form-fill script block
                        if "zapway.app" in url.lower():
                            # Parse sections list to construct main body and section heading
                            import json
                            parsed_sections = []
                            if sections:
                                try:
                                    parsed_sections = json.loads(sections)
                                except:
                                    pass
                            
                            full_body_parts = []
                            first_heading = ""
                            first_content = ""
                            for s in parsed_sections:
                                if isinstance(s, dict):
                                    if s.get("heading"):
                                        full_body_parts.append(s["heading"])
                                    if s.get("content"):
                                        full_body_parts.append(s["content"])
                                    bullets = s.get("bullets", [])
                                    if isinstance(bullets, list):
                                        full_body_parts.extend([b for b in bullets if isinstance(b, str)])
                                    elif isinstance(bullets, str):
                                        full_body_parts.append(bullets)
                            full_body = "\n\n".join(full_body_parts)
                            
                            if parsed_sections and isinstance(parsed_sections[0], dict):
                                first_heading = parsed_sections[0].get("heading", "")
                                first_content = parsed_sections[0].get("content", "")
                            if not first_content:
                                first_content = full_body

                            word_count = len(full_body.split()) if full_body else 100
                            read_time = f"{max(1, round(word_count / 200))} min read"

                            login_script = f"""
                            <script>
                            (function() {{
                                const articleData = {{
                                    title: {repr(title or '')},
                                    meta_title: {repr(meta_title or '')},
                                    meta_desc: {repr(meta_desc or '')},
                                    source: {repr(source or '')},
                                    source_url: {repr(source_url or '')},
                                    first_heading: {repr(first_heading or '')},
                                    first_content: {repr(first_content or '')},
                                    read_time: {repr(read_time)}
                                }};

                                let loginClicked = false;
                                let formFilled = false;

                                function runAutomation() {{
                                    // 1. Handle Login Page
                                    const emailField = document.getElementById('email');
                                    const passwordField = document.getElementById('password');
                                    if (emailField && passwordField && !loginClicked) {{
                                        emailField.value = 'prerak.sg@gmail.com';
                                        emailField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        
                                        passwordField.value = '132325';
                                        passwordField.dispatchEvent(new Event('input', {{ bubbles: true }}));

                                        const buttons = document.querySelectorAll('button');
                                        for (let btn of buttons) {{
                                            if (btn.textContent.toLowerCase().includes('login') || btn.textContent.toLowerCase().includes('sign in') || btn.type === 'submit') {{
                                                loginClicked = true;
                                                console.log('[AUTO-LOGIN] Submitting credentials');
                                                btn.click();
                                                break;
                                            }}
                                        }}
                                        return;
                                    }}

                                    // 2. Handle Form Page
                                    function fillByPlaceholder(placeholderText, value) {{
                                        if (!value) return;
                                        const inputs = document.querySelectorAll('input, textarea');
                                        for (let el of inputs) {{
                                            const ph = el.getAttribute('placeholder') || '';
                                            if (ph.toLowerCase().includes(placeholderText.toLowerCase())) {{
                                                if (!el.value) {{
                                                    el.value = value;
                                                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                                    console.log('[AUTO-FILL] Filled: ' + placeholderText);
                                                }}
                                                break;
                                            }}
                                        }}
                                    }}

                                    // Verify we are on the insertion form (and not login page)
                                    if (!emailField && !passwordField && !formFilled) {{
                                        const headlineField = document.querySelector('input[placeholder*="headline"], input[placeholder*="Headline"]');
                                        if (headlineField) {{
                                            fillByPlaceholder("Reuters", articleData.source);
                                            fillByPlaceholder("news headline", articleData.title);
                                            fillByPlaceholder("Google search results & browser tab", articleData.meta_title);
                                            fillByPlaceholder("under the title in Google", articleData.meta_desc);
                                            fillByPlaceholder("Jane Doe", "Zapway Team");
                                            fillByPlaceholder("JD", "ZT");
                                            fillByPlaceholder("Senior correspondent", "EV News Correspondent");
                                            fillByPlaceholder("4 min read", articleData.read_time);
                                            fillByPlaceholder("Overview, Key Findings", articleData.first_heading || articleData.title);
                                            fillByPlaceholder("Section body text", articleData.first_content);
                                            formFilled = true;
                                            console.log('[AUTO-FILL] Form processing completed');
                                        }}
                                    }}
                                }}
                                
                                // Poll every 500ms
                                setInterval(runAutomation, 500);
                            }})();
                            </script>
                            """
                            base_tag = base_tag + login_script

                        if "<head>" in content_str.lower():
                            content_str = re.sub(r'(<head[^>]*>)', r'\1' + base_tag, content_str, flags=re.IGNORECASE)
                        else:
                            content_str = base_tag + content_str
                        content_bytes = content_str.encode('utf-8')
                    except Exception:
                        pass
                        
                return Response(content=content_bytes, media_type=content_type)
    except Exception as e:
        # Final fallback if aiohttp throws exception (e.g. SSL error)
        try:
            async with aiohttp.ClientSession() as session:
                fallback_url = f"https://api.allorigins.win/raw?url={url}"
                async with session.get(fallback_url, timeout=15) as fb_resp:
                    content_bytes = await fb_resp.read()
                    return Response(content=content_bytes, media_type="text/html")
        except:
            return Response(content=f"Failed to load URL: {str(e)}", status_code=500, media_type="text/plain")

@router.get("/rejected")
def get_rejected():
    try:
        data = NewsService.get_rejected()
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/restore/{id}")
def restore_article(id: str):
    try:
        NewsService.restore_article(id)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/growth")
def get_growth():
    try:
        data = AnalyticsService.get_growth()
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/seo")
def get_seo():
    try:
        data = NewsService.get_seo_overview()
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/experiments")
def get_experiments():
    try:
        data = NewsService.get_experiments()
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/social/{id}")
def get_social_bundle(id: str):
    try:
        data = NewsService.get_social_bundle(id)
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/tasks/{task_id}")
def get_task_status(task_id: str):
    try:
        from backend.db import queries
        data = queries.get_task(task_id)
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/next-fetch")
def get_next_fetch():
    try:
        import datetime
        import time
        from backend.db.queries import get_db
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT last_fetch_time FROM sources WHERE activity_status = 'active' AND last_fetch_time IS NOT NULL ORDER BY last_fetch_time DESC LIMIT 1")
            row = cur.fetchone()
            
        if row and row['last_fetch_time']:
            try:
                # Handle formats dynamically
                last_fetch = datetime.datetime.strptime(row['last_fetch_time'], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                last_fetch = datetime.datetime.strptime(row['last_fetch_time'].split('.')[0], "%Y-%m-%d %H:%M:%S")
            last_ts = last_fetch.replace(tzinfo=datetime.timezone.utc).timestamp()
        else:
            last_ts = time.time() - 3600
            
        next_ts = last_ts + 21600
        seconds_left = int(next_ts - time.time())
        if seconds_left <= 0:
            time_past = time.time() - last_ts
            cycles = int(time_past / 21600) + 1
            next_ts = last_ts + cycles * 21600
            seconds_left = max(0, int(next_ts - time.time()))
        return {"success": True, "data": {"seconds_left": seconds_left}}
    except Exception as e:
        print(f"Error calculating next-fetch: {e}")
        return {"success": True, "data": {"seconds_left": 21600}}

@router.get("/v1/diagnostics/ingestion-status")
def get_ingestion_status():
    import os
    import json
    import time
    import traceback
    try:
        # Check database connectivity
        from backend.db.queries import get_db
        db_connected = False
        active_sources = []
        try:
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
                db_connected = True
                
                # Retrieve all sources from source_scores table
                cur.execute("""
                    SELECT source_id, name, domain, type, activity_status, fetch_status, failure_count
                    FROM source_scores
                """)
                active_sources = [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Database diagnostics failure: {e}")
            db_connected = False

        # Check Redis connection & get heartbeat
        heartbeat = "DOWN"
        circuit_breakers = {}
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.2)
            conn_res = s.connect_ex(('127.0.0.1', 6379))
            s.close()
            
            if conn_res == 0:
                import redis
                r = redis.Redis(host='127.0.0.1', port=6379, db=0, socket_timeout=1)
                r.ping()
                hb_val = r.get("health:layer1:heartbeat")
                if hb_val and hb_val.decode('utf-8') == "OK":
                    heartbeat = "OK"
                
                # Fetch circuit breakers from Redis
                cb_val = r.get("health:layer1:circuit_breakers")
                if cb_val:
                    circuit_breakers = json.loads(cb_val.decode('utf-8'))
        except Exception:
            # Fallback to local files if Redis is down
            pass

        # If Redis was down or key was missing, fall back to checking circuit_breakers.json file
        if not circuit_breakers:
            try:
                scratch_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../scratch/circuit_breakers.json"))
                if os.path.exists(scratch_file):
                    with open(scratch_file, "r") as f:
                        circuit_breakers = json.load(f)
            except Exception as e:
                print(f"Failed to read local circuit breakers file: {e}")

        # Populating heartbeat status fallback based on local circuit breakers file mod time (if within 2 mins)
        if heartbeat == "DOWN":
            try:
                scratch_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../scratch/circuit_breakers.json"))
                if os.path.exists(scratch_file):
                    file_mod_time = os.path.getmtime(scratch_file)
                    if time.time() - file_mod_time < 180:  # Active within last 3 minutes
                        heartbeat = "OK"
            except Exception:
                pass

        # Populate states for all sources
        sources_list = []
        for src in active_sources:
            sid = src["source_id"]
            cb_info = circuit_breakers.get(sid, {})
            
            cb_state = cb_info.get("state", "CLOSED")
            quarantined_until = cb_info.get("quarantined_until", None)
            
            # Double check if database shows it's failing consecutively
            fail_cnt = src.get("failure_count")
            if fail_cnt is None:
                fail_cnt = 0
            if fail_cnt >= 3 and cb_state == "CLOSED":
                cb_state = "OPEN"
                
            sources_list.append({
                "source_id": sid,
                "name": src["name"],
                "domain": src["domain"],
                "type": src["type"],
                "activity_status": src["activity_status"],
                "fetch_status": src["fetch_status"],
                "failure_count": fail_cnt,
                "circuit_breaker_state": cb_state,
                "quarantined_until": quarantined_until
            })
            
        return {
            "success": True,
            "data": {
                "heartbeat": heartbeat,
                "database_connected": db_connected,
                "sources": sources_list
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@router.get("/v1/diagnostics/sources-health")
def get_sources_health():
    try:
        import json
        import os
        from email_utils import send_alert_email
        
        health_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../static/sources_health.json"))
        if not os.path.exists(health_file):
            return {
                "success": False, 
                "error": "No health telemetry available yet. Run scripts/verify_sources.py first."
            }
            
        with open(health_file, "r") as f:
            telemetry = json.load(f)
            
        offline_tier1 = []
        for src in telemetry.get("sources", []):
            if src.get("tier") in ("Tier 1", "tier_1") and src.get("status") == "Offline":
                offline_tier1.append(src["name"])
                
        if offline_tier1:
            fail_state_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../static/consecutive_failures.json"))
            fail_state = {}
            if os.path.exists(fail_state_file):
                try:
                    with open(fail_state_file, "r") as f:
                        fail_state = json.load(f)
                except:
                    pass
            
            alerts_triggered = []
            for name in offline_tier1:
                fail_state[name] = fail_state.get(name, 0) + 1
                if fail_state[name] >= 3:
                    alerts_triggered.append(name)
            
            # Reset counters for healthy nodes
            for src in telemetry.get("sources", []):
                if src.get("status") == "Healthy" and src["name"] in fail_state:
                    fail_state.pop(src["name"], None)
            
            with open(fail_state_file, "w") as f:
                json.dump(fail_state, f)
                
            if alerts_triggered:
                subject = "CRITICAL: Tier 1 EV Sources Offline Alerts"
                body = "The following Tier 1 sources have been offline for 3+ consecutive sweeps:\n" + "\n".join(f"- {name}" for name in alerts_triggered)
                try:
                    send_alert_email(subject, body)
                except Exception as ex:
                    print(f"Failed to send alert email: {ex}")
                    
        return {"success": True, "data": telemetry}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/debug-db")
def get_debug_db():
    try:
        from backend.db.queries import get_db
        import io
        import sys
        import traceback
        from system_orchestrator import NewsroomOrchestrator
        
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        
        orchestrator_log = ""
        error_msg = ""
        try:
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM scraped_raw WHERE title LIKE '%sierra%' AND source_id = 'evo_india_ev'")
                row = cur.fetchone()
                if row:
                    signal = dict(row)
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(NewsroomOrchestrator().process_signal(signal))
                    loop.close()
                else:
                    error_msg = "No Sierra signal found from evo_india_ev"
        except Exception as run_err:
            error_msg = f"Orchestrator Error: {run_err}\n{traceback.format_exc()}"
        finally:
            sys.stdout = old_stdout
            orchestrator_log = buffer.getvalue()

        with get_db() as conn:
            cur = conn.cursor()
            
            cur.execute("SELECT count(*) as count, status FROM stories GROUP BY status")
            stories = [dict(r) for r in cur.fetchall()]
            
            cur.execute("SELECT count(*) as count, clustered FROM scraped_raw GROUP BY clustered")
            scraped_raw = [dict(r) for r in cur.fetchall()]
            
            cur.execute("SELECT id, title, source_id, timestamp, clustered, length(content) as content_len FROM scraped_raw WHERE title LIKE '%sierra%'")
            recent_raw = [dict(r) for r in cur.fetchall()]
            
            return {
                "success": True,
                "data": {
                    "stories_by_status": stories,
                    "scraped_raw_by_clustered": scraped_raw,
                    "recent_raw_signals": recent_raw,
                    "orchestrator_log": orchestrator_log,
                    "orchestrator_error": error_msg
                }
            }
    except Exception as e:
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}



