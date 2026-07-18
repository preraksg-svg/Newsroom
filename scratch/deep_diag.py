"""
Deep diagnostic: find exactly WHY news is not being scraped.
"""
import asyncio, sqlite3, os, sys, time, importlib
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'newsroom.db')

def check_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cutoff = int(time.time()) - 86400
    cur.execute("SELECT COUNT(*) as c FROM scraped_raw WHERE CAST(timestamp AS INTEGER) > ?", (cutoff,))
    print(f"[DB] Raw signals in last 24h: {cur.fetchone()['c']}")
    
    cur.execute("SELECT title, timestamp, source_id FROM scraped_raw ORDER BY CAST(timestamp AS INTEGER) DESC LIMIT 5")
    rows = cur.fetchall()
    print("[DB] Most recent raw signals:")
    for r in rows:
        try:
            age_h = (time.time() - int(float(r['timestamp']))) / 3600
            print(f"  [{age_h:.1f}h ago] {r['source_id']}: {r['title'][:60]}")
        except:
            print(f"  [?h ago] {r['source_id']}: {r['title'][:60]}")
    
    cur.execute("SELECT COUNT(*) as c FROM source_scores WHERE activity_status='active'")
    print(f"\n[DB] Active sources: {cur.fetchone()['c']}")
    
    cur.execute("""SELECT source_id, domain, failure_count, fetch_status 
                   FROM source_scores WHERE failure_count > 0 
                   ORDER BY failure_count DESC LIMIT 10""")
    rows = cur.fetchall()
    if rows:
        print("[DB] Failing sources (circuit breaker risk):")
        for r in rows:
            print(f"  {r['source_id']:30s} failures={r['failure_count']} status={r['fetch_status']}")
    else:
        print("[DB] No failing sources found.")
    
    # Check circuit_breakers.json
    cb_path = os.path.join(os.path.dirname(__file__), 'circuit_breakers.json')
    if os.path.exists(cb_path):
        import json
        with open(cb_path) as f:
            cbs = json.load(f)
        open_cbs = {k: v for k, v in cbs.items() if v.get('state') == 'OPEN'}
        print(f"\n[CB] OPEN circuit breakers: {len(open_cbs)}")
        for k, v in open_cbs.items():
            remaining = max(0, v.get('quarantined_until', 0) - time.time())
            print(f"  QUARANTINED: {k} (remaining: {remaining/60:.1f}min)")
    else:
        print("\n[CB] No circuit_breakers.json found.")
    
    conn.close()

async def test_scrapers():
    import workers.website_worker as ww
    importlib.reload(ww)
    
    print("\n[SCRAPER] Testing working RSS/web sources...")
    test_sources = [
        ('motorbeam_rss',    'https://www.motorbeam.com/feed/'),
        ('autocar_india',    'https://www.autocarindia.com/car-news'),
        ('carandbike',       'https://www.carandbike.com/rss/news.rss'),
        ('carblogindia',     'https://www.carblogindia.com/feed/'),
    ]
    
    total = 0
    for sid, url in test_sources:
        try:
            results = await asyncio.wait_for(ww.scrape_website(url), timeout=15.0)
            print(f"  [{sid}] => {len(results)} articles")
            total += len(results)
            for r in results[:1]:
                wc = len(r['content_raw'].split())
                print(f"    title: {r['title'][:60]}")
                print(f"    words: {wc}")
        except asyncio.TimeoutError:
            print(f"  [{sid}] TIMEOUT (>15s)")
        except Exception as e:
            print(f"  [{sid}] ERROR: {e}")
    
    print(f"\n[SCRAPER] Total articles across tested sources: {total}")
    return total

check_db()
total = asyncio.run(test_scrapers())
print(f"\n{'[OK] Scraping is working.' if total > 0 else '[FAIL] ZERO articles - pipeline broken!'}")
