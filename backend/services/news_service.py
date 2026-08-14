import json
import os
import asyncio
from datetime import datetime, timezone
from backend.db import queries
from backend.llm import generate_ai_summary, rewrite_article
from backend.db.queries import log_groq_usage
from backend.headline_engine import generate_headline_variations
from backend.thumbnail_engine import generate_thumbnail_prompts, mock_generate_images
from backend.social_engine import generate_viral_bundle
import gtts

from backend.db.queries import add_task

# Global dict to track real-time Playwright publisher status per article
PUBLISH_LOGS: dict = {}

class NewsService:
    @staticmethod
    def _parse_item(item):
        """Helper to parse JSON fields from DB into objects."""
        for field in ['sections', 'images', 'audio', 'ai_summary']:
            val = item.get(field)
            if isinstance(val, str) and val.strip():
                try:
                    item[field] = json.loads(val)
                except:
                    # Fallback for raw strings (like old audio path)
                    if field == 'audio' and val.startswith('/static'):
                        item[field] = {"url": val}
                    elif field in ['sections', 'images']:
                        item[field] = []
                    else:
                        item[field] = {}
            elif val is None:
                item[field] = [] if field in ['sections', 'images'] else {}
                
        # Reconstruct original content if it is JSON structured content
        orig = item.get("original_content")
        if isinstance(orig, str) and orig.strip().startswith('['):
            try:
                import json as _json
                structured = _json.loads(orig)
                if isinstance(structured, list):
                    reconstructed = []
                    for s_item in structured:
                        if isinstance(s_item, dict):
                            tag = s_item.get("tag", "p")
                            text = s_item.get("text", "")
                            if tag in ["h1", "h2"]:
                                reconstructed.append(f"## {text}")
                            elif tag == "h3":
                                reconstructed.append(f"### {text}")
                            elif tag == "li":
                                reconstructed.append(f"* {text}")
                            elif tag == "table":
                                reconstructed.append(text)
                            else:
                                reconstructed.append(text)
                    item["original_content"] = "\n\n".join(reconstructed)
            except Exception:
                pass
                
        # Table fallback injection mechanism
        orig_content = item.get("original_content") or ""
        sections = item.get("sections") or []
        if isinstance(sections, list) and sections and isinstance(orig_content, str):
            has_table_in_sections = any('|' in str(s.get('content', '')) and '---' in str(s.get('content', '')) for s in sections)
            if not has_table_in_sections and '|' in orig_content and '---' in orig_content:
                import re as _re
                # Match consecutive lines starting and ending with |
                table_pattern = _re.compile(r'((?:^\|[^\n]+\|\r?\n?)+)', _re.MULTILINE)
                table_matches = table_pattern.findall(orig_content)
                if table_matches:
                    table_md = "\n\n" + table_matches[0].strip() + "\n\n"
                    # Append table to the last section's content
                    last_sec = sections[-1]
                    if isinstance(last_sec, dict):
                        last_sec['content'] = (last_sec.get('content') or "") + table_md
                        item["sections"] = sections
                        
        return item

    @staticmethod
    def get_news(status=None, search=None, limit=100, page=1):
        offset = (page - 1) * limit
        items = queries.fetch_all_news(status, search, limit, offset)
        total = queries.fetch_news_count(status, search)
        
        formatted = []
        for item in items:
            item = NewsService._parse_item(item)
            formatted.append({
                "id": item['id'],
                "createdTime": item['created_at'],
                "fields": {
                    "title": item['title'],
                    "status": item['status'],
                    "publisher": item['publisher'],
                    "final_score": item['final_score'],
                    "ai_summary": item['ai_summary'],
                    "sections": item['sections'],
                    "images": item['images'],
                    "audio": item['audio']
                }
            })
        return {"items": formatted, "total": total}

    @staticmethod
    def get_article(article_id):
        article = queries.fetch_story_by_id(article_id)
        if not article:
            raise Exception("Article not found")
        item = NewsService._parse_item(article)
        
        # On-the-fly dynamic image crawling fallback for existing articles
        if (not item.get("images") or len(item["images"]) == 0) and item.get("url"):
            try:
                from zapway_publisher import fetch_all_image_urls
                img_urls = fetch_all_image_urls(item["url"])
                if img_urls:
                    item["images"] = img_urls
                    # Persist it to DB so we don't have to crawl again
                    queries.update_story(article_id, "images", json.dumps(img_urls))
            except Exception as e:
                print(f"[DYNAMIC IMAGE] Failed to crawl: {e}")
                
        return item


    @staticmethod
    def update_article(article_id, data):
        # Safe mapping from frontend keys to database columns
        FIELD_MAP = {
            "title": "title",
            "status": "status",
            "publisher": "publisher",
            "original_content": "original_content",
            "sections": "sections",
            "images": "images",
            "audio": "audio",
            "meta_title": "meta_title",
            "meta_desc": "meta_desc",
            "keywords": "keywords",
            "seo_strategy": "seo_strategy",
            "seo_faq": "seo_faq"
        }
        
        article = queries.fetch_story_by_id(article_id)
        is_already_published = article and article.get("status") == "Published"

        for key, value in data.items():
            db_key = FIELD_MAP.get(key)
            if not db_key:
                continue # Skip unauthorized or unknown fields
                
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            queries.update_story(article_id, db_key, value)

        if is_already_published:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(NewsService.handle_action("publish_article", article_id))
            except RuntimeError:
                pass
        return True

    @staticmethod
    async def handle_action(action, article_id, params=None, internal=False):
        params = params or {}
        article = queries.fetch_story_by_id(article_id)
        if not article: raise Exception("Article not found")

        if action == "generate_summary":
            summary = generate_ai_summary(article['title'], article['original_content'])
            queries.update_story(article_id, "ai_summary", json.dumps(summary))
            return {"ai_summary": summary}

        elif action == "regenerate_headlines":
            variants = generate_headline_variations(article['title'], article['original_content'])
            queries.update_story(article_id, "headline_variants", json.dumps(variants))
            return {"variants": variants}

        elif action == "generate_thumbnails" or action == "generate_images":
            if internal:
                try:
                    prompts = generate_thumbnail_prompts(article['title'], article['original_content'])
                    images = mock_generate_images(prompts)
                    queries.update_story(article_id, "images", json.dumps(images))
                    return {"images": images}
                except Exception as e:
                    return {"error": f"Thumbnail generation failed: {str(e)}"}
            else:
                task_id = queries.add_task("image", article_id)
                return {"status": "queued", "task_id": task_id}

        elif action == "generate_audio":
            if internal:
                try:
                    text = f"{article['title']}. {article['original_content'][:500]}"
                    # Use absolute path relative to this file
                    static_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../static"))
                    audio_dir = os.path.join(static_root, "audio")
                    os.makedirs(audio_dir, exist_ok=True)
                    
                    path = os.path.join(audio_dir, f"{article_id}.mp3")
                    def create_tts():
                        import gtts
                        tts = gtts.gTTS(text)
                        tts.save(path)
                    await asyncio.to_thread(create_tts)
                    audio_data = {"url": f"/static/audio/{article_id}.mp3"}
                    queries.update_story(article_id, "audio", json.dumps(audio_data))
                    return {"audio": audio_data}
                except Exception as e:
                    return {"error": f"Audio generation failed: {str(e)}"}
            else:
                task_id = queries.add_task("audio", article_id)
                return {"status": "queued", "task_id": task_id}

        elif action == "generate_social":
            try:
                bundle = generate_viral_bundle(article['title'], article['original_content'])
                queries.update_story(article_id, "social_bundle", json.dumps(bundle))
                return {"social_bundle": bundle}
            except Exception as e:
                return {"error": f"Social bundle generation failed: {str(e)}"}

        elif action == "get_raw_source":
            raw = queries.get_raw_signal(article_id) if hasattr(queries, 'get_raw_signal') else {"content": article['original_content']}
            return {"raw_content": raw}

        elif action == "reject_article":
            queries.update_story(article_id, "status", "Rejected")
            return {"status": "Rejected"}

        elif action == "revert_to_draft":
            queries.update_story(article_id, "status", "Draft")
            return {"status": "Draft"}

        elif action == "approve_article":
            queries.update_story(article_id, "status", "Approved")
            return {"status": "Approved"}

        elif action == "publish_article":
            now_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            # Mark as "Publishing" (in-progress) — do NOT mark Published until the
            # Playwright publish actually succeeds, so a failed publish never
            # falsely shows as Published and can be retried.
            queries.update_story(article_id, "status", "Publishing")
            queries.update_story(article_id, "error_message", "")

            # ── Auto-publish to zapway.app via Playwright ──────────────────
            import threading

            # Reset log for this article
            PUBLISH_LOGS[article_id] = [
                {"step": "init", "msg": "Starting Playwright automation...", "status": "running"}
            ]

            def _log(step, msg, status="running"):
                PUBLISH_LOGS.setdefault(article_id, []).append({"step": step, "msg": msg, "status": status})
                print(f"[PUBLISHER] {msg}")

            def _run_playwright_publisher(article_data):
                """Run Playwright publisher in a background thread with its own event
                loop. Retries once on failure to absorb transient slow-render /
                network hiccups on the constrained free-tier browser."""
                from zapway_publisher import publish_to_zapway
                result = None
                max_attempts = 2
                for attempt in range(1, max_attempts + 1):
                    try:
                        _log("browser", f"Launching headless browser (attempt {attempt}/{max_attempts})...")
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        _log("navigate", "Navigating to zapway.app/News/insert_news...")
                        result = loop.run_until_complete(publish_to_zapway(article_data))
                        loop.close()
                    except Exception as e:
                        result = {"success": False, "error": str(e)}
                    if result and result.get("success"):
                        break
                    if attempt < max_attempts:
                        _log("retry", f"Attempt {attempt} failed ({str(result.get('error'))[:70]}). Retrying...", "running")

                if result and result.get("success"):
                    # Only NOW mark it truly published.
                    queries.update_story(article_id, "status", "Published")
                    queries.update_story(article_id, "published_date", now_str)
                    if result.get("final_url"):
                        queries.update_story(article_id, "wp_url", result.get("final_url"))
                    _log("done", f"✅ Successfully published to zapway.app!", "success")

                    # Auto-share to X/Twitter (no-op if X creds not configured).
                    try:
                        from x_publisher import post_to_x, build_caption
                        share_url = result.get("final_url") or article_data.get("url") or ""
                        caption = build_caption(
                            article_data.get("title", ""),
                            article_data.get("meta_description", ""),
                        )
                        x_res = post_to_x(caption, url=share_url)
                        if x_res.get("success"):
                            _log("x", "✅ Shared to X/Twitter", "success")
                        elif not x_res.get("skipped"):
                            _log("x", f"⚠️ X share failed: {x_res.get('error')}", "running")
                    except Exception as xe:
                        _log("x", f"⚠️ X share error: {xe}", "running")
                else:
                    # Revert to Draft so the failure is visible and retryable.
                    err = str(result.get("error")) if result else "Unknown error"
                    queries.update_story(article_id, "status", "Draft")
                    queries.update_story(article_id, "error_message", err[:500])
                    _log("error", f"❌ Failed after {max_attempts} attempts: {err}", "error")

            # Build article dict with all fields needed by the publisher
            import json as _json
            raw_sections = article.get("sections")
            sections_list = []
            if isinstance(raw_sections, str) and raw_sections.strip():
                try:
                    sections_list = _json.loads(raw_sections)
                except Exception:
                    pass
            elif isinstance(raw_sections, list):
                sections_list = raw_sections

            raw_images = article.get("images")
            images_list = []
            if isinstance(raw_images, str) and raw_images.strip():
                try:
                    images_list = _json.loads(raw_images)
                except Exception:
                    pass
            elif isinstance(raw_images, list):
                images_list = raw_images

            article_data = {
                "title": article.get("title", ""),
                "sections": sections_list,
                "original_content": article.get("original_content", ""),
                "ai_summary": article.get("ai_summary", ""),
                "meta_title": article.get("meta_title", ""),
                "meta_description": article.get("meta_desc", article.get("meta_description", "")),
                "keywords": article.get("keywords", []),
                "source": article.get("source", "Zapway Newsroom"),
                "url": article.get("url", ""),
                "images": images_list,
            }


            t = threading.Thread(target=_run_playwright_publisher, args=(article_data,), daemon=True)
            t.start()
            print(f"[PUBLISHER] Background publish thread started for article {article_id}")

            return {"status": "Publishing", "published_at": now_str, "message": "Publishing in progress — status updates to Published on success."}


        elif action == "calculate_score":
            # Simple heuristic for the backend: based on title length and content presence
            title_score = min(len(article['title']) / 50.0 * 100, 100)
            content_score = 100 if article['original_content'] else 0
            final_score = (title_score + content_score) / 2
            queries.update_story(article_id, "final_score", final_score)
            return {"final_score": final_score}

        elif action == "select_headline":
            selected = params.get("selected") or params.get("headline")
            if selected:
                queries.update_story(article_id, "title", selected)
                return {"title": selected}
            return {"error": "Missing selected headline in params"}

        elif action == "select_thumbnail":
            selected = params.get("selected") or params.get("image_url")
            if selected:
                # Store as a list of URL strings for frontend compatibility
                queries.update_story(article_id, "images", json.dumps([selected]))
                return {"images": [selected]}
            return {"error": "Missing selected thumbnail in params"}

        else:
            raise Exception(f"Unknown action: {action}")

    @staticmethod
    def get_raw_source(article_id):
        raw = queries.get_raw_signal(article_id)
        return {"content": raw}

    @staticmethod
    def get_rejected():
        return NewsService.get_news(status="Rejected")

    @staticmethod
    def restore_article(article_id):
        queries.update_story(article_id, "status", "Draft")
        return True

class AnalyticsService:
    @staticmethod
    def get_groq_usage():
        used = queries.fetch_groq_usage()
        limit = 500000
        return {
            "used": used,
            "limit": limit,
            "percentage": (used / limit) * 100 if limit > 0 else 0
        }

class IntelligenceService:
    @staticmethod
    def get_sources():
        sources = queries.fetch_sources()
        # ID normalization is already handled in queries.fetch_sources()
        return sources
