import sqlite3
import json

conn = sqlite3.connect('newsroom.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT id, title, url, images, sections, original_content FROM stories ORDER BY created_at DESC LIMIT 3")
rows = cur.fetchall()

for row in rows:
    print(f"\nSTORY ID: {row['id']}")
    print(f"TITLE: {row['title']}")
    print(f"URL: {row['url']}")
    print(f"IMAGES: {row['images']}")
    print(f"SECTIONS: {row['sections'][:400]}...")
    print(f"ORIGINAL CONTENT LENGTH: {len(row['original_content']) if row['original_content'] else 0}")
    if row['original_content']:
        print(f"ORIGINAL CONTENT SAMPLE:\n{row['original_content'][:500]}\n")

conn.close()
