import sys
import os
import sqlite3
import requests

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.llm import filter_article, generate_social_post

def run_diagnostics():
    print("=== ZapwayNewsroom System Diagnostics ===")
    
    # 1. Check Database
    print("\n1. Checking Database Connectivity...")
    db_path = os.path.join(PROJECT_ROOT, "newsroom.db")
    if not os.path.exists(db_path):
        print(f"[FAIL] Database file not found at {db_path}")
    else:
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM stories")
            count = cur.fetchone()[0]
            print(f"[SUCCESS] Database accessible. {count} stories found.")
        except Exception as e:
            print(f"[FAIL] Database error: {e}")

    # 2. Check Groq API Key Fallback
    print("\n2. Testing LLM Gatekeeper Pipeline (Rate Limit check)...")
    try:
        res = filter_article("Tesla launches new EV", "Tesla has launched a new electric vehicle with 500 miles range.")
        if "relevant" in res:
            print(f"[SUCCESS] Gatekeeper returned valid JSON: {res}")
        else:
            print(f"[FAIL] Gatekeeper returned unexpected output: {res}")
    except Exception as e:
        print(f"[FAIL] Gatekeeper pipeline crashed: {e}")
        
    print("\n3. Testing LLM Social Generation Pipeline...")
    try:
        res = generate_social_post("Tesla releases update", "Software update adds new features", "http://example.com")
        if res:
            print(f"[SUCCESS] Generation successful.")
        else:
            print(f"[FAIL] Generation returned empty output.")
    except Exception as e:
        print(f"[FAIL] Generation pipeline crashed: {e}")

if __name__ == "__main__":
    run_diagnostics()
