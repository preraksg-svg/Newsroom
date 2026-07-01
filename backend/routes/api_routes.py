from fastapi import APIRouter, HTTPException, Query, Body, BackgroundTasks
from typing import Optional, Dict, Any
from backend.services.news_service import NewsService, AnalyticsService, IntelligenceService

router = APIRouter(prefix="/api")

@router.get("/news")
def get_news(
    status: Optional[str] = None, 
    search: Optional[str] = None, 
    limit: int = 100,
    page: int = 1
):
    try:
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

@router.get("/raw-source/{id}")
def get_raw_source(id: str):
    try:
        data = NewsService.get_raw_source(id)
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

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

