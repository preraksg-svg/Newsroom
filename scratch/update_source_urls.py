import sqlite3

updates = {
    "baaz_bikes_network": "https://www.baaz.bike/",
    "aarya_automobiles": "https://aaryaautomobile.com",
    "strikeco_electric_3w": "https://strikeco.co.in",
    "altmin_materials": "https://www.altmin.in",
    "himadri_chemicals": "https://www.himadri.com",
    "adani_total_emobility": "https://www.adanitotalgas.com",
    "newsapi_global": "https://newsapi.org",
    "newsapi_india": "https://newsapi.org",
    "newsdata_global": "https://newsdata.io",
    "newsdata_india": "https://newsdata.io",
    "gnews_global": "https://gnews.io",
    "gnews_india": "https://gnews.io"
}

conn = sqlite3.connect('newsroom.db')
cur = conn.cursor()

for source_id, new_domain in updates.items():
    cur.execute("UPDATE source_scores SET domain = ? WHERE source_id = ?", (new_domain, source_id))
    print(f"Updated {source_id} -> {new_domain} (Rows affected: {cur.rowcount})")

conn.commit()
conn.close()
print("Source URL updates completed.")
