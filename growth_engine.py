"""
ZAPWAY Growth Engine
====================
Calculates GrowthScore, tracks traffic, and drives the content flywheel.
GrowthScore = 0.4*traffic + 0.3*CTR + 0.2*shares + 0.1*engagement
"""
from backend.db.queries import get_db
import time

def init_growth_metrics(story_id: str):
    """Initialize growth metrics for a new article."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO growth_metrics (story_id, traffic_total, ctr_avg, shares_total, engagement_rate, growth_score)
            VALUES (?, 0, 0.0, 0, 0.0, 0.0)
        """, (story_id,))
        conn.commit()

def update_growth_metrics(story_id: str, traffic: int = 0, ctr: float = 0.0, shares: int = 0, engagement: float = 0.0):
    """Update metrics and recalculate GrowthScore."""
    with get_db() as conn:
        cur = conn.cursor()
        
        # Get existing or init
        cur.execute("SELECT traffic_total, ctr_avg, shares_total, engagement_rate FROM growth_metrics WHERE story_id = ?", (story_id,))
        row = cur.fetchone()
        
        if row:
            new_traffic = row[0] + traffic
            new_shares = row[2] + shares
            # Exponential moving average for CTR and Engagement
            ALPHA = 0.3
            new_ctr = row[1] * (1 - ALPHA) + ctr * ALPHA if row[1] > 0 else ctr
            new_eng = row[3] * (1 - ALPHA) + engagement * ALPHA if row[3] > 0 else engagement
        else:
            new_traffic = traffic
            new_shares = shares
            new_ctr = ctr
            new_eng = engagement

        # GrowthScore calculation
        norm_traffic = min(new_traffic / 10000, 1.0) * 100
        norm_shares = min(new_shares / 500, 1.0) * 100
        
        growth_score = (0.4 * norm_traffic) + (0.3 * new_ctr) + (0.2 * norm_shares) + (0.1 * new_eng)
        
        cur.execute("""
            INSERT OR REPLACE INTO growth_metrics 
            (story_id, traffic_total, ctr_avg, shares_total, engagement_rate, growth_score, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (story_id, new_traffic, new_ctr, new_shares, new_eng, growth_score))
        
        # Sync to stories table
        cur.execute("UPDATE stories SET growth_score = ? WHERE id = ?", (growth_score, story_id))
        
        conn.commit()
    
    return growth_score

def get_top_growth_signals(limit: int = 10):
    """Get articles with highest growth scores for learning."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT s.id, s.title, g.growth_score, g.traffic_total, g.shares_total
            FROM stories s
            JOIN growth_metrics g ON s.id = g.story_id
            ORDER BY g.growth_score DESC LIMIT ?
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]

def learn_growth_patterns():
    """Analyze high-growth articles to extract successful keywords/patterns."""
    # Logic to extract keywords from titles and update growth_patterns table
    pass
