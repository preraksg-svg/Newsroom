import sqlite3
import os
from backend.db.queries import init_db

DB_PATH = os.path.join(os.path.dirname(__file__), '../newsroom.db')
init_db()
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT * FROM scraped_raw LIMIT 1")
row = cur.fetchone()
if row:
    print("KEYS:", row.keys())
    print("URL:", row['url'])
    print("TITLE:", row['title'])
    print("CONTENT (first 200 chars):", row['content'][:200])
else:
    print("No rows in scraped_raw")
conn.close()
