import sqlite3
conn = sqlite3.connect('newsroom.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, title, original_content, sections FROM stories WHERE id = 'rec_1783855892082'")
row = cur.fetchone()
if row:
    print("ID:", row['id'])
    print("TITLE:", row['title'])
    print("SECTIONS:", row['sections'])
    print("ORIGINAL CONTENT:\n", row['original_content'])
conn.close()
