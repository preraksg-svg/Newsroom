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
                from zapway_publisher import fetch_main_image_url
                img_url = fetch_main_image_url(item["url"])
                if img_url:
                    item["images"] = [img_url]
                    # Persist it to DB so we don't have to crawl again
                    queries.update_story(article_id, "images", json.dumps([img_url]))
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
        
        for key, value in data.items():
            db_key = FIELD_MAP.get(key)
            if not db_key:
                continue # Skip unauthorized or unknown fields
                
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            queries.update_story(article_id, db_key, value)
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

        elif action == "approve_article":
            queries.update_story(article_id, "status", "Approved")
            return {"status": "Approved"}

        elif action == "publish_article":
            now_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            queries.update_story(article_id, "status", "Published")
            queries.update_story(article_id, "published_date", now_str)

            # ── Auto-publish to zapway.app via Playwright ──────────────────
            import asyncio
            import threading

            # Reset log for this article
            PUBLISH_LOGS[article_id] = [
                {"step": "init", "msg": "Starting Playwright automation...", "status": "running"}
            ]

            def _log(step, msg, status="running"):
                PUBLISH_LOGS.setdefault(article_id, []).append({"step": step, "msg": msg, "status": status})
                print(f"[PUBLISHER] {msg}")

            def _run_playwright_publisher(article_data):
                """Run Playwright publisher in a background thread with its own event loop."""
                try:
                    _log("browser", "Launching headless browser...")
                    from zapway_publisher import publish_to_zapway
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    _log("navigate", "Navigating to zapway.app/News/insert_news...")
                    result = loop.run_until_complete(publish_to_zapway(article_data))
                    loop.close()
                    if result.get("success"):
                        _log("done", f"✅ Successfully published to zapway.app!", "success")
                    else:
                        _log("error", f"❌ Failed: {result.get('error')}", "error")
                except Exception as e:
                    _log("error", f"❌ Exception: {str(e)}", "error")

            # Build article dict with all fields needed by the publisher
            article_data = {
                "title": article.get("title", ""),
                "sections": article.get("sections", []),
                "original_content": article.get("original_content", ""),
                "ai_summary": article.get("ai_summary", ""),
                "meta_title": article.get("meta_title", ""),
                "meta_description": article.get("meta_desc", article.get("meta_description", "")),
                "keywords": article.get("keywords", []),
                "source": article.get("source", "Zapway Newsroom"),
                "url": article.get("url", ""),
            }

            t = threading.Thread(target=_run_playwright_publisher, args=(article_data,), daemon=True)
            t.start()
            print(f"[PUBLISHER] Background publish thread started for article {article_id}")

            return {"status": "Published", "published_at": now_str}


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

    @staticmethod
    def get_seo_overview():
        stories = queries.fetch_seo_overview()
        keyword_items = []
        for s in stories:
            # Assuming keywords is a comma-separated string or JSON list
            raw_kws = s.get('keywords')
            if not raw_kws: continue
            
            if isinstance(raw_kws, str):
                try:
                    kw_list = json.loads(raw_kws)
                except:
                    kw_list = [k.strip() for k in raw_kws.split(',')]
            else:
                kw_list = raw_kws
                
            for i, kw in enumerate(kw_list):
                keyword_items.append({
                    "keyword": kw,
                    "rank": 3 + i, # Mock rank data
                    "traffic": 1200 - (i * 100), # Mock traffic data
                    "article_id": s['id']
                })
                
        return {
            "keywords": keyword_items,
            "timeline": [30, 45, 60, 40, 70, 90, 80]
        }

    @staticmethod
    def get_experiments():
        data = queries.fetch_experiment_data()
        formatted = []
        for item in data:
            variants = json.loads(item['headline_variants']) if item['headline_variants'] else []
            # Map variants to expected structure: { text: string, ctr: number }
            variant_objs = [{"text": v, "ctr": 2.5 + (i * 0.5)} for i, v in enumerate(variants)]
            formatted.append({
                "article_id": item['id'],
                "title": item['title'],
                "variants": variant_objs,
                "winner": variants[0] if variants else None
            })
        return formatted

    @staticmethod
    def get_social_bundle(article_id):
        article = queries.fetch_story_by_id(article_id)
        if not article: raise Exception("Article not found")
        
        # 1. Try primary social_bundle column
        bundle_raw = article.get('social_bundle')
        bundle = {}
        if bundle_raw:
            try:
                bundle = json.loads(bundle_raw) if isinstance(bundle_raw, str) else bundle_raw
            except:
                bundle = {}

        # 2. Fallback to nested ai_summary.social_bundle if empty
        if not bundle or (not bundle.get('tweet') and not bundle.get('linkedin')):
            summary_raw = article.get('ai_summary')
            if summary_raw:
                try:
                    summary = json.loads(summary_raw) if isinstance(summary_raw, str) else summary_raw
                    if "social_bundle" in summary:
                        bundle = summary["social_bundle"]
                except:
                    pass

        # 3. Normalize structure for frontend (tweet.text, linkedin.body)
        if not isinstance(bundle, dict): bundle = {}
        
        # Handle string-based or legacy fields
        tweet = bundle.get("tweet") or {}
        if isinstance(tweet, str): tweet = {"text": tweet}
        
        linkedin = bundle.get("linkedin") or {}
        if isinstance(linkedin, str): linkedin = {"body": linkedin}

        return {
            "tweet": {"text": tweet.get("text", "")},
            "linkedin": {"body": linkedin.get("body", "")}
        }

class AnalyticsService:
    @staticmethod
    def get_global_stats():
        top_articles = queries.fetch_analytics()
        total_views = sum([a.get('traffic_total') or 0 for a in top_articles])
        avg_ctr = sum([a.get('ctr_avg') or 0 for a in top_articles]) / len(top_articles) if top_articles else 0
        return {
            "top_articles": top_articles,
            "total_views": total_views,
            "avg_ctr": avg_ctr,
            "timeline": [120, 450, 320, 580, 890, 1100, 950],
            "time_series": [120, 450, 320, 580, 890, 1100, 950]
        }

    @staticmethod
    def get_groq_usage():
        used = queries.fetch_groq_usage()
        limit = 500000
        return {
            "used": used,
            "limit": limit,
            "percentage": (used / limit) * 100 if limit > 0 else 0
        }

    @staticmethod
    def get_growth():
        signals = queries.fetch_growth_overview()
        return {"top_signals": signals}

class IntelligenceService:
    @staticmethod
    def get_sources():
        sources = queries.fetch_sources()
        # ID normalization is already handled in queries.fetch_sources()
        return sources
