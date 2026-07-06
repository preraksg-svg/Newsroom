import sqlite3
import re

def clean_titles():
    conn = sqlite3.connect('newsroom.db')
    cur = conn.cursor()
    cur.execute("SELECT id, title FROM stories")
    rows = cur.fetchall()
    
    count = 0
    for r in rows:
        story_id, title = r
        if re.search(r'\s*\[[a-fA-F0-9]{4}\]$', title):
            new_title = re.sub(r'\s*\[[a-fA-F0-9]{4}\]$', '', title)
            cur.execute("UPDATE stories SET title=? WHERE id=?", (new_title, story_id))
            count += 1
            
    conn.commit()
    conn.close()
    print(f"Cleaned {count} titles in database.")

if __name__ == "__main__":
    clean_titles()
