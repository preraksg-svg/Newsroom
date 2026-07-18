import sqlite3
conn = sqlite3.connect('newsroom.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, title, url, news_type FROM stories WHERE status = 'Draft' ORDER BY id DESC LIMIT 10")
for row in cur.fetchall():
    print(dict(row))
conn.close()
