import sqlite3
import os
import sys

sys.path.append(os.getcwd())
from backend.db.queries import DB_PATH

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Find raw signals that are clustered = 1 (marked as processed) but no story exists
cur.execute("""
    SELECT r.id, r.title, r.source_id, r.url 
    FROM scraped_raw r 
    LEFT JOIN stories s ON r.url = s.url 
    WHERE r.clustered = 1 AND s.url IS NULL
""")
rows = cur.fetchall()
print(f"Found {len(rows)} raw signals marked as clustered=1 with no story.")

# Reset clustered=0 for these specific signals so that run_full_pipeline() processes them
reset_count = 0
for r in rows:
    # Double check if the source is an Indian source
    cur.execute("SELECT country FROM sources WHERE source_id=?", (r['source_id'],))
    src_row = cur.fetchone()
    country = src_row[0] if src_row else 'IN'
    if country == 'IN':
        cur.execute("UPDATE scraped_raw SET clustered = 0 WHERE id = ?", (r['id'],))
        reset_count += 1

conn.commit()
print(f"Successfully reset clustered=0 for {reset_count} Indian raw signals.")
conn.close()
