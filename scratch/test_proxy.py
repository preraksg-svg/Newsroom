import sqlite3
import requests

conn = sqlite3.connect('newsroom.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, title, url FROM stories WHERE status = 'Draft'")
rows = cur.fetchall()
conn.close()

for r in rows[:5]:
    url = r['url']
    print(f"\nChecking proxy for story: {r['title']} ({r['id']})")
    print(f"URL: {url}")
    proxy_test_url = f"http://localhost:8000/api/proxy?url={url}"
    try:
        res = requests.get(proxy_test_url, timeout=10)
        print(f"Proxy Status Code: {res.status_code}")
        print(f"Response preview: {res.text[:200]}...")
    except Exception as e:
        print(f"Failed to fetch proxy: {e}")
