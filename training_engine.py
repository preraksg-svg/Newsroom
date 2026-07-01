"""
ZAPWAY Real News Training System
=================================
Learns from every ingested article to improve generation quality.
- Parses articles into structured training data
- Extracts headline/structure/topic patterns
- Links patterns to performance metrics
- Feeds best patterns into LLM generation
- Validates generated content before saving
"""
import json
import time
import hashlib
import re
from backend.db.queries import get_db, get_connection


# ===============================================================
# TRAINING DATA TABLE
# ===============================================================

def init_training_tables():
    with get_db() as conn:
        cur = conn.cursor()

        cur.execute('''
            CREATE TABLE IF NOT EXISTS training_data (
                article_id TEXT PRIMARY KEY,
                title TEXT,
                structured_content TEXT,
                source TEXT,
                source_type TEXT,
                publish_time TEXT,
                topic TEXT,
                style_features TEXT,
                quality_tag TEXT DEFAULT 'untagged',
                pattern_score REAL DEFAULT 0.0,
                views INTEGER DEFAULT 0,
                ctr REAL DEFAULT 0.0,
                engagement REAL DEFAULT 0.0,
                read_time REAL DEFAULT 0.0,
                shares REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS headline_patterns (
                pattern_id TEXT PRIMARY KEY,
                pattern_type TEXT,
                template TEXT,
                keyword_positions TEXT,
                avg_length REAL,
                times_seen INTEGER DEFAULT 1,
                avg_score REAL DEFAULT 0.0,
                best_example TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS structure_patterns (
                pattern_id TEXT PRIMARY KEY,
                section_count INTEGER,
                section_flow TEXT,
                avg_word_count INTEGER,
                times_seen INTEGER DEFAULT 1,
                avg_score REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS topic_clusters (
                topic TEXT PRIMARY KEY,
                cluster TEXT,
                article_count INTEGER DEFAULT 1,
                avg_performance REAL DEFAULT 0.0,
                trending_velocity REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
    print("[TRAINING] Training tables initialized.")


# ===============================================================
# STEP 1: PARSE INTO STRUCTURED TRAINING DATA
# ===============================================================

TOPIC_KEYWORDS = {
    "Launch": ["launch", "unveil", "reveal", "introduce", "debut", "new model"],
    "Policy": ["subsidy", "policy", "regulation", "government", "tax", "incentive", "mandate"],
    "Tech": ["battery", "range", "charging speed", "motor", "autonomous", "software", "platform"],
    "Charging": ["charger", "charging station", "fast charge", "supercharger", "network", "infrastructure"],
    "Market": ["sales", "market share", "growth", "revenue", "stock", "investment", "valuation"],
    "Safety": ["recall", "crash", "safety", "accident", "investigation", "defect"],
}

HEADLINE_TYPES = {
    "product_action": r"(launches|unveils|reveals|introduces|debuts)",
    "policy_impact": r"(announces|approves|mandates|subsidizes|bans)",
    "data_insight": r"(\d+%|\d+ million|\d+ billion|record|surge|drop)",
    "question_hook": r"(why|how|what|will|can|should)\s",
    "comparison": r"(vs\.?|versus|compared|better than|beats)",
}


def classify_headline(title: str) -> dict:
    t = title.lower()
    for htype, pattern in HEADLINE_TYPES.items():
        if re.search(pattern, t, re.IGNORECASE):
            return {"headline_type": htype, "length": len(title.split()), "has_number": bool(re.search(r'\d', title))}
    return {"headline_type": "statement", "length": len(title.split()), "has_number": bool(re.search(r'\d', title))}


def classify_topic(title: str, content: str) -> str:
    text = (title + " " + content[:500]).lower()
    scores = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        scores[topic] = sum(1 for kw in keywords if kw in text)
    if max(scores.values()) == 0:
        return "General"
    return max(scores, key=scores.get)


def extract_style_features(title: str, sections: list, content: str) -> dict:
    word_count = len(content.split())
    headline_info = classify_headline(title)

    tone = "neutral"
    if any(w in title.lower() for w in ["breaking", "urgent", "massive", "shocking"]):
        tone = "urgent"
    elif any(w in title.lower() for w in ["analysis", "report", "study", "data"]):
        tone = "analytical"
    elif any(w in title.lower() for w in ["exclusive", "first look", "insider"]):
        tone = "exclusive"

    return {
        "headline_type": headline_info["headline_type"],
        "headline_length": headline_info["length"],
        "has_number_in_headline": headline_info["has_number"],
        "section_count": len(sections),
        "word_count": word_count,
        "tone": tone,
        "section_flow": [s.get("heading", s.get("name", "")) for s in sections[:6]]
    }


def store_training_data(article_id: str, title: str, content: str,
                        sections: list, source: str, source_type: str = ""):
    """Parse and store every ingested article as training data."""
    topic = classify_topic(title, content)
    style = extract_style_features(title, sections, content)

    structured = {
        "title": title,
        "sections": [{"heading": s.get("heading", s.get("name", "")),
                       "content": s.get("content", "")[:500]} for s in sections],
        "keywords": extract_keywords(title, content),
        "style_features": style
    }

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO training_data
            (article_id, title, structured_content, source, source_type,
             publish_time, topic, style_features)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (article_id, title, json.dumps(structured), source, source_type,
              str(time.time()), topic, json.dumps(style)))
        conn.commit()

    # Extract patterns from this article
    _extract_headline_pattern(title, topic, style)
    _extract_structure_pattern(sections, len(content.split()))
    _update_topic_cluster(topic)

    return structured


def extract_keywords(title: str, content: str) -> list:
    text = (title + " " + content[:1000]).lower()
    ev_terms = ["ev", "electric vehicle", "battery", "charging", "tesla", "byd",
                "tata", "mahindra", "hyundai", "kia", "ola", "ather", "subsidy",
                "range", "kwh", "fast charging", "infrastructure", "policy"]
    return [t for t in ev_terms if t in text][:8]


# ===============================================================
# STEP 2: PATTERN EXTRACTION
# ===============================================================

def _extract_headline_pattern(title: str, topic: str, style: dict):
    htype = style.get("headline_type", "statement")
    pid = f"hp_{htype}_{topic.lower()}"

    words = title.split()
    kw_positions = []
    for i, w in enumerate(words):
        if w.lower() in ["ev", "electric", "battery", "charging", "tesla", "launch", "new"]:
            kw_positions.append(i)

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT times_seen FROM headline_patterns WHERE pattern_id = ?", (pid,))
        row = cur.fetchone()

        if row:
            cur.execute("""
                UPDATE headline_patterns SET
                    times_seen = times_seen + 1,
                    avg_length = (avg_length * times_seen + ?) / (times_seen + 1),
                    best_example = CASE WHEN LENGTH(?) > LENGTH(best_example) THEN ? ELSE best_example END,
                    last_updated = CURRENT_TIMESTAMP
                WHERE pattern_id = ?
            """, (len(words), title, title, pid))
        else:
            cur.execute("""
                INSERT INTO headline_patterns
                (pattern_id, pattern_type, template, keyword_positions, avg_length, best_example)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (pid, htype, f"{htype}_{topic}", json.dumps(kw_positions), len(words), title))
        conn.commit()


def _extract_structure_pattern(sections: list, word_count: int):
    flow = [s.get("heading", s.get("name", "Section")) for s in sections]
    flow_key = "|".join(flow[:6])
    pid = f"sp_{hashlib.md5(flow_key.encode()).hexdigest()[:10]}"

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT times_seen FROM structure_patterns WHERE pattern_id = ?", (pid,))
        row = cur.fetchone()

        if row:
            cur.execute("""
                UPDATE structure_patterns SET
                    times_seen = times_seen + 1,
                    avg_word_count = (avg_word_count * times_seen + ?) / (times_seen + 1),
                    last_updated = CURRENT_TIMESTAMP
                WHERE pattern_id = ?
            """, (word_count, pid))
        else:
            cur.execute("""
                INSERT INTO structure_patterns
                (pattern_id, section_count, section_flow, avg_word_count)
                VALUES (?, ?, ?, ?)
            """, (pid, len(sections), json.dumps(flow), word_count))
        conn.commit()


def _update_topic_cluster(topic: str):
    cluster_map = {
        "Launch": "Product", "Policy": "Regulatory", "Tech": "Innovation",
        "Charging": "Infrastructure", "Market": "Business",
        "Safety": "Regulatory", "General": "Misc"
    }
    cluster = cluster_map.get(topic, "Misc")

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT article_count FROM topic_clusters WHERE topic = ?", (topic,))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE topic_clusters SET article_count = article_count + 1, last_updated = CURRENT_TIMESTAMP WHERE topic = ?", (topic,))
        else:
            cur.execute("INSERT INTO topic_clusters (topic, cluster) VALUES (?, ?)", (topic, cluster))
        conn.commit()


# ===============================================================
# STEP 3: PERFORMANCE LINKING
# ===============================================================

def link_performance(article_id: str, views: int = 0, ctr: float = 0.0,
                     engagement: float = 0.0, read_time: float = 0.0, shares: float = 0.0):
    score = 0.35 * ctr + 0.25 * engagement + 0.20 * read_time + 0.20 * shares

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE training_data SET
                views = ?, ctr = ?, engagement = ?, read_time = ?,
                shares = ?, pattern_score = ?
            WHERE article_id = ?
        """, (views, ctr, engagement, read_time, shares, score, article_id))

        # Update headline pattern scores
        cur.execute("SELECT style_features, topic FROM training_data WHERE article_id = ?", (article_id,))
        row = cur.fetchone()
        if row:
            try:
                style = json.loads(row[0])
                topic = row[1]
                htype = style.get("headline_type", "statement")
                pid = f"hp_{htype}_{topic.lower()}"
                cur.execute("""
                    UPDATE headline_patterns SET
                        avg_score = (avg_score * (times_seen - 1) + ?) / times_seen
                    WHERE pattern_id = ?
                """, (score, pid))
            except:
                pass
        conn.commit()


# ===============================================================
# STEP 4: ACTIVE TRAINING (USER QUALITY TAGS)
# ===============================================================

def tag_article_quality(article_id: str, tag: str):
    """Manual quality tagging: 'high', 'low', or 'untagged'."""
    boost = {"high": 0.3, "low": -0.3, "untagged": 0.0}
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE training_data SET quality_tag = ?, pattern_score = pattern_score + ? WHERE article_id = ?",
                    (tag, boost.get(tag, 0.0), article_id))
        conn.commit()


# ===============================================================
# STEP 5: GET BEST PATTERNS FOR GENERATION
# ===============================================================

def get_best_patterns_for_generation(topic: str = None) -> dict:
    """Returns the best-performing patterns for the LLM to use during generation."""
    with get_db() as conn:
        cur = conn.cursor()

        # Best headlines
        if topic:
            cur.execute("""
                SELECT best_example, pattern_type, avg_score
                FROM headline_patterns WHERE pattern_id LIKE ? AND avg_score > 0
                ORDER BY avg_score DESC LIMIT 5
            """, (f"%{topic.lower()}%",))
        else:
            cur.execute("""
                SELECT best_example, pattern_type, avg_score
                FROM headline_patterns WHERE avg_score > 0
                ORDER BY avg_score DESC LIMIT 5
            """)
        headlines = [{"example": r[0], "type": r[1], "score": r[2]} for r in cur.fetchall()]

        # Best structures
        cur.execute("""
            SELECT section_flow, section_count, avg_score
            FROM structure_patterns WHERE avg_score > 0
            ORDER BY avg_score DESC LIMIT 3
        """)
        structures = [{"flow": r[0], "sections": r[1], "score": r[2]} for r in cur.fetchall()]

        # Best topics
        cur.execute("""
            SELECT topic, avg_performance, article_count
            FROM topic_clusters
            ORDER BY avg_performance DESC LIMIT 5
        """)
        topics = [{"topic": r[0], "score": r[1], "count": r[2]} for r in cur.fetchall()]

        # Gold training examples (manually tagged high quality)
        cur.execute("""
            SELECT title, structured_content, pattern_score
            FROM training_data WHERE quality_tag = 'high'
            ORDER BY pattern_score DESC LIMIT 3
        """)
        gold = [{"title": r[0], "content": r[1][:500], "score": r[2]} for r in cur.fetchall()]

        return {
            "best_headlines": headlines,
            "best_structures": structures,
            "best_topics": topics,
            "gold_examples": gold
        }


# ===============================================================
# STEP 6: VALIDATION LAYER
# ===============================================================

def validate_generated_article(draft: dict) -> dict:
    """
    Validates a generated article against learned patterns.
    Returns {"valid": bool, "issues": [...], "score": float}
    """
    issues = []
    score = 1.0

    title = draft.get("title") or draft.get("seo_headline") or ""
    sections = draft.get("sections", [])
    meta_title = draft.get("meta_title", "")
    meta_desc = draft.get("meta_description", "")
    html_body = draft.get("html_body", "")

    # Title validation
    if not title or len(title) < 10:
        issues.append("Title too short or missing")
        score -= 0.3
    if len(title.split()) > 20:
        issues.append("Title too long (>20 words)")
        score -= 0.1

    # Sections validation
    if len(sections) < 2:
        issues.append("Too few sections (need at least 2)")
        score -= 0.2
    for s in sections:
        if not s.get("heading") and not s.get("name"):
            issues.append("Section missing heading")
            score -= 0.1
            break

    # SEO validation
    if not meta_title:
        issues.append("Missing meta_title")
        score -= 0.15
    elif len(meta_title) > 65:
        issues.append("meta_title too long (>65 chars)")
        score -= 0.05
    if not meta_desc:
        issues.append("Missing meta_description")
        score -= 0.15
    elif len(meta_desc) > 160:
        issues.append("meta_description too long (>160 chars)")
        score -= 0.05

    # Content depth
    total_words = sum(len((s.get("content", "") + s.get("html", "")).split()) for s in sections)
    if total_words < 200:
        issues.append(f"Content too thin ({total_words} words, need 600+)")
        score -= 0.3
    elif total_words < 600:
        issues.append(f"Content below target ({total_words} words, target 600-900)")
        score -= 0.1

    return {
        "valid": score >= 0.5 and len([i for i in issues if "missing" in i.lower()]) == 0,
        "issues": issues,
        "score": max(0, score)
    }


# ===============================================================
# STEP 7: TRAINING STATS
# ===============================================================

def get_training_stats() -> dict:
    with get_db() as conn:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM training_data")
        total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM training_data WHERE quality_tag = 'high'")
        gold = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM headline_patterns")
        hp = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM structure_patterns")
        sp = cur.fetchone()[0]

        cur.execute("SELECT topic, article_count, avg_performance FROM topic_clusters ORDER BY article_count DESC LIMIT 5")
        topics = [{"topic": r[0], "count": r[1], "score": r[2]} for r in cur.fetchall()]

        cur.execute("SELECT AVG(pattern_score) FROM training_data WHERE pattern_score > 0")
        avg = cur.fetchone()[0] or 0

    return {
        "total_training_articles": total,
        "gold_tagged": gold,
        "headline_patterns": hp,
        "structure_patterns": sp,
        "avg_pattern_score": round(avg, 3),
        "top_topics": topics
    }


def initialize_training_engine():
    """Initialize training tables from an application startup path."""
    init_training_tables()
