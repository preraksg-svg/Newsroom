import sqlite3
import os

from backend.db.queries import DB_PATH
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Get table schema
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cur.fetchall()]
print("Tables:", tables)

for tbl in ['sources', 'source_scores']:
    if tbl in tables:
        cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE activity_status='active'")
        print(f"Active in {tbl}:", cur.fetchone()[0])
        cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE activity_status='active' AND country='IN'")
        print(f"Active in {tbl} (IN only):", cur.fetchone()[0])
        cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE activity_status='active' AND COALESCE(country, 'IN')='IN'")
        print(f"Active in {tbl} (IN only with COALESCE):", cur.fetchone()[0])

conn.close()
