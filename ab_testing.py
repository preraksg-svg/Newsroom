"""
ZAPWAY Headline A/B Testing System
====================================
Generate 2-3 headline variants -> split traffic -> track -> pick winner -> learn.

Flow:
  Generate → Split → Track → Score → Select Winner → Update Patterns
"""
import json
import time
import hashlib
import uuid
from backend.db.queries import get_db


# ===============================================================
# DATABASE TABLES
# ===============================================================

def init_ab_tables():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS headline_tests (
                test_id TEXT PRIMARY KEY,
                article_id TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                winner_variant_id TEXT,
                total_impressions INTEGER DEFAULT 0,
                min_impressions INTEGER DEFAULT 50,
                max_hours INTEGER DEFAULT 24,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS headline_variants (
                variant_id TEXT PRIMARY KEY,
                test_id TEXT NOT NULL,
                headline_text TEXT NOT NULL,
                pattern_type TEXT,
                pattern_id TEXT,
                impressions INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                ctr REAL DEFAULT 0.0,
                engagement_score REAL DEFAULT 0.0,
                read_time REAL DEFAULT 0.0,
                variant_score REAL DEFAULT 0.0,
                is_winner INTEGER DEFAULT 0,
                FOREIGN KEY (test_id) REFERENCES headline_tests(test_id)
            )
        ''')
        conn.commit()
    print("[A/B TEST] Tables initialized.")


# ===============================================================
# CREATE A/B TEST
# ===============================================================

def create_ab_test(article_id: str, variants: list, min_impressions: int = 50, max_hours: int = 24) -> dict:
    """
    Create a new A/B test for an article.
    variants: list of {"headline": str, "pattern_type": str, "pattern_id": str|None}
    Max 3 variants enforced.
    """
    if len(variants) < 2:
        return {"success": False, "error": "Need at least 2 variants"}
    variants = variants[:3]  # Max 3

    test_id = f"abt_{uuid.uuid4().hex[:12]}"

    with get_db() as conn:
        cur = conn.cursor()

        # Check if article already has active test
        cur.execute("SELECT test_id FROM headline_tests WHERE article_id = ? AND status = 'active'", (article_id,))
        existing = cur.fetchone()
        if existing:
            return {"success": False, "error": "Article already has active test", "test_id": existing[0]}

        cur.execute("""
            INSERT INTO headline_tests (test_id, article_id, min_impressions, max_hours)
            VALUES (?, ?, ?, ?)
        """, (test_id, article_id, min_impressions, max_hours))

        variant_ids = []
        for i, v in enumerate(variants):
            vid = f"{test_id}_v{i}"
            cur.execute("""
                INSERT INTO headline_variants (variant_id, test_id, headline_text, pattern_type, pattern_id)
                VALUES (?, ?, ?, ?, ?)
            """, (vid, test_id, v["headline"], v.get("pattern_type", ""), v.get("pattern_id")))
            variant_ids.append(vid)

        conn.commit()

    print(f"[A/B TEST] Created test {test_id} with {len(variants)} variants for article {article_id}")
    return {"success": True, "test_id": test_id, "variant_ids": variant_ids}


# ===============================================================
# TRAFFIC SPLITTING — Deterministic user→variant mapping
# ===============================================================

def get_variant_for_user(test_id: str, user_id: str) -> dict:
    """
    Adaptive Split: same user usually sees same variant, 
    but traffic distribution shifts toward better performers.
    """
    from bandit_engine import calculate_traffic_shares
    
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT status FROM headline_tests WHERE test_id = ?", (test_id,))
        test = cur.fetchone()
        if not test:
            return {"error": "Test not found"}

        # If test completed, return winner
        if test[0] == "completed":
            cur.execute("SELECT headline_text, pattern_type FROM headline_variants WHERE test_id = ? AND is_winner = 1", (test_id,))
            winner = cur.fetchone()
            if winner:
                return {"headline": winner[0], "pattern_type": winner[1], "is_winner": True}

        # BANDIT LOGIC: Get variants with their traffic shares
        cur.execute("""
            SELECT v.variant_id, v.headline_text, v.pattern_type, 
                   IFNULL(m.traffic_share, 0.33) as share
            FROM headline_variants v
            LEFT JOIN real_time_metrics m ON v.variant_id = m.variant_id
            WHERE v.test_id = ? ORDER BY v.variant_id
        """, (test_id,))
        variants = cur.fetchall()
        if not variants:
            return {"error": "No variants"}

        # Use user_id hash to pick a random value [0, 1)
        hash_input = f"{user_id}_{test_id}"
        rand_val = (int(hashlib.md5(hash_input.encode()).hexdigest(), 16) % 1000) / 1000.0
        
        cumulative = 0.0
        selected = variants[0]
        for v in variants:
            cumulative += v[3]
            if rand_val < cumulative:
                selected = v
                break

        return {
            "variant_id": selected[0],
            "headline": selected[1],
            "pattern_type": selected[2],
            "is_winner": False,
            "test_active": True,
            "traffic_share": selected[3]
        }


# ===============================================================
# TRACKING EVENTS (UPGRADED WITH BANDIT SYNC)
# ===============================================================

def record_impression(variant_id: str):
    """Track that a user saw this variant."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE headline_variants SET impressions = impressions + 1 WHERE variant_id = ?", (variant_id,))
        cur.execute("""
            UPDATE headline_tests SET total_impressions = total_impressions + 1
            WHERE test_id = (SELECT test_id FROM headline_variants WHERE variant_id = ?)
        """, (variant_id,))
        conn.commit()
    
    # Sync to bandit
    _sync_to_bandit(variant_id)


def record_click(variant_id: str):
    """Track that a user clicked this variant."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE headline_variants SET clicks = clicks + 1 WHERE variant_id = ?", (variant_id,))
        cur.execute("SELECT impressions, clicks FROM headline_variants WHERE variant_id = ?", (variant_id,))
        row = cur.fetchone()
        if row and row[0] > 0:
            ctr = (row[1] / row[0]) * 100
            cur.execute("UPDATE headline_variants SET ctr = ? WHERE variant_id = ?", (ctr, variant_id))
        conn.commit()
    
    _sync_to_bandit(variant_id)


def record_engagement(variant_id: str, engagement: float = 0.0, read_time: float = 0.0):
    """Track engagement metrics for a variant."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT engagement_score, read_time, clicks FROM headline_variants WHERE variant_id = ?", (variant_id,))
        row = cur.fetchone()
        if not row: return

        clicks = max(row[2], 1)
        new_eng = (row[0] * (clicks - 1) + engagement) / clicks
        new_rt = (row[1] * (clicks - 1) + read_time) / clicks

        cur.execute("UPDATE headline_variants SET engagement_score = ?, read_time = ? WHERE variant_id = ?",
                    (new_eng, new_rt, variant_id))

        cur.execute("SELECT ctr FROM headline_variants WHERE variant_id = ?", (variant_id,))
        ctr_row = cur.fetchone()
        ctr = ctr_row[0] if ctr_row else 0
        
        # Scoring: 0.6×CTR + 0.25×Engagement + 0.15×ReadTime
        variant_score = 0.6 * ctr + 0.25 * new_eng + 0.15 * new_rt
        cur.execute("UPDATE headline_variants SET variant_score = ? WHERE variant_id = ?", (variant_score, variant_id))
        conn.commit()
    
    _sync_to_bandit(variant_id)


def _sync_to_bandit(variant_id: str):
    try:
        from bandit_engine import sync_bandit_metrics, calculate_traffic_shares, detect_early_winner
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT test_id, impressions, clicks, variant_score FROM headline_variants WHERE variant_id = ?", (variant_id,))
            row = cur.fetchone()
            if row:
                sync_bandit_metrics(variant_id, 'headline', row[0], row[1], row[2], row[3])
                calculate_traffic_shares(row[0], 'headline')
                
                # Early Winner Detection
                winner_id = detect_early_winner(row[0], 'headline')
                if winner_id:
                    check_and_select_winner(row[0]) # Force completion
    except Exception as e:
        print(f"[BANDIT SYNC ERROR] {e}")


# ===============================================================
# WINNER SELECTION
# ===============================================================

def check_and_select_winner(test_id: str) -> dict:
    """
    Check if a test should be concluded.
    Conditions:
      1. All variants have >= min_impressions
      2. OR max_hours exceeded (auto-pick best)
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT article_id, status, min_impressions, max_hours, created_at FROM headline_tests WHERE test_id = ?", (test_id,))
        test = cur.fetchone()
        if not test or test[1] != "active":
            return {"concluded": False, "reason": "Not active"}

        article_id = test[0]
        min_imp = test[2]
        max_hours = test[3]

        # Check time limit
        try:
            created = float(test[4]) if test[4] else time.time()
        except:
            created = time.time()
        hours_elapsed = (time.time() - created) / 3600
        time_expired = hours_elapsed >= max_hours

        # Get variants
        cur.execute("""
            SELECT variant_id, headline_text, pattern_type, pattern_id, 
                   impressions, ctr, variant_score, is_winner
            FROM headline_variants WHERE test_id = ?
            ORDER BY variant_score DESC
        """, (test_id,))
        variants = cur.fetchall()

        if not variants:
            return {"concluded": False, "reason": "No variants"}

        # Check if all have enough impressions
        all_above_threshold = all(v[4] >= min_imp for v in variants)

        # Check for clear winner (>20% lead)
        if len(variants) >= 2:
            best_score = variants[0][6]
            second_score = variants[1][6]
            clear_winner = best_score > 0 and (best_score - second_score) / max(best_score, 0.01) > 0.20
        else:
            clear_winner = True

        should_conclude = all_above_threshold or time_expired or (clear_winner and variants[0][4] >= 20)

        if not should_conclude:
            return {
                "concluded": False,
                "hours_elapsed": round(hours_elapsed, 1),
                "variants": [{"id": v[0], "impressions": v[4], "ctr": v[5], "score": v[6]} for v in variants]
            }

        # SELECT WINNER
        winner = variants[0]  # Already sorted by variant_score DESC
        winner_id = winner[0]
        winner_headline = winner[1]
        winner_pattern_type = winner[2]
        winner_pattern_id = winner[3]

        # Mark winner
        cur.execute("UPDATE headline_variants SET is_winner = 1 WHERE variant_id = ?", (winner_id,))
        cur.execute("""
            UPDATE headline_tests SET
                status = 'completed',
                winner_variant_id = ?,
                completed_at = CURRENT_TIMESTAMP
            WHERE test_id = ?
        """, (winner_id, test_id))

        # Replace article headline with winner
        cur.execute("UPDATE stories SET title = ? WHERE id = ?", (winner_headline, article_id))

        conn.commit()

        # LEARNING: Update headline pattern weights
        _update_pattern_learning(variants)

        reason = "time_limit" if time_expired else ("clear_winner" if clear_winner else "threshold")
        print(f"[A/B TEST] Winner selected for {test_id}: '{winner_headline}' ({winner_pattern_type}) | Reason: {reason}")

        return {
            "concluded": True,
            "reason": reason,
            "winner": {
                "variant_id": winner_id,
                "headline": winner_headline,
                "pattern_type": winner_pattern_type,
                "score": winner[6],
                "ctr": winner[5]
            },
            "all_variants": [{"id": v[0], "headline": v[1], "type": v[2],
                              "impressions": v[4], "ctr": v[5], "score": v[6]} for v in variants]
        }


def _update_pattern_learning(variants):
    """Reinforce winning patterns, reduce losing patterns."""
    try:
        from headline_engine import update_headline_performance
        for v in variants:
            pattern_id = v[3]  # pattern_id
            if not pattern_id:
                continue
            ctr = v[5]
            score = v[6]
            is_winner = v[0] == variants[0][0]  # First = winner (sorted by score)

            if is_winner:
                # Boost winner pattern
                update_headline_performance(pattern_id, ctr=ctr, engagement=score, shares=score * 0.5)
            else:
                # Slight decrease for losers (gentle — don't kill patterns)
                update_headline_performance(pattern_id, ctr=max(0, ctr * 0.5), engagement=max(0, score * 0.3), shares=0)
    except Exception as e:
        print(f"[A/B TEST] Learning update error: {e}")


# ===============================================================
# AUTO-CHECK LOOP (called periodically)
# ===============================================================

def check_all_active_tests():
    """Check all active tests for winner selection."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT test_id FROM headline_tests WHERE status = 'active'")
        active = cur.fetchall()

    concluded = 0
    for row in active:
        result = check_and_select_winner(row[0])
        if result.get("concluded"):
            concluded += 1

    if concluded > 0:
        print(f"[A/B TEST] Concluded {concluded} tests this cycle.")
    return concluded


# ===============================================================
# QUERY HELPERS
# ===============================================================

def get_test_for_article(article_id: str) -> dict:
    """Get A/B test status for an article."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT test_id, status, total_impressions, created_at, winner_variant_id
            FROM headline_tests WHERE article_id = ?
            ORDER BY created_at DESC LIMIT 1
        """, (article_id,))
        test = cur.fetchone()
        if not test:
            return {"has_test": False}

        cur.execute("""
            SELECT v.variant_id, v.headline_text, v.pattern_type, v.impressions, v.clicks, v.ctr,
                   v.engagement_score, v.read_time, v.variant_score, v.is_winner,
                   IFNULL(m.traffic_share, 0.33) as share
            FROM headline_variants v
            LEFT JOIN real_time_metrics m ON v.variant_id = m.variant_id
            WHERE v.test_id = ?
            ORDER BY v.variant_score DESC
        """, (test[0],))
        variants = cur.fetchall()

        return {
            "has_test": True,
            "test_id": test[0],
            "status": test[1],
            "total_impressions": test[2],
            "winner_id": test[4],
            "is_optimizing": test[1] == 'active' and test[2] > 30, # Optimization starts after cold start
            "variants": [{
                "variant_id": v[0], "headline": v[1], "pattern_type": v[2],
                "impressions": v[3], "clicks": v[4], "ctr": round(v[5], 2),
                "engagement": round(v[6], 2), "read_time": round(v[7], 1),
                "score": round(v[8], 2), "is_winner": bool(v[9]),
                "traffic_share": round(v[10] * 100, 1)
            } for v in variants]
        }


def get_all_active_tests() -> list:
    """Get all currently active A/B tests."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.test_id, t.article_id, t.total_impressions, t.created_at,
                   s.title
            FROM headline_tests t
            LEFT JOIN stories s ON t.article_id = s.id
            WHERE t.status = 'active'
            ORDER BY t.created_at DESC
        """)
        tests = cur.fetchall()
        return [{
            "test_id": t[0], "article_id": t[1],
            "impressions": t[2], "title": t[4] or "Unknown"
        } for t in tests]


def initialize_ab_testing():
    """Initialize headline A/B testing tables from an application startup path."""
    init_ab_tables()
