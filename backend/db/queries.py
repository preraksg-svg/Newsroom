import sqlite3
import os
import time
import json
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), '../../newsroom.db')

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initializes the SQLite schema for the entire system."""
    with get_db() as conn:
        cur = conn.cursor()
        
        # Core Tables
        cur.execute('''
            CREATE TABLE IF NOT EXISTS stories (
                id TEXT PRIMARY KEY,
                url TEXT,
                title TEXT,
                original_content TEXT,
                sections TEXT,
                images TEXT,
                audio TEXT,
                meta_title TEXT,
                meta_desc TEXT,
                keywords TEXT,
                status TEXT DEFAULT 'Draft',
                publisher TEXT,
                published_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                final_score REAL DEFAULT 0.0,
                ai_summary TEXT DEFAULT '{}',
                headline_variants TEXT,
                social_bundle TEXT DEFAULT '{}',
                growth_score REAL DEFAULT 0.0,
                seo_strategy TEXT,
                seo_faq TEXT,
                wp_slug TEXT,
                wp_id TEXT,
                wp_url TEXT,
                error_message TEXT,
                news_type TEXT,
                score_credibility REAL,
                score_intelligence REAL,
                score_virality REAL,
                score_time REAL,
                score_relevance REAL,
                priority TEXT,
                decision_state TEXT
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY,
                name TEXT,
                domain TEXT,
                type TEXT,
                category TEXT,
                tier TEXT,
                score_authority REAL DEFAULT 0.5,
                score_accuracy REAL DEFAULT 0.5,
                score_speed REAL DEFAULT 0.5,
                score_engagement REAL DEFAULT 0.5,
                confidence_score REAL DEFAULT 0.5,
                india_relevance REAL DEFAULT 0.5,
                dynamic_score REAL DEFAULT 0.5,
                final_score REAL DEFAULT 0.5,
                activity_status TEXT DEFAULT 'active', 
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_fetch_time TIMESTAMP,
                fetch_status TEXT,
                fetch_count_last INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS scraped_raw (
                id TEXT PRIMARY KEY,
                title TEXT,
                content TEXT,
                url TEXT,
                source_id TEXT,
                source_type TEXT,
                author TEXT,
                timestamp TEXT,
                engagement_data TEXT,
                clustered INTEGER DEFAULT 0
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS groq_usage (
                date_str TEXT PRIMARY KEY,
                total_tokens INTEGER DEFAULT 0
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS growth_metrics (
                story_id TEXT PRIMARY KEY,
                traffic_total INTEGER DEFAULT 0,
                ctr_avg REAL DEFAULT 0.0,
                shares_total INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0.0,
                growth_score REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                task_type TEXT,
                article_id TEXT,
                params TEXT,
                status TEXT DEFAULT 'pending',
                retry_count INTEGER DEFAULT 0,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS yt_memory (
                channel_id TEXT PRIMARY KEY,
                last_video_id TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS source_performance (
                story_id TEXT PRIMARY KEY,
                views INTEGER DEFAULT 0,
                ctr REAL DEFAULT 0.0,
                engagement REAL DEFAULT 0.0,
                read_time REAL DEFAULT 0.0
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS edit_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT,
                snapshot_data TEXT,
                version INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS social_campaigns (
                campaign_id TEXT PRIMARY KEY,
                story_id TEXT,
                platform TEXT,
                hook TEXT,
                caption TEXT,
                expected_ctr REAL,
                priority_score REAL,
                distribution_logic TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS social_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT,
                clicks INTEGER DEFAULT 0,
                impressions INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS pattern_memory (
                pattern_id TEXT PRIMARY KEY,
                type TEXT,
                pattern TEXT,
                source TEXT,
                score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS learning_predictions (
                id TEXT PRIMARY KEY,
                story_id TEXT,
                feature_vector TEXT,
                predicted_engagement REAL,
                actual_reward REAL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS model_weights (
                feature TEXT PRIMARY KEY,
                weight REAL
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS system_locks (
                lock_name TEXT PRIMARY KEY,
                is_locked INTEGER DEFAULT 0,
                locked_at TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS discovered_sources (
                domain TEXT PRIMARY KEY,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                validation_score REAL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                frequency_count INTEGER DEFAULT 1
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS seo_pages (
                id TEXT PRIMARY KEY,
                type TEXT,
                slug TEXT UNIQUE,
                title TEXT,
                content TEXT,
                meta_tags TEXT,
                keywords TEXT,
                internal_links TEXT,
                faq_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS worker_memory (
                source_id TEXT PRIMARY KEY,
                total_ingested INTEGER DEFAULT 0,
                total_selected INTEGER DEFAULT 0,
                total_ignored INTEGER DEFAULT 0,
                total_high_perf INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.5,
                avg_engagement REAL DEFAULT 0.0,
                relevance_score REAL DEFAULT 0.5,
                worker_score REAL DEFAULT 0.5,
                poll_interval_multiplier REAL DEFAULT 1.0,
                last_50_performance TEXT DEFAULT '[]',
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS trend_memory (
                topic TEXT PRIMARY KEY,
                signal_count INTEGER DEFAULT 0,
                velocity REAL DEFAULT 0.0,
                is_active INTEGER DEFAULT 1,
                last_signal TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS topic_clusters (
                topic TEXT PRIMARY KEY,
                avg_performance REAL DEFAULT 0.0,
                article_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS growth_patterns (
                id TEXT PRIMARY KEY,
                keyword TEXT,
                platform TEXT,
                performance_score REAL,
                trend_status TEXT,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                event_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Robust Column Additions (Migrations)
        cols_to_add = [
            ("stories", "headline_variants", "TEXT"),
            ("stories", "social_bundle", "TEXT DEFAULT '{}'"),
            ("stories", "growth_score", "REAL DEFAULT 0.0"),
            ("stories", "seo_strategy", "TEXT"),
            ("stories", "seo_faq", "TEXT"),
            ("stories", "wp_slug", "TEXT"),
            ("stories", "wp_id", "TEXT"),
            ("stories", "wp_url", "TEXT"),
            ("stories", "error_message", "TEXT"),
            ("stories", "news_type", "TEXT"),
            ("stories", "score_credibility", "REAL"),
            ("stories", "score_intelligence", "REAL"),
            ("stories", "score_virality", "REAL"),
            ("stories", "score_time", "REAL"),
            ("stories", "score_relevance", "REAL"),
            ("stories", "priority", "TEXT"),
            ("stories", "decision_state", "TEXT"),
            ("sources", "country", "TEXT DEFAULT 'IN'"),
            ("sources", "access_method", "TEXT DEFAULT 'Playwright'")
        ]
        
        for table, col, col_type in cols_to_add:
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass 

        conn.commit()
        migrate_social_bundles()
    print(f"[DB] Initialization complete at {DB_PATH}")

def is_duplicate(url, title):
    """Check if a story already exists in the database."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM stories WHERE url = ? LIMIT 1", (url,))
        return cur.fetchone() is not None

