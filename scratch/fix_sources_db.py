"""
Fix broken sources in source_scores database:
- Deactivate sources that 403 or return 0 articles (auto.ndtv.com, motoroctane.com)
- Add motorbeam.com RSS which is verified to return 15 articles
- Verify the final source list
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), '..', 'newsroom.db')
if not os.path.exists(db_path):
    db_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'db', 'newsroom.db')

print(f"Using DB: {os.path.abspath(db_path)}")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Show current active sources
cur.execute("SELECT source_id, domain, type, activity_status, failure_count FROM source_scores ORDER BY activity_status, domain")
rows = cur.fetchall()
print(f"\nAll sources ({len(rows)} total):")
for r in rows:
    print(f"  [{r['activity_status']}] {r['domain']!r:60s} type={r['type']:10s} failures={r['failure_count']}")

# Deactivate broken sources
broken_domains = ['auto.ndtv.com', 'www.motoroctane.com']
for domain in broken_domains:
    cur.execute("UPDATE source_scores SET activity_status='inactive' WHERE domain=?", (domain,))
    if cur.rowcount:
        print(f"\n[FIX] Deactivated: {domain}")
    else:
        print(f"\n[INFO] Not found in DB: {domain}")

# Add motorbeam.com if not already present
cur.execute("SELECT source_id FROM source_scores WHERE domain='www.motorbeam.com'")
if not cur.fetchone():
    cur.execute("""
        INSERT INTO source_scores (
            source_id, domain, type, category, tier, score_authority, access_method, country,
            activity_status, failure_count, fetch_status
        ) VALUES (
            'motorbeam_rss', 'https://www.motorbeam.com/feed/', 'website', 'EV_News', 'Tier 1',
            0.78, 'RSS', 'IN', 'active', 0, 'success'
        )
    """)
    print("\n[FIX] Added motorbeam.com RSS as active source")
else:
    cur.execute("UPDATE source_scores SET activity_status='active', failure_count=0 WHERE domain='www.motorbeam.com'")
    print("\n[FIX] Re-activated motorbeam.com")

# Reset circuit breaker failures for all active sources
cur.execute("UPDATE source_scores SET failure_count=0 WHERE activity_status='active'")
print(f"\n[FIX] Reset failure counts for all active sources")

conn.commit()

# Show final state
print("\n--- Final Active Sources ---")
cur.execute("SELECT source_id, domain, type, activity_status FROM source_scores WHERE activity_status='active' ORDER BY domain")
for r in cur.fetchall():
    print(f"  {r['source_id']:30s} {r['domain']!r:60s} type={r['type']}")

conn.close()
print("\nDone.")
