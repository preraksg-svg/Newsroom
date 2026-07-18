import json
import os

health_file = "static/sources_health.json"
if os.path.exists(health_file):
    with open(health_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    print("Offline sources:")
    for s in data["sources"]:
        if s["status"] == "Offline":
            print(f"- {s['source_id']}: {s['name']} ({s['url']}) -> {s['error']}")
else:
    print("Health file does not exist.")
