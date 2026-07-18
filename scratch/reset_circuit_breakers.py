"""
Emergency reset: clear all open circuit breakers and reset failure counts.
Run this whenever scraping stops.
"""
import sqlite3, os, json, time

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'newsroom.db')
CB_PATH = os.path.join(os.path.dirname(__file__), 'circuit_breakers.json')

# 1. Reset all failure counts in DB
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("UPDATE source_scores SET failure_count=0, fetch_status='success' WHERE activity_status='active'")
conn.commit()
changed = cur.rowcount
print(f"[RESET] Cleared failure counts for {changed} active sources in DB.")
conn.close()

# 2. Clear the circuit_breakers.json file entirely
if os.path.exists(CB_PATH):
    with open(CB_PATH, 'w') as f:
        json.dump({}, f)
    print(f"[RESET] Cleared all circuit breakers from {CB_PATH}")
else:
    print(f"[RESET] No circuit_breakers.json to clear.")

print("[RESET] Done. All sources are now unblocked.")