# --- STORY QUERIES ---

def fetch_all_news(status=None, search=None, limit=100, offset=0):
    with get_db() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM stories WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if search:
            query += " AND (title LIKE ? OR original_content LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]

def fetch_news_count(status=None, search=None):
    with get_db() as conn:
        cur = conn.cursor()
        query = "SELECT COUNT(*) as total FROM stories WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if search:
            query += " AND (title LIKE ? OR original_content LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        cur.execute(query, params)
        row = cur.fetchone()
        return row['total'] if row else 0

def fetch_story_by_id(story_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM stories WHERE id = ?", (story_id,))
        row = cur.fetchone()
        return dict(row) if row else None

VALID_STORY_COLUMNS = {
    'url', 'title', 'original_content', 'sections', 'images', 'audio',
    'meta_title', 'meta_desc', 'keywords', 'status', 'publisher',
    'published_date', 'final_score', 'ai_summary', 'headline_variants',
    'social_bundle', 'growth_score', 'seo_strategy', 'seo_faq',
    'wp_slug', 'wp_url', 'error_message', 'news_type', 'score_credibility',
    'score_intelligence', 'score_virality', 'score_time', 'score_relevance',
    'priority', 'decision_state'
}

def update_story(story_id, field, value):
    if field not in VALID_STORY_COLUMNS:
        raise ValueError(f"Invalid column name: {field}")
        
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE stories SET {field} = ? WHERE id = ?", (value, story_id))
        conn.commit()

def create_draft(url, title, original_content, meta_title, meta_desc, keywords, publisher, published_date, scores_dict=None, seo_strategy=None, seo_faq=None):
    """Worker-level helper to create a new story draft."""
    with get_db() as conn:
        cur = conn.cursor()
        # Check for duplicates by URL, title, or original content
        if "zapway.in/intelligence" not in url:
            cur.execute("SELECT id FROM stories WHERE url = ? OR title = ? OR original_content = ? LIMIT 1", (url, title, original_content))
            if cur.fetchone():
                return None
            
        # Check for fuzzy title similarity within the last 48 hours
        if "zapway.in/intelligence" not in url:
            cur.execute("SELECT title FROM stories WHERE created_at >= datetime('now', '-48 hours')")
            existing_stories = cur.fetchall()
            from difflib import SequenceMatcher
            for row in existing_stories:
                existing_title = row['title']
                if existing_title:
                    ratio = SequenceMatcher(None, title.lower(), existing_title.lower()).ratio()
                    if ratio > 0.7:
                        return None
            
        record_id = "rec_" + str(int(time.time() * 1000))
        status = "Draft"
        
        # Defaults
        sections = json.dumps([])
        images = json.dumps([])
        audio = ""
        ai_summary = json.dumps({})
        social_bundle = json.dumps({})
        
        if scores_dict:
            status = "Draft"
            if "ai_summary" in scores_dict:
                ai_summary = json.dumps(scores_dict["ai_summary"])
            if "sections" in scores_dict:
                sections = json.dumps(scores_dict["sections"])
            if "social_bundle" in scores_dict:
                social_bundle = json.dumps(scores_dict["social_bundle"])

        cur.execute('''
            INSERT INTO stories (
                id, url, title, original_content, 
                meta_title, meta_desc, keywords, status, 
                publisher, published_date, sections, images, audio, ai_summary, social_bundle,
                final_score, score_credibility, score_intelligence, score_virality, score_time, score_relevance, seo_strategy, seo_faq
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record_id, url, title, original_content,
            meta_title, meta_desc, keywords, status,
            publisher, published_date, sections, images, audio, ai_summary, social_bundle,
            scores_dict.get('final_score', 0) if scores_dict else 0,
            scores_dict.get('credibility', 0) if scores_dict else 0,
            scores_dict.get('intelligence', 0) if scores_dict else 0,
            scores_dict.get('virality', 0) if scores_dict else 0,
            scores_dict.get('time', 0) if scores_dict else 0,
            scores_dict.get('relevance', 0) if scores_dict else 0,
            seo_strategy,
            seo_faq
        ))
        conn.commit()
        return record_id

def migrate_social_bundles():
    """Migrate nested social_bundle from ai_summary column to social_bundle column."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, ai_summary, social_bundle FROM stories")
        rows = cur.fetchall()
        for row in rows:
            story_id = row['id']
            ai_summary_raw = row['ai_summary']
            social_bundle_raw = row['social_bundle']
            
            # If social_bundle is empty or default, try to extract from ai_summary
            if not social_bundle_raw or social_bundle_raw == '{}' or social_bundle_raw == '[]':
                try:
                    summary = json.loads(ai_summary_raw) if ai_summary_raw else {}
                    if "social_bundle" in summary:
                        bundle = summary["social_bundle"]
                        # Normalize bundle shape
                        tweet = bundle.get("tweet") or ""
                        if isinstance(tweet, str): tweet = {"text": tweet}
                        
                        linkedin = bundle.get("linkedin") or ""
                        if isinstance(linkedin, str): linkedin = {"body": linkedin}
                        
                        normalized = {
                            "tweet": {"text": tweet.get("text", "")},
                            "linkedin": {"body": linkedin.get("body", "")}
                        }
                        cur.execute("UPDATE stories SET social_bundle = ? WHERE id = ?", (json.dumps(normalized), story_id))
                except:
                    pass
        conn.commit()

# --- SOURCE QUERIES ---

def fetch_sources():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM sources ORDER BY final_score DESC")
        results = []
        for r in cur.fetchall():
            d = dict(r)
            d['id'] = d.get('source_id') 
            results.append(d)
        return results

def log_source_fetch(source_id, status, count, error=None):
    """Update source health stats after a fetch attempt."""
    with get_db() as conn:
        cur = conn.cursor()
        if status == 'success' and count > 0:
            cur.execute('''
                UPDATE sources 
                SET last_fetch_time = CURRENT_TIMESTAMP,
                    fetch_status = 'success',
                    fetch_count_last = ?,
                    failure_count = 0,
                    activity_status = 'active'
                WHERE source_id = ?
            ''', (count, source_id))
        else:
            cur.execute('''
                UPDATE sources 
                SET last_fetch_time = CURRENT_TIMESTAMP,
                    fetch_status = ?,
                    fetch_count_last = 0,
                    failure_count = failure_count + 1
                WHERE source_id = ?
            ''', (status, source_id))
        
        cur.execute("UPDATE sources SET activity_status = 'inactive' WHERE failure_count > 10")
        conn.commit()

# --- ANALYTICS QUERIES ---

def fetch_analytics(story_id=None):
    with get_db() as conn:
        cur = conn.cursor()
        if story_id:
            cur.execute("SELECT * FROM growth_metrics WHERE story_id = ?", (story_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        else:
            cur.execute("""
                SELECT 
                    s.id, 
                    s.title, 
                    COALESCE(g.traffic_total, 0) AS traffic_total, 
                    COALESCE(g.ctr_avg, 0) AS ctr_avg, 
                    COALESCE(g.engagement_rate, 0) AS engagement_rate 
                FROM stories s 
                LEFT JOIN growth_metrics g ON s.id = g.story_id 
                ORDER BY g.traffic_total DESC LIMIT 20
            """)
            return [dict(r) for r in cur.fetchall()]

def log_groq_usage(tokens):
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO groq_usage (date_str, total_tokens) VALUES (?, 0)", (today_str,))
        cursor.execute("UPDATE groq_usage SET total_tokens = total_tokens + ? WHERE date_str = ?", (tokens, today_str))
        conn.commit()

def fetch_groq_usage():
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT total_tokens FROM groq_usage WHERE date_str = ?", (today,))
        row = cur.fetchone()
        return row[0] if row else 0

# --- WORKER SUPPORT ---

def get_raw_signal(story_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT content FROM scraped_raw WHERE id = ? OR url = (SELECT url FROM stories WHERE id = ?)", (story_id, story_id))
        row = cur.fetchone()
        return row[0] if row else None

def update_task_status(task_id, status, error_msg=None):
    with get_db() as conn:
        cur = conn.cursor()
        if error_msg:
            cur.execute("UPDATE tasks SET status = ?, error = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, error_msg, task_id))
        else:
            cur.execute("UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, task_id))
        conn.commit()

# --- YT MEMORY ---

def get_yt_memory(channel_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT last_video_id FROM yt_memory WHERE channel_id = ?", (channel_id,))
        row = cur.fetchone()
        return row['last_video_id'] if row else None

def update_yt_memory(channel_id, video_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO yt_memory (channel_id, last_video_id, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (channel_id, video_id))
        conn.commit()

# --- DASHBOARD SPECIFIC ---

def fetch_growth_overview():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                s.id, 
                s.title, 
                COALESCE(g.growth_score, 0) AS growth_score,
                COALESCE(g.traffic_total, 0) AS traffic_total, 
                COALESCE(g.ctr_avg, 0) AS ctr_avg, 
                COALESCE(g.shares_total, 0) AS shares_total, 
                COALESCE(g.engagement_rate, 0) AS engagement_rate 
            FROM stories s 
            LEFT JOIN growth_metrics g ON s.id = g.story_id 
            WHERE s.status = 'Published'
            ORDER BY g.traffic_total DESC
        """)
        return [dict(r) for r in cur.fetchall()]

def fetch_seo_overview():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, title, meta_title, meta_desc, keywords, seo_strategy FROM stories WHERE status IN ('Published', 'Draft')")
        return [dict(r) for r in cur.fetchall()]

def fetch_experiment_data():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, title, headline_variants, social_bundle FROM stories WHERE status IN ('Published', 'Draft') AND headline_variants IS NOT NULL")
        return [dict(r) for r in cur.fetchall()]

# --- TASK MANAGEMENT ---

def add_task(task_type, article_id, params=None):
    """Add a new task to the queue."""
    task_id = f"task_{int(time.time() * 1000)}"
    params_json = json.dumps(params) if params else "{}"
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO tasks (id, task_type, article_id, params, status)
            VALUES (?, ?, ?, ?, 'pending')
        ''', (task_id, task_type, article_id, params_json))
        conn.commit()
    return task_id

def get_next_pending_task():
    """Find the next pending task without claiming it."""
    from types import SimpleNamespace
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1")
        row = cur.fetchone()
        if not row: return None
        return SimpleNamespace(**dict(row))

def claim_next_task():
    """Atomically find and claim the next pending task."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1")
        task = cur.fetchone()
        if not task: return None
        
        task_id = task['id']
        update_task_status(task_id, "processing")
        return dict(task)

def update_task_status(task_id, status, error_msg=None):
    with get_db() as conn:
        cur = conn.cursor()
        if error_msg:
            cur.execute("UPDATE tasks SET status = ?, error = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, error_msg, task_id))
        else:
            cur.execute("UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, task_id))
        conn.commit()

def complete_task(task_id):
    update_task_status(task_id, "completed")

def fail_task(task_id, error_msg):
    update_task_status(task_id, "failed", error_msg)

def get_task(task_id):
    """Retrieve task details by ID."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cur.fetchone()
        return dict(row) if row else None

# --- ENGINE SUPPORT ---

def get_connection():
    """Direct SQLite connection for specialized engines."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def create_social_campaign(story_id, platform, hook, caption, expected_ctr, priority_score, distribution_logic):
    """Save a social media campaign for distribution."""
    campaign_id = f"cmp_{int(time.time() * 1000)}_{platform.lower()}"
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO social_campaigns (
                campaign_id, story_id, platform, hook, caption, 
                expected_ctr, priority_score, distribution_logic, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        ''', (campaign_id, story_id, platform, hook, caption, expected_ctr, priority_score, distribution_logic))
        conn.commit()
    return campaign_id
