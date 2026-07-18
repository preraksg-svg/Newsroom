import sqlite3
import os
import sys

sys.path.append(os.getcwd())
from backend.db.queries import DB_PATH

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get all signals marked as clustered=2 (rejected)
cur.execute("""
    SELECT r.id, r.title, r.source_id, r.url 
    FROM scraped_raw r 
    WHERE r.clustered = 2
""")
rows = cur.fetchall()
print(f"Found {len(rows)} raw signals marked as clustered=2 (rejected).")

# Reset clustered=0 for these specific signals
reset_count = 0
for r in rows:
    cur.execute("UPDATE scraped_raw SET clustered = 0 WHERE id = ?", (r['id'],))
    reset_count += 1

conn.commit()
print(f"Successfully reset clustered=0 for {reset_count} rejected signals.")
conn.close()
