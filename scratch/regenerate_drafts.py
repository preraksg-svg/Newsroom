import sqlite3
import asyncio
import json
import os
import sys

# Configure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Include project root in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from layer3_generation.generation_fanout import run_microtask_a_with_retry
from backend.db import queries

async def regenerate_all_drafts():
    conn = sqlite3.connect('newsroom.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("SELECT id, url, title, original_content FROM stories WHERE status = 'Draft'")
    drafts = cur.fetchall()
    print(f"[REGEN] Found {len(drafts)} drafts to regenerate.")
    
    for idx, row in enumerate(drafts):
        story_id = row['id']
        url = row['url']
        title = row['title']
        content = row['original_content']
        
        # Reconstruct JSON structured content if applicable
        if isinstance(content, str) and content.strip().startswith('['):
            try:
                structured = json.loads(content)
                if isinstance(structured, list):
                    reconstructed = []
                    for item in structured:
                        if isinstance(item, dict):
                            tag = item.get("tag", "p")
                            text = item.get("text", "")
                            if tag in ["h1", "h2"]:
                                reconstructed.append(f"## {text}")
                            elif tag == "h3":
                                reconstructed.append(f"### {text}")
                            elif tag == "li":
                                reconstructed.append(f"* {text}")
                            else:
                                reconstructed.append(text)
                    content = "\n\n".join(reconstructed)
            except Exception:
                pass
        
        print(f"\n[REGEN] ({idx+1}/{len(drafts)}) Regenerating: {title[:50]}...")
        try:
            # Re-run LLM generation using the updated rules
            updated_payload = await run_microtask_a_with_retry(
                content=content,
                url=url,
                title=title
            )
            
            if updated_payload and isinstance(updated_payload, dict):
                sections = json.dumps(updated_payload.get("sections", []))
                
                # Format images
                raw_imgs = updated_payload.get("images", [])
                img_urls = []
                for item in raw_imgs:
                    if isinstance(item, dict) and item.get("url"):
                        img_urls.append(item.get("url"))
                    elif isinstance(item, str):
                        img_urls.append(item)
                images = json.dumps(img_urls)
                
                meta_title = updated_payload.get("meta_title", title)
                meta_desc = updated_payload.get("meta_description", updated_payload.get("meta_desc", ""))
                keywords = json.dumps(updated_payload.get("keywords", []))
                
                # Update database
                cur.execute("""
                    UPDATE stories 
                    SET sections = ?, images = ?, meta_title = ?, meta_desc = ?, keywords = ?, original_content = ?
                    WHERE id = ?
                """, (sections, images, meta_title, meta_desc, keywords, content, story_id))
                conn.commit()
                print(f"[REGEN] Successfully updated story ID: {story_id}")
            else:
                print(f"[REGEN] WARNING: Generation returned invalid payload for {story_id}")
        except Exception as e:
            print(f"[REGEN] ERROR regenerating story ID {story_id}: {e}")
            
    conn.close()
    print("\n[REGEN] Completed regeneration of all drafts!")

if __name__ == "__main__":
    asyncio.run(regenerate_all_drafts())
