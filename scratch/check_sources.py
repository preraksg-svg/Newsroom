import sqlite3, os

db_path = os.path.join('backend', 'db', 'newsroom.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables)

if 'sources' in tables:
    cur.execute("SELECT * FROM sources LIMIT 30")
    rows = cur.fetchall()
    print("\nSources:", rows)
    for row in rows:
        print(" ", row)

conn.close()
