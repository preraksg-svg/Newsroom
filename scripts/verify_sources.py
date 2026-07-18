import asyncio
import json
import os
import sys
import time
import secrets
import random
import logging
from typing import Dict, Any, List

sys.path.append(os.getcwd())
import httpx
from backend.db.queries import get_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_sources")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
]

def make_traceparent() -> str:
    # Generates a W3C compliant traceparent header: 00-traceid-parentid-flags
    trace_id = secrets.token_hex(16)
    parent_id = secrets.token_hex(8)
    return f"00-{trace_id}-{parent_id}-01"

async def check_source(sem: asyncio.Semaphore, client: httpx.AsyncClient, source: Dict[str, Any]) -> Dict[str, Any]:
    source_id = source["source_id"]
    name = source["name"]
    url = source["domain"]
    tier = source["tier"]
    
    is_twitter = "twitter.com" in url.lower() or "x.com" in url.lower()
    check_url = "https://twitter.com" if is_twitter else url

    if not check_url.startswith("http://") and not check_url.startswith("https://"):
        check_url = "https://" + check_url
        
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "traceparent": make_traceparent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    status_state = "Offline"
    latency_ms = 0.0
    error_msg = None
    
    async with sem:
        start_time = time.perf_counter()
        try:
            # Send GET request with a 10s timeout
            response = await client.get(check_url, headers=headers, timeout=10.0, follow_redirects=True)
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            
            is_youtube = "youtube.com" in url.lower()
            
            if 200 <= response.status_code < 400:
                status_state = "Healthy"
            elif response.status_code in (429, 403, 401):
                status_state = "Degraded"
                error_msg = f"HTTP {response.status_code}: Rate-limited/Blocked"
            elif (is_youtube or is_twitter) and response.status_code == 302:
                status_state = "Healthy"
            else:
                status_state = "Degraded"
                error_msg = f"HTTP {response.status_code}"
        except httpx.ConnectTimeout:
            status_state = "Degraded"
            error_msg = "Connection Timeout"
        except httpx.ConnectError:
            status_state = "Degraded"
            error_msg = "DNS/Connection Error"
        except httpx.HTTPError as he:
            status_state = "Degraded"
            error_msg = f"HTTP Error: {str(he)}"
        except Exception as e:
            status_state = "Degraded"
            error_msg = str(e)
            
    return {
        "source_id": source_id,
        "name": name,
        "url": url,
        "tier": tier,
        "status": status_state,
        "latency_ms": round(latency_ms, 2),
        "error": error_msg,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

async def main():
    # 1. Fetch from SQLite source_scores
    sources = []
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT source_id, name, domain, tier FROM source_scores")
            rows = cur.fetchall()
            for r in rows:
                sources.append({
                    "source_id": r[0],
                    "name": r[1],
                    "domain": r[2],
                    "tier": r[3]
                })
    except Exception as e:
        logger.error(f"Failed to fetch sources from database: {e}")
        sys.exit(1)
        
    if not sources:
        logger.warning("No active sources found in registry.")
        return

    logger.info(f"Loaded {len(sources)} sources from registry. Launching sweep...")
    
    # 2. Configure Semaphore (concurrency limit = 15) and httpx client
    sem = asyncio.Semaphore(15)
    limits = httpx.Limits(max_connections=50, max_keepalive_connections=50)
    
    results = []
    async with httpx.AsyncClient(limits=limits, verify=False) as client:
        tasks = [check_source(sem, client, s) for s in sources]
        results = await asyncio.gather(*tasks)
        
    # 3. Compute LatencyIndex
    healthy_latencies = [r["latency_ms"] for r in results if r["status"] in ("Healthy", "Degraded") and r["latency_ms"] > 0]
    latency_index = sum(healthy_latencies) / len(healthy_latencies) if healthy_latencies else 0.0
    
    output = {
        "latency_index_ms": round(latency_index, 2),
        "total_checked": len(results),
        "healthy_count": sum(1 for r in results if r["status"] == "Healthy"),
        "degraded_count": sum(1 for r in results if r["status"] == "Degraded"),
        "offline_count": sum(1 for r in results if r["status"] == "Offline"),
        "sources": results,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    # Save findings locally so API can load instantly
    static_dir = os.path.join(os.path.dirname(__file__), "../static")
    os.makedirs(static_dir, exist_ok=True)
    health_file = os.path.join(static_dir, "sources_health.json")
    
    with open(health_file, "w") as f:
        json.dump(output, f, indent=2)
        
    logger.info(f"Sources sweep completed. LatencyIndex: {output['latency_index_ms']} ms. Saved telemetry to {health_file}")

if __name__ == "__main__":
    asyncio.run(main())
