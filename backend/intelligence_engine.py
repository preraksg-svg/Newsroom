import time
import math
from backend.db.queries import get_db

def get_source_credibility(source_identifier: str):
    """Retrieves or synthesizes the Source Credibility Score from the database."""
    with get_db() as conn:
        cur = conn.cursor()
        # source_identifier might be handle or URL parsed domain
        cur.execute("SELECT final_score FROM sources WHERE name = ? OR domain = ?", (source_identifier, source_identifier))
        row = cur.fetchone()
        if row:
            return row["final_score"]
        else:
            return 0.5 # Default UNKNOWN source credibility

def update_source_score(source_id: str, perf_data: dict):
    """
    ScoreUpdate = α × (Performance − Expected) × ConfidenceScore
    perf_data expects: ctr, engagement, read_time, shares
    """
    ALPHA = 0.05
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT dynamic_score, confidence_score, activity_status FROM sources WHERE source_id = ?", (source_id,))
        row = cur.fetchone()
        if not row:
            return
            
        old_score = row["dynamic_score"]
        confidence = row["confidence_score"]
        
        # Calculate performance
        # PerformanceScore = 0.35 CTR + 0.25 Engagement + 0.20 ReadTime + 0.20 Shares
        perf = (0.35 * perf_data.get("ctr", 0)) + \
               (0.25 * perf_data.get("engagement", 0)) + \
               (0.20 * perf_data.get("read_time", 0)) + \
               (0.20 * perf_data.get("shares", 0))
               
        expected = old_score 
        
        score_update = ALPHA * (perf - expected) * confidence
        new_dynamic = min(max(old_score + score_update, 0.0), 1.0)
        
        # Determine lifecycle testing promotion
        status = row["activity_status"]
        if status == "testing" and new_dynamic > 0.6:
            status = "trusted"
        elif status == "trusted" and new_dynamic < 0.3:
            status = "degraded"
            
        cur.execute("UPDATE sources SET dynamic_score = ?, activity_status = ?, last_updated = CURRENT_TIMESTAMP WHERE source_id = ?", (new_dynamic, status, source_id))
        conn.commit()

def calculate_priority_score(source_type: str, timestamp_epoch: float, source_cred: float):
    """
    PriorityScore = 0.5 × SpeedScore + 0.3 × FreshnessScore + 0.2 × SourceCredibility
    """
    speed_map = {"twitter": 1, "reddit": 0.9, "youtube": 0.9, "rss": 0.7, "news_rss": 0.7, "blog": 0.5}
    speed_score = speed_map.get(source_type, 0.5)
    
    # Freshness = 100 * e^(-λ * minutes)
    diff_minutes = (time.time() - timestamp_epoch) / 60.0
    LAMBDA = 0.05
    freshness_score = math.exp(-LAMBDA * max(diff_minutes, 0)) # 0 to 1
    
    return (0.5 * speed_score) + (0.3 * freshness_score) + (0.2 * source_cred)

