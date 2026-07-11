import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('newsroom.db')
cur = conn.cursor()
cur.execute("SELECT id, title, content FROM scraped_raw WHERE id='raw_b88b7bc88dbcd2eb480a8bf79a32c69c' OR id LIKE '%rec_1783760366248%' OR id LIKE '%17837603%' LIMIT 4")
rows = cur.fetchall()
if not rows:
    # Query by url matching
    cur.execute("SELECT id, title, content FROM scraped_raw ORDER BY timestamp DESC LIMIT 3")
    rows = cur.fetchall()

for row in rows:
    print(f"ID: {row[0]}")
    print(f"Title: {row[1]}")
    print(f"Content:\n{row[2][:1000]}")
    print("-" * 50)
conn.close()
