"""
ZAPWAY Self-Learning Intelligence Engine
==========================================
Two-level continuous learning system:
  Level 1 (Micro) - Worker-level learning per source
  Level 2 (Macro) - System-level learning for content quality

All weights update from DATA, not from hardcoded rules.
"""
import math
import time
import json
from contextlib import contextmanager
from backend.db.queries import get_db, get_connection


# ===============================================================
# DATABASE SCHEMA — Learning Tables
# ===============================================================

def init_learning_tables():
    """Create all learning memory tables."""
    with get_db() as conn:
        cur = conn.cursor()

        # -- Worker Memory (per source) -------------------------
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

        # -- Content Memory (patterns) --------------------------
        cur.execute('''
            CREATE TABLE IF NOT EXISTS content_memory (
                pattern_id TEXT PRIMARY KEY,
                headline_style TEXT,
                topic TEXT,
                format TEXT,
                structure TEXT,
                source_type TEXT,
                performance_score REAL DEFAULT 0.0,
                views INTEGER DEFAULT 0,
                ctr REAL DEFAULT 0.0,
                engagement REAL DEFAULT 0.0,
                read_time REAL DEFAULT 0.0,
                shares REAL DEFAULT 0.0,
                times_used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # -- Trend Memory --------------------------------------
        cur.execute('''
            CREATE TABLE IF NOT EXISTS trend_memory (
                topic TEXT PRIMARY KEY,
                signal_count INTEGER DEFAULT 0,
                velocity REAL DEFAULT 0.0,
                is_active INTEGER DEFAULT 1,
                last_signal TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # -- LLM Prompt Memory ---------------------------------
        cur.execute('''
            CREATE TABLE IF NOT EXISTS prompt_memory (
                prompt_hash TEXT PRIMARY KEY,
                prompt_type TEXT,
                token_count INTEGER,
                quality_score REAL DEFAULT 0.5,
                times_used INTEGER DEFAULT 1,
                avg_output_quality REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
    print("[LEARNING] Memory tables initialized.")


# ===============================================================
# LEVEL 1: WORKER-LEVEL LEARNING (Micro)
# ===============================================================

# Learning rate for worker scores
WORKER_ALPHA = 0.1

def record_worker_ingestion(source_id: str, was_selected: bool, was_high_perf: bool = False):
    """
    Called every time a worker ingests content.
    Tracks whether the content was selected for article generation.
    """
    with get_db() as conn:
        cur = conn.cursor()

        # Ensure row exists
        cur.execute("""
            INSERT OR IGNORE INTO worker_memory (source_id)
            VALUES (?)
        """, (source_id,))

        # Update counters
        cur.execute("""
            UPDATE worker_memory SET
                total_ingested = total_ingested + 1,
                total_selected = total_selected + ?,
                total_ignored = total_ignored + ?,
                total_high_perf = total_high_perf + ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE source_id = ?
        """, (
            1 if was_selected else 0,
            0 if was_selected else 1,
            1 if was_high_perf else 0,
            source_id
        ))

        # Recalculate success rate
        cur.execute("SELECT total_ingested, total_selected FROM worker_memory WHERE source_id = ?", (source_id,))
        row = cur.fetchone()
        if row and row[0] > 0:
            success_rate = row[1] / row[0]
            cur.execute("UPDATE worker_memory SET success_rate = ? WHERE source_id = ?", (success_rate, source_id))

        # Update last_50 performance ring buffer
        cur.execute("SELECT last_50_performance FROM worker_memory WHERE source_id = ?", (source_id,))
        row = cur.fetchone()
        if row:
            try:
                perf_list = json.loads(row[0] or "[]")
            except:
                perf_list = []
            perf_list.append(1.0 if was_selected else 0.0)
            if len(perf_list) > 50:
                perf_list = perf_list[-50:]
            cur.execute("UPDATE worker_memory SET last_50_performance = ? WHERE source_id = ?",
                        (json.dumps(perf_list), source_id))

        conn.commit()


def update_worker_score(source_id: str, engagement: float = 0.0, relevance: float = 0.5):
    """
    Update the composite worker score using the formula:
    WorkerScore = 0.5 × SuccessRate + 0.3 × Engagement + 0.2 × Relevance
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT success_rate, avg_engagement, relevance_score, worker_score FROM worker_memory WHERE source_id = ?", (source_id,))
        row = cur.fetchone()
        if not row:
            return

        old_score = row[3] or 0.5
        success_rate = row[0] or 0.5

        # Smooth engagement update
        new_engagement = (row[1] or 0.0) * 0.8 + engagement * 0.2
        new_relevance = (row[2] or 0.5) * 0.7 + relevance * 0.3

        # Calculate new score
        new_score = 0.5 * success_rate + 0.3 * new_engagement + 0.2 * new_relevance

        # Reinforcement update with learning rate
        final_score = old_score + WORKER_ALPHA * (new_score - old_score)

        # Update poll interval: high-score sources get polled MORE (lower multiplier)
        # Low-score sources get polled LESS (higher multiplier)
        if final_score > 0.7:
            poll_mult = 0.5    # Poll twice as often
        elif final_score > 0.5:
            poll_mult = 1.0    # Normal
        elif final_score > 0.3:
            poll_mult = 2.0    # Half frequency
        else:
            poll_mult = 4.0    # Quarter frequency

        cur.execute("""
            UPDATE worker_memory SET
                avg_engagement = ?,
                relevance_score = ?,
                worker_score = ?,
                poll_interval_multiplier = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE source_id = ?
        """, (new_engagement, new_relevance, final_score, poll_mult, source_id))
        conn.commit()


def get_worker_score(source_id: str) -> float:
    """Get current worker score for a source."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT worker_score FROM worker_memory WHERE source_id = ?", (source_id,))
        row = cur.fetchone()
        return row[0] if row else 0.5


def get_poll_multiplier(source_id: str) -> float:
    """Get the learned polling frequency multiplier for a source."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT poll_interval_multiplier FROM worker_memory WHERE source_id = ?", (source_id,))
        row = cur.fetchone()
        return row[0] if row else 1.0


def should_skip_content(source_id: str, title: str) -> bool:
    """
    Workers learn to skip low-value content faster over time.
    If a source has consistently low scores, skip marginal content.
    """
    score = get_worker_score(source_id)
    if score < 0.2:
        return True   # Source is too low quality, skip everything
    if score < 0.35 and len(title) < 30:
        return True   # Low-quality source + short title = skip
    return False


# ===============================================================
# LEVEL 2: SYSTEM-LEVEL LEARNING (Macro)
# ===============================================================

# Learning rate for system weights
SYSTEM_ALPHA = 0.05

def record_content_pattern(story_id: str, headline: str, topic: str, 
                           format_type: str, structure: str, source_type: str):
    """Record a content pattern when an article is generated."""
    pattern_id = f"cp_{abs(hash(headline + topic)) % 9999999}"
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO content_memory 
            (pattern_id, headline_style, topic, format, structure, source_type)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (pattern_id, headline[:100], topic, format_type, structure, source_type))
        cur.execute("""
            UPDATE content_memory SET times_used = times_used + 1, last_updated = CURRENT_TIMESTAMP
            WHERE pattern_id = ?
        """, (pattern_id,))
        conn.commit()
    return pattern_id


def update_content_performance(pattern_id: str, views: int = 0, ctr: float = 0.0,
                                engagement: float = 0.0, read_time: float = 0.0,
                                shares: float = 0.0):
    """
    Update performance metrics for a content pattern.
    PerformanceScore = 0.35 × CTR + 0.25 × Engagement + 0.2 × ReadTime + 0.2 × Shares
    """
    perf_score = 0.35 * ctr + 0.25 * engagement + 0.20 * read_time + 0.20 * shares

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT performance_score FROM content_memory WHERE pattern_id = ?", (pattern_id,))
        row = cur.fetchone()
        if not row:
            return

        old_score = row[0] or 0.0
        # Reinforcement: NewWeight = OldWeight + α × (Performance − Expected)
        new_score = old_score + SYSTEM_ALPHA * (perf_score - old_score)

        cur.execute("""
            UPDATE content_memory SET
                performance_score = ?,
                views = views + ?,
                ctr = ?,
                engagement = ?,
                read_time = ?,
                shares = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE pattern_id = ?
        """, (new_score, views, ctr, engagement, read_time, shares, pattern_id))
        conn.commit()


def get_top_performing_patterns(limit: int = 10) -> list:
    """Get the highest-performing content patterns for RAG context."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT headline_style, topic, format, structure, performance_score
            FROM content_memory
            WHERE performance_score > 0
            ORDER BY performance_score DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        return [
            {
                "headline_style": r[0], "topic": r[1],
                "format": r[2], "structure": r[3],
                "score": r[4]
            }
            for r in rows
        ]


def get_best_headline_patterns(limit: int = 5) -> list:
    """Returns headline styles that historically perform best."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT headline_style, performance_score
            FROM content_memory
            WHERE performance_score > 0.3
            ORDER BY performance_score DESC
            LIMIT ?
        """, (limit,))
        return [r[0] for r in cur.fetchall()]


def get_best_topics(limit: int = 5) -> list:
    """Returns topics that historically drive the most engagement."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT topic, AVG(performance_score) as avg_perf
            FROM content_memory
            WHERE topic != '' AND performance_score > 0
            GROUP BY topic
            ORDER BY avg_perf DESC
            LIMIT ?
        """, (limit,))
        return [{"topic": r[0], "avg_score": r[1]} for r in cur.fetchall()]


# ===============================================================
# TREND DETECTION
# ===============================================================

def record_trend_signal(topic: str, source_id: str):
    now = time.time()
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT signal_count, last_signal FROM trend_memory WHERE topic = ?", (topic,))
        row = cur.fetchone()
        if row:
            new_count = row[0] + 1
            try:
                last_ts = float(row[1]) if row[1] else now
            except:
                last_ts = now
            hours_elapsed = max((now - last_ts) / 3600, 0.1)
            velocity = new_count / hours_elapsed
            cur.execute("""
                UPDATE trend_memory SET
                    signal_count = ?,
                    velocity = ?,
                    is_active = 1,
                    last_signal = ?
                WHERE topic = ?
            """, (new_count, velocity, str(now), topic))
        else:
            cur.execute("""
                INSERT INTO trend_memory (topic, signal_count, velocity, is_active, last_signal)
                VALUES (?, 1, 0.0, 1, ?)
            """, (topic, str(now)))
        conn.commit()


def get_active_trends(min_signals: int = 3) -> list:
    """Get topics that are trending (multiple signals from multiple sources)."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT topic, signal_count, velocity
            FROM trend_memory
            WHERE is_active = 1 AND signal_count >= ?
            ORDER BY velocity DESC
            LIMIT 20
        """, (min_signals,))
        return [
            {"topic": r[0], "signals": r[1], "velocity": r[2]}
            for r in cur.fetchall()
        ]


def is_trending(topic: str) -> bool:
    """Check if a topic is currently trending."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT signal_count, velocity FROM trend_memory WHERE topic = ? AND is_active = 1", (topic,))
        row = cur.fetchone()
        if row and row[0] >= 3 and row[1] > 1.0:
            return True
    return False


# ===============================================================
# DECAY MECHANISM
# ===============================================================

# Decay constant — higher = faster decay
LAMBDA_DECAY = 0.01   # ~7% decay per day

def apply_decay():
    """
    Apply time-based decay to all scores:
    Score = Score × e^(−λt)
    Called during daily maintenance.
    """
    now = time.time()

    with get_db() as conn:
        cur = conn.cursor()

        # Decay content memory scores
        cur.execute("SELECT pattern_id, performance_score, last_updated FROM content_memory WHERE performance_score > 0.01")
        patterns = cur.fetchall()
        for p in patterns:
            try:
                last_ts = float(p[2]) if p[2] else now
            except:
                last_ts = now
            days_elapsed = (now - last_ts) / 86400
            decay_factor = math.exp(-LAMBDA_DECAY * days_elapsed)
            new_score = p[1] * decay_factor
            if new_score < 0.01:
                new_score = 0.0
            cur.execute("UPDATE content_memory SET performance_score = ? WHERE pattern_id = ?", (new_score, p[0]))

        # Decay worker memory scores (gentler)
        cur.execute("SELECT source_id, worker_score, last_updated FROM worker_memory WHERE worker_score > 0.01")
        workers = cur.fetchall()
        for w in workers:
            try:
                last_ts = float(w[2]) if w[2] else now
            except:
                last_ts = now
            days_elapsed = (now - last_ts) / 86400
            decay_factor = math.exp(-LAMBDA_DECAY * 0.5 * days_elapsed)  # Half decay rate for workers
            new_score = max(w[1] * decay_factor, 0.1)  # Floor at 0.1 — never fully kill a source
            cur.execute("UPDATE worker_memory SET worker_score = ? WHERE source_id = ?", (new_score, w[0]))

        # Deactivate stale trends (no signals in 48h)
        cutoff = str(now - 172800)
        cur.execute("UPDATE trend_memory SET is_active = 0 WHERE last_signal < ? AND is_active = 1", (cutoff,))

        conn.commit()
    print("[LEARNING] Decay cycle applied to all memory stores.")


# ===============================================================
# LLM USAGE OPTIMIZATION
# ===============================================================

def should_use_llm(source_id: str, content_length: int) -> bool:
    """
    System learns when NOT to use LLM.
    If a source consistently produces content that gets rejected,
    skip LLM entirely for that source.
    """
    score = get_worker_score(source_id)
    if score < 0.15:
        return False   # Too low quality — don't waste tokens
    if content_length < 100 and score < 0.4:
        return False   # Short content from low-score source — skip
    return True


def record_prompt_performance(prompt_type: str, token_count: int, quality: float):
    """Track which prompt patterns are most token-efficient."""
    prompt_hash = f"ph_{abs(hash(prompt_type)) % 999999}"
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT times_used, avg_output_quality FROM prompt_memory WHERE prompt_hash = ?", (prompt_hash,))
        row = cur.fetchone()
        if row:
            new_avg = (row[1] * row[0] + quality) / (row[0] + 1)
            cur.execute("""
                UPDATE prompt_memory SET
                    times_used = times_used + 1,
                    avg_output_quality = ?,
                    token_count = ?
                WHERE prompt_hash = ?
            """, (new_avg, token_count, prompt_hash))
        else:
            cur.execute("""
                INSERT INTO prompt_memory (prompt_hash, prompt_type, token_count, quality_score, avg_output_quality)
                VALUES (?, ?, ?, ?, ?)
            """, (prompt_hash, prompt_type, token_count, quality, quality))
        conn.commit()


# ===============================================================
# SOURCE LEARNING (Dynamic Source Scoring)
# ===============================================================

SOURCE_ALPHA = 0.08

def update_source_learning(source_id: str, article_performance: float, expected: float = 0.5):
    """
    Dynamically update source score based on actual article performance:
    NewSourceScore = OldScore + α × (Performance − Expected)
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT dynamic_score FROM sources WHERE source_id = ?", (source_id,))
        row = cur.fetchone()
        if not row:
            return

        old_score = row[0] or 0.5
        new_score = old_score + SOURCE_ALPHA * (article_performance - expected)
        new_score = max(0.05, min(1.0, new_score))  # Clamp 0.05–1.0

        cur.execute("UPDATE sources SET dynamic_score = ?, last_updated = CURRENT_TIMESTAMP WHERE source_id = ?",
                    (new_score, source_id))
        conn.commit()


# ===============================================================
# FULL FEEDBACK LOOP
# ===============================================================

def run_full_feedback_loop(story_id: str, source_id: str,
                           views: int, ctr: float, engagement: float,
                           read_time: float, shares: float):
    """
    Complete feedback loop:
    Ingest → Generate → Publish → Track → Learn → Update weights → Improve next cycle
    """
    # 1. Calculate performance score
    perf_score = 0.35 * ctr + 0.25 * engagement + 0.20 * read_time + 0.20 * shares
    normalized = min(perf_score / 100.0, 1.0)

    # 2. Update worker-level learning
    is_high_perf = normalized > 0.6
    record_worker_ingestion(source_id, was_selected=True, was_high_perf=is_high_perf)
    update_worker_score(source_id, engagement=normalized, relevance=normalized * 0.8)

    # 3. Update source learning
    update_source_learning(source_id, normalized)

    # 4. Update content memory patterns
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT title, news_type FROM stories WHERE id = ?", (story_id,))
        row = cur.fetchone()
        if row:
            pattern_id = record_content_pattern(
                story_id, row[0] or "", row[1] or "Event",
                "article", "standard", "mixed"
            )
            update_content_performance(pattern_id, views, ctr, engagement, read_time, shares)

    # 5. Check for trends
    if row:
        record_trend_signal(row[1] or "EV News", source_id)

    print(f"[LEARNING] Full feedback loop completed for {story_id} | Score: {normalized:.2f} | HighPerf: {is_high_perf}")


# ===============================================================
# DAILY MAINTENANCE
# ===============================================================

def run_learning_maintenance():
    """Called daily to apply decay and log learning stats."""
    apply_decay()

    # Print learning dashboard
    with get_db() as conn:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*), AVG(worker_score) FROM worker_memory")
        wm = cur.fetchone()

        cur.execute("SELECT COUNT(*), AVG(performance_score) FROM content_memory WHERE performance_score > 0")
        cm = cur.fetchone()

        cur.execute("SELECT COUNT(*) FROM trend_memory WHERE is_active = 1")
        tm = cur.fetchone()

    print("=" * 50)
    print("  ZAPWAY LEARNING DASHBOARD")
    print("=" * 50)
    print(f"  Workers tracked:    {wm[0] or 0}")
    print(f"  Avg worker score:   {(wm[1] or 0):.3f}")
    print(f"  Content patterns:   {cm[0] or 0}")
    print(f"  Avg content score:  {(cm[1] or 0):.3f}")
    print(f"  Active trends:      {tm[0] or 0}")
    print("=" * 50)


# ===============================================================
# BOOT
# ===============================================================

def initialize_learning_engine():
    """Initialize learning memory tables from an application startup path."""
    init_learning_tables()
