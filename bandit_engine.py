"""
ZAPWAY Real-Time Switching System (Multi-Armed Bandit)
=====================================================
Optimizes traffic allocation in real-time by shifting weight to better performers.
Supports both Headlines and Thumbnails.
"""
import math
import random
from backend.db.queries import get_db

# ===============================================================
# BANDIT CONFIGURATION
# ===============================================================

TEMPERATURE = 0.5  # Lower = more aggressive exploitation, Higher = more exploration
MIN_EXPLORATION_IMPRESSIONS = 30  # Initial "Cold Start" phase per variant

# ===============================================================
# DATABASE SCHEMA
# ===============================================================

def init_bandit_tables():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS real_time_metrics (
                variant_id TEXT PRIMARY KEY,
                test_type TEXT, -- 'headline' or 'thumbnail'
                test_id TEXT,
                impressions INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                ctr REAL DEFAULT 0.0,
                engagement REAL DEFAULT 0.0,
                read_time REAL DEFAULT 0.0,
                live_score REAL DEFAULT 0.0,
                traffic_share REAL DEFAULT 0.33,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

# ===============================================================
# TRAFFIC ALLOCATION (SOFTMAX BANDIT)
# ===============================================================

def calculate_traffic_shares(test_id: str, test_type: str = 'headline'):
    """
    Calculate traffic shares for variants using Softmax.
    TrafficShare = e^(Score/T) / Σ e^(Score/T)
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        # Get variants and their scores
        if test_type == 'headline':
            cur.execute("SELECT variant_id, variant_score, impressions FROM headline_variants WHERE test_id = ?", (test_id,))
        else:
            cur.execute("SELECT variant_id, thumbnail_score, impressions FROM thumbnail_variants WHERE test_id = ?", (test_id,))
            
        variants = cur.fetchall()
        if not variants: return

        # Phase 1: Cold Start (Exploration)
        total_imp = sum(v[2] for v in variants)
        if total_imp < MIN_EXPLORATION_IMPRESSIONS * len(variants):
            share = 1.0 / len(variants)
            for v in variants:
                _update_traffic_share(v[0], share)
            return

        # Phase 2: Exploitation (Softmax)
        scores = [v[1] for v in variants]
        # Normalize scores to prevent overflow in exp()
        max_score = max(scores) if scores else 0
        exp_scores = [math.exp((s - max_score) / TEMPERATURE) for s in scores]
        sum_exp = sum(exp_scores)
        
        shares = [s / sum_exp for s in exp_scores]
        
        # Apply simplified rules (Best: 50-70%, Second: 20-30%, etc)
        # We let Softmax handle this naturally, but we can clamp if needed
        for i, v in enumerate(variants):
            _update_traffic_share(v[0], shares[i])

def _update_traffic_share(variant_id: str, share: float):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE real_time_metrics SET traffic_share = ?, last_updated = CURRENT_TIMESTAMP WHERE variant_id = ?", (share, variant_id))
        conn.commit()

# ===============================================================
# REAL-TIME WINNER DETECTION
# ===============================================================

def detect_early_winner(test_id: str, test_type: str = 'headline') -> str:
    """
    Declare winner early if one variant is significantly better.
    Condition: Best Score > others by 25% AND min impressions reached.
    """
    with get_db() as conn:
        cur = conn.cursor()
        if test_type == 'headline':
            cur.execute("SELECT variant_id, variant_score, impressions FROM headline_variants WHERE test_id = ? ORDER BY variant_score DESC", (test_id,))
        else:
            cur.execute("SELECT variant_id, thumbnail_score, impressions FROM thumbnail_variants WHERE test_id = ? ORDER BY thumbnail_score DESC", (test_id,))
            
        variants = cur.fetchall()
        if len(variants) < 2: return None
        
        best = variants[0]
        second = variants[1]
        
        # Thresholds
        if best[2] < 50: return None # Min impressions for early win
        
        if second[1] == 0:
            if best[1] > 0: return best[0]
            return None
            
        improvement = (best[1] - second[1]) / second[1]
        
        if improvement > 0.30: # 30% lead
            print(f"[BANDIT] Early winner detected: {best[0]} with {improvement*100:.1f}% lead")
            return best[0]
            
    return None

# ===============================================================
# TRACKING BRIDGE
# ===============================================================

def sync_bandit_metrics(variant_id: str, test_type: str, test_id: str, impressions: int, clicks: int, score: float):
    """Update real_time_metrics table with latest data."""
    with get_db() as conn:
        cur = conn.cursor()
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        cur.execute("""
            INSERT INTO real_time_metrics (variant_id, test_type, test_id, impressions, clicks, ctr, live_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(variant_id) DO UPDATE SET
                impressions = excluded.impressions,
                clicks = excluded.clicks,
                ctr = excluded.ctr,
                live_score = excluded.live_score,
                last_updated = CURRENT_TIMESTAMP
        """, (variant_id, test_type, test_id, impressions, clicks, ctr, score))
        conn.commit()

def trigger_bandit_sync():
    """Maintenance: Recalculate all traffic shares."""
    print("[BANDIT] Triggering global sync...")
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT test_id, test_type FROM real_time_metrics")
        tests = cur.fetchall()
        for test_id, test_type in tests:
            calculate_traffic_shares(test_id, test_type)
    print("[BANDIT] Global sync completed.")

def initialize_bandit_engine():
    """Initialize real-time bandit tables from an application startup path."""
    init_bandit_tables()
