import sqlite3
import json

conn = sqlite3.connect('newsroom.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT id, title, sections, original_content FROM stories WHERE status = 'Draft'")
rows = cur.fetchall()

for row in rows:
    print(f"\nSTORY ID: {row['id']}")
    print(f"TITLE: {row['title']}")
    
    sections = json.loads(row['sections']) if row['sections'] else []
    print(f"SECTIONS COUNT: {len(sections)}")
    for i, s in enumerate(sections):
        print(f"  Sec {i+1}: {s.get('heading') or s.get('title')}")
        
    # Check for markdown headers in original content
    orig = row['original_content'] or ""
    headers_in_orig = [line.strip() for line in orig.split('\n') if line.strip().startswith('##') or line.strip().startswith('###')]
    print(f"ORIGINAL HEADERS FOUND: {headers_in_orig}")
    
conn.close()
