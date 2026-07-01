"""
ZAPWAY Thumbnail A/B Testing System
====================================
Test multiple thumbnail variants → split traffic → track → pick winner.
"""
import json
import time
import hashlib
import uuid
from backend.db.queries import get_db


# ===============================================================
# DATABASE TABLES
# ===============================================================

def init_thumbnail_ab_tables():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS thumbnail_tests (
                test_id TEXT PRIMARY KEY,
                article_id TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                winner_variant_id TEXT,
                total_impressions INTEGER DEFAULT 0,
                min_impressions INTEGER DEFAULT 100,
                max_hours INTEGER DEFAULT 48,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS thumbnail_variants (
                variant_id TEXT PRIMARY KEY,
                test_id TEXT NOT NULL,
                image_url TEXT NOT NULL,
                style_type TEXT,
                impressions INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                ctr REAL DEFAULT 0.0,
                engagement_score REAL DEFAULT 0.0,
                read_time REAL DEFAULT 0.0,
                thumbnail_score REAL DEFAULT 0.0,
                is_winner INTEGER DEFAULT 0,
                FOREIGN KEY (test_id) REFERENCES thumbnail_tests(test_id)
            )
        ''')
        conn.commit()
    print("[THUMBNAIL A/B] Tables initialized.")


# ===============================================================
# CREATE THUMBNAIL A/B TEST
# ===============================================================

def create_thumbnail_test(article_id: str, variants: list, min_impressions: int = 100) -> dict:
    """
    variants: list of {"image_url": str, "style_type": str}
    """
    if len(variants) < 2:
        return {"success": False, "error": "Need at least 2 variants"}
    
    test_id = f"thbt_{uuid.uuid4().hex[:12]}"

    with get_db() as conn:
        cur = conn.cursor()
        
        # Check if active test exists
        cur.execute("SELECT test_id FROM thumbnail_tests WHERE article_id = ? AND status = 'active'", (article_id,))
        if cur.fetchone():
            return {"success": False, "error": "Active test already exists"}

        cur.execute("""
            INSERT INTO thumbnail_tests (test_id, article_id, min_impressions)
            VALUES (?, ?, ?)
        """, (test_id, article_id, min_impressions))

        for i, v in enumerate(variants):
            vid = f"{test_id}_v{i}"
            cur.execute("""
                INSERT INTO thumbnail_variants (variant_id, test_id, image_url, style_type)
                VALUES (?, ?, ?, ?)
            """, (vid, test_id, v["image_url"], v["style_type"]))
            
        conn.commit()

    print(f"[THUMBNAIL A/B] Created test {test_id} for article {article_id}")
    return {"success": True, "test_id": test_id}


# ===============================================================
# TRAFFIC SPLITTING
# ===============================================================

def get_thumbnail_for_user(test_id: str, user_id: str) -> dict:
    """
    Adaptive Split: shifts traffic to better thumbnails in real-time.
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT status FROM thumbnail_tests WHERE test_id = ?", (test_id,))
        test = cur.fetchone()
        if not test: return {"error": "Test not found"}

        if test[0] == "completed":
            cur.execute("SELECT image_url, style_type FROM thumbnail_variants WHERE test_id = ? AND is_winner = 1", (test_id,))
            winner = cur.fetchone()
            if winner:
                return {"image_url": winner[0], "style_type": winner[1], "is_winner": True}

        # BANDIT LOGIC: Get variants and traffic shares
        cur.execute("""
            SELECT v.variant_id, v.image_url, v.style_type,
                   IFNULL(m.traffic_share, 0.33) as share
            FROM thumbnail_variants v
            LEFT JOIN real_time_metrics m ON v.variant_id = m.variant_id
            WHERE v.test_id = ? ORDER BY v.variant_id
        """, (test_id,))
        variants = cur.fetchall()
        if not variants: return {"error": "No variants"}

        # Use user_id hash for split
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
            "image_url": selected[1],
            "style_type": selected[2],
            "is_winner": False,
            "test_active": True,
            "traffic_share": selected[3]
        }


# ===============================================================
# TRACKING
# ===============================================================

def record_thumbnail_impression(variant_id: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE thumbnail_variants SET impressions = impressions + 1 WHERE variant_id = ?", (variant_id,))
        cur.execute("""
            UPDATE thumbnail_tests SET total_impressions = total_impressions + 1
            WHERE test_id = (SELECT test_id FROM thumbnail_variants WHERE variant_id = ?)
        """, (variant_id,))
        conn.commit()
    _sync_to_bandit(variant_id)

def record_thumbnail_click(variant_id: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE thumbnail_variants SET clicks = clicks + 1 WHERE variant_id = ?", (variant_id,))
        cur.execute("SELECT impressions, clicks FROM thumbnail_variants WHERE variant_id = ?", (variant_id,))
        row = cur.fetchone()
        if row and row[0] > 0:
            ctr = (row[1] / row[0]) * 100
            cur.execute("UPDATE thumbnail_variants SET ctr = ? WHERE variant_id = ?", (ctr, variant_id))
        conn.commit()
    _sync_to_bandit(variant_id)

def record_thumbnail_engagement(variant_id: str, engagement: float, read_time: float):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT ctr, engagement_score, read_time, clicks FROM thumbnail_variants WHERE variant_id = ?", (variant_id,))
        row = cur.fetchone()
        if not row: return

        ctr, old_eng, old_rt, clicks = row
        clicks = max(clicks, 1)
        new_eng = (old_eng * (clicks - 1) + engagement) / clicks
        new_rt = (old_rt * (clicks - 1) + read_time) / clicks
        
        # Scoring: 0.6×CTR + 0.25×Engagement + 0.15×ReadTime
        score = 0.6 * ctr + 0.25 * new_eng + 0.15 * new_rt
        
        cur.execute("""
            UPDATE thumbnail_variants 
            SET engagement_score = ?, read_time = ?, thumbnail_score = ?
            WHERE variant_id = ?
        """, (new_eng, new_rt, score, variant_id))
        conn.commit()
    _sync_to_bandit(variant_id)

def _sync_to_bandit(variant_id: str):
    try:
        from bandit_engine import sync_bandit_metrics, calculate_traffic_shares, detect_early_winner
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT test_id, impressions, clicks, thumbnail_score FROM thumbnail_variants WHERE variant_id = ?", (variant_id,))
            row = cur.fetchone()
            if row:
                sync_bandit_metrics(variant_id, 'thumbnail', row[0], row[1], row[2], row[3])
                calculate_traffic_shares(row[0], 'thumbnail')
                
                # Early winner
                winner_id = detect_early_winner(row[0], 'thumbnail')
                if winner_id:
                    check_thumbnail_winner(row[0])
    except Exception as e:
        print(f"[BANDIT THUMB ERROR] {e}")


# ===============================================================
# WINNER SELECTION
# ===============================================================

def check_thumbnail_winner(test_id: str) -> dict:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT article_id, status, min_impressions, max_hours, created_at FROM thumbnail_tests WHERE test_id = ?", (test_id,))
        test = cur.fetchone()
        if not test or test[1] != "active": return {"concluded": False}

        article_id, _, min_imp, max_h, created = test
        created_ts = float(created) if isinstance(created, (int, float)) else time.time()
        hours_elapsed = (time.time() - created_ts) / 3600
        
        cur.execute("SELECT variant_id, image_url, style_type, impressions, thumbnail_score FROM thumbnail_variants WHERE test_id = ? ORDER BY thumbnail_score DESC", (test_id,))
        variants = cur.fetchall()
        
        all_above = all(v[3] >= min_imp for v in variants)
        time_expired = hours_elapsed >= max_h
        
        if all_above or time_expired:
            winner = variants[0]
            cur.execute("UPDATE thumbnail_variants SET is_winner = 1 WHERE variant_id = ?", (winner[0],))
            cur.execute("UPDATE thumbnail_tests SET status = 'completed', winner_variant_id = ?, completed_at = CURRENT_TIMESTAMP WHERE test_id = ?", (winner[0], test_id))
            
            # Replace main thumbnail (in images list)
            cur.execute("SELECT images FROM stories WHERE id = ?", (article_id,))
            story_row = cur.fetchone()
            if story_row:
                try:
                    import json
                    current_images = json.loads(story_row[0] or "[]")
                except:
                    current_images = []
                winning_url = winner[1]
                if winning_url in current_images:
                    current_images.remove(winning_url)
                new_images = [winning_url] + current_images
                cur.execute("UPDATE stories SET images = ? WHERE id = ?",
                            (json.dumps(new_images), article_id))
            
            conn.commit()
            
            # Learning
            try:
                from thumbnail_engine import update_style_weight
                for v in variants:
                    update_style_weight(v[2], v[4], expected=0.05)
            except: pass
            
            return {"concluded": True, "winner": winner[2]}
            
        return {"concluded": False}


# ===============================================================
# HELPERS
# ===============================================================

def get_thumbnail_test_status(article_id: str) -> dict:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT test_id, status, total_impressions FROM thumbnail_tests WHERE article_id = ? ORDER BY created_at DESC LIMIT 1", (article_id,))
        test = cur.fetchone()
        if not test: return {"has_test": False}
        
        cur.execute("""
            SELECT v.variant_id, v.image_url, v.style_type, v.impressions, v.ctr, v.thumbnail_score, v.is_winner,
                   IFNULL(m.traffic_share, 0.33) as share
            FROM thumbnail_variants v
            LEFT JOIN real_time_metrics m ON v.variant_id = m.variant_id
            WHERE v.test_id = ?
            ORDER BY v.thumbnail_score DESC
        """, (test[0],))
        vars = cur.fetchall()
        
        return {
            "has_test": True,
            "test_id": test[0],
            "status": test[1],
            "total_impressions": test[2],
            "is_optimizing": test[1] == 'active' and test[2] > 30,
            "variants": [{
                "id": v[0], "url": v[1], "style": v[2], "impressions": v[3], 
                "ctr": v[4], "score": v[5], "is_winner": bool(v[6]),
                "traffic_share": round(v[7] * 100, 1)
            } for v in vars]
        }

def list_active_thumbnail_tests():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT test_id FROM thumbnail_tests WHERE status = 'active'")
        return [r[0] for r in cur.fetchall()]

def check_all_thumbnail_tests():
    active = list_active_thumbnail_tests()
    concluded = 0
    for tid in active:
        res = check_thumbnail_winner(tid)
        if res.get("concluded"):
            concluded += 1
    return concluded

def initialize_thumbnail_ab_testing():
    """Initialize thumbnail A/B testing tables from an application startup path."""
    init_thumbnail_ab_tables()
