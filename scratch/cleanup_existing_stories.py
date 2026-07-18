import sqlite3
import json
import os
import sys

sys.path.append(os.getcwd())

db_path = "newsroom.db"

layout_noise = [
    "top stories", "latest videos", "network18 updates", "recent posts", 
    "popular tags", "related content", "recommended stories", "trending", 
    "must read", "popular videos", "latest news", "overdrive sites", 
    "better photography", "better interiors", "moneycontrol", "firstpost", 
    "news18", "copyright", "follow the market", "follow us", "latest updates"
]

menu_keywords = [
    "find cars", "compare cars", "car reviews", "car photos", "car videos", "car brands", "just launched cars", "upcoming cars", "popular cars",
    "find bikes", "compare bikes", "bike reviews", "bike photos", "bike videos", "bike brands", "just launched bikes", "upcoming bikes", "popular bikes",
    "all reviews", "first drive", "road test", "comparo", "news & features", "opinions", "motorsport", "press releases", "all photos", "get app", "better photography"
]

def clean_sections():
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist locally.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, title, sections FROM stories")
    rows = cursor.fetchall()
    
    cleaned_count = 0
    for row in rows:
        story_id = row["id"]
        title = row["title"] or ""
        sections_raw = row["sections"]
        
        title_safe = title.encode('ascii', 'ignore').decode('ascii')
        
        if not sections_raw:
            continue
            
        try:
            sections = json.loads(sections_raw)
        except Exception as e:
            print(f"Failed to parse JSON for story {story_id}: {e}")
            continue
            
        if not isinstance(sections, list):
            continue
            
        original_sections_raw = json.dumps(sections)
        filtered_sections = []
        for sec in sections:
            heading = sec.get("heading", "") or ""
            heading_lower = heading.lower()
            if any(kw in heading_lower for kw in layout_noise):
                heading_safe = heading.encode('ascii', 'ignore').decode('ascii')
                print(f"[CLEANUP] Removing layout noise section '{heading_safe}' from story {story_id}: {title_safe}")
                continue
                
            content_text = sec.get("content", "") or ""
            content_lines = content_text.split('\n')
            filtered_lines = []
            for line in content_lines:
                line_lower = line.lower()
                if any(kw in line_lower for kw in menu_keywords) or (len(line.split()) <= 4 and any(kw in line_lower for kw in ["find", "compare", "reviews", "photos", "videos", "upcoming", "launched", "popular", "brands"])):
                    line_safe = line.encode('ascii', 'ignore').decode('ascii')
                    print(f"[CLEANUP] Removing menu text line '{line_safe}' from story {story_id}: {title_safe}")
                    continue
                filtered_lines.append(line)
            
            sec["content"] = "\n".join(filtered_lines)
            filtered_sections.append(sec)
            
        if json.dumps(filtered_sections) != original_sections_raw:
            cursor.execute(
                "UPDATE stories SET sections = ? WHERE id = ?",
                (json.dumps(filtered_sections), story_id)
            )
            cleaned_count += 1
            
    conn.commit()
    conn.close()
    print(f"\n[CLEANUP COMPLETED] Successfully cleaned {cleaned_count} existing stories.")

if __name__ == "__main__":
    clean_sections()
