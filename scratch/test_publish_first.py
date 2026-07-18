import sqlite3
import requests
import time
import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 1. Fetch first draft ID
conn = sqlite3.connect('newsroom.db')
cur = conn.cursor()
cur.execute("SELECT id, title, url FROM stories WHERE status = 'Draft' ORDER BY created_at DESC LIMIT 1")
row = cur.fetchone()
conn.close()

if not row:
    print("No draft articles found in the database.")
    sys.exit(0)

article_id, title, url = row
print(f"Testing publishing on draft article:")
print(f"ID: {article_id}")
print(f"Title: {title}")
print(f"URL: {url}")

# 2. POST to local action API
payload = {
    "action": "publish_article",
    "article_id": article_id
}

print(f"\nSending action request to local API...")
try:
    res = requests.post("http://localhost:8000/api/action", json=payload, timeout=10)
    print(res.json())
except Exception as e:
    print("API call failed:", e)
    sys.exit(1)

# 3. Poll log status
print("\nPolling publishing status logs...")
for _ in range(30):
    time.sleep(2)
    try:
        log_res = requests.get(f"http://localhost:8000/api/publish-log/{article_id}", timeout=5)
        log_data = log_res.json()
        print(f"\n--- LOG UPDATE ({time.strftime('%H:%M:%S')}) ---")
        print(f"Status: {log_data.get('status')}")
        print(f"Task ID: {log_data.get('task_id')}")
        
        logs = log_data.get("logs", [])
        for log in logs[-5:]:
            print(f"  {log}")
            
        if log_data.get('status') in ['completed', 'success', 'failed']:
            print(f"\nPublishing completed with status: {log_data.get('status')}")
            break
    except Exception as e:
        print("Polling failed:", e)