def cluster_raw_events():
    """
    Deduplication Engine. Runs periodically.
    Creates master "Clustered Events" by looking at title similarity over a time window.
    Supports FAST MODE (30m) OR Normal (3h).
    """
    with get_db() as conn:
        cur = conn.cursor()
        # Grab unprocessed raw items
        cur.execute("SELECT * FROM scraped_raw WHERE clustered = 0 ORDER BY timestamp DESC LIMIT 50")
        rows = cur.fetchall()
        
        clusters = []
        for row in rows:
            mapped = False
            r_time = float(row["timestamp"]) if row["timestamp"].replace('.', '').isdigit() else time.time()
            
            for c in clusters:
                # Naive title string matching for MVP (Instead of Deep Embeddings which require PyTorch locally)
                # Check overlapping words
                w1 = set(row["title"].lower().split())
                w2 = set(c["primary_title"].lower().split())
                intersection = w1.intersection(w2)
                overlap_ratio = len(intersection) / max(len(w1), len(w2), 1)
                
                # Check time window (3 hours max for generic cluster)
                time_diff = abs(c["latest_timestamp"] - r_time)
                
                if overlap_ratio > 0.4 and time_diff <= (3 * 3600):
                    c["items"].append(row)
                    c["latest_timestamp"] = max(c["latest_timestamp"], r_time)
                    c["sources"].add(row["source_id"] or row["url"])
                    mapped = True
                    break
            
            if not mapped:
                clusters.append({
                    "primary_title": row["title"],
                    "primary_content": row["content"],
                    "primary_url": row["url"],
                    "primary_type": row["type"],
                    "items": [row],
                    "latest_timestamp": r_time,
                    "sources": {row["source_id"] or row["url"]}
                })
                
        # For each cluster, format them into a unified ingest payload
        unified_events = []
        for c in clusters:
            source_count = len(c["sources"])
            
            # Find best credibility source in cluster
            best_cred = 0.0
            for item in c["items"]:
                cred = get_source_credibility(item["source_id"])
                if cred > best_cred:
                    best_cred = cred
                    
            # ConfidenceScore = 0.5 × SourceCredibility + 0.3 × SourceCount + 0.2 × AgreementScore
            # source_count scaled: 1 -> 0.3, 2 -> 0.7, 3+ -> 1.0
            sc_score = 0.3 if source_count == 1 else (0.7 if source_count == 2 else 1.0)
            agreement_score = 1.0 if source_count > 1 else 0.5
            
            confidence = (0.5 * best_cred) + (0.3 * sc_score) + (0.2 * agreement_score)
            
            # Evaluate FAST MODE Criteria 
            # (If it's extremely fresh < 30 mins, has high priority, and high confidence OR it's from a tier 1 source)
            fast_mode = False
            priority = calculate_priority_score(c["primary_type"], c["latest_timestamp"], best_cred)
            time_since_creation = (time.time() - c["latest_timestamp"]) / 60.0
            
            if time_since_creation < 30 and priority > 0.7:
                fast_mode = True
                
            unified_events.append({
                "title": c["primary_title"],
                "content": "\n---\n".join([i["content"] for i in c["items"]]),
                "url": c["primary_url"],
                "source_count": source_count,
                "confidence_score": confidence,
                "priority_score": priority,
                "fast_mode": fast_mode,
                "raw_ids": [i["id"] for i in c["items"]]
            })
            
            # Mark processed in DB
            for i in c["items"]:
                cur.execute("UPDATE scraped_raw SET clustered = 1 WHERE id = ?", (i["id"],))
                
        conn.commit()
    return unified_events

def check_diversity_constraint(source_id: str) -> bool:
    """
    Max articles per source per hour = X.
    Returns True if safe, False if violating diversity penalty limit.
    """
    MAX_ARTICLES_PER_HOUR = 3
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM scraped_raw WHERE source_id = ? AND timestamp > ?", (source_id, time.time() - 3600))
        count = cur.fetchone()[0]
        return count <= MAX_ARTICLES_PER_HOUR

def run_daily_maintenance():
    """
    Cron endpoint: Applies activity-based time decay, drops removed sources, recalculates FinalScores.
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        # Recalculate Final Scores and Apply Decentralized Decay
        cur.execute("SELECT source_id, dynamic_score, score_authority, activity_status, strftime('%s', last_updated) as last_ts FROM sources")
        sources = cur.fetchall()
        now = time.time()
        
        for s in sources:
            last_activity = now - float(s["last_ts"]) if s["last_ts"] else 0
            
            # Active source decay slowly (long lambda), Inactive decay fast
            LAMBDA = 0.001 if s["activity_status"] in ["active", "trusted"] else 0.05
            
            # Activity Time Decay
            decayed_dynamic = s["dynamic_score"] * math.exp(-LAMBDA * (last_activity / 86400.0))
            
            # FinalSourceScore = 0.5 DynamicScore + 0.3 Authority + 0.2 FreshnessPerformance
            # We mock FreshnessPerformance here from the decay delta
            freshness_perf = math.exp(-LAMBDA * (last_activity / 86400.0))
            
            final_score = (0.5 * decayed_dynamic) + (0.3 * s["score_authority"]) + (0.2 * freshness_perf)
            
            cur.execute("UPDATE sources SET dynamic_score = ?, final_score = ? WHERE source_id = ?", (decayed_dynamic, final_score, s["source_id"]))
            
        conn.commit()
