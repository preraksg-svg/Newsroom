import sqlite3
conn = sqlite3.connect('newsroom.db')
cur = conn.cursor()

# Check statuses
cur.execute("SELECT status, count(*) FROM stories GROUP BY status")
rows = cur.fetchall()
print("Stories by status:")
for r in rows:
    print(f"  {r[0]!r}: {r[1]}")

# Check recent raw signals
cur.execute("SELECT count(*) FROM scraped_raw")
print("\nTotal raw signals:", cur.fetchone()[0])
cur.execute("SELECT count(*) FROM scraped_raw WHERE clustered=0")
print("Unprocessed raw signals:", cur.fetchone()[0])

# Check recent stories  
cur.execute("SELECT id, title, status, created_at FROM stories ORDER BY created_at DESC LIMIT 5")
print("\nRecent 5 stories:")
for r in cur.fetchall():
    print(f"  [{r[2]}] {r[1][:60] if r[1] else 'NO TITLE'}")

conn.close()
