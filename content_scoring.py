"""
ZAPWAY Content Scoring Engine (Pre-Publish)
=============================================
Predicts article performance BEFORE publishing.
Uses 5 sub-scores to compute a composite ContentScore.

ContentScore =
  0.30 × HeadlineScore +
  0.25 × TopicTrend +
  0.20 × Readability +
  0.15 × SourceCredibility +
  0.10 × Freshness

Decision:
  < 60  → Reject / Regenerate
  60-75 → Improve (flag for review)
  > 75  → Approve for publish
"""
import re
import time
import json
import math
from backend.db.queries import get_db


# ===============================================================
# SUB-SCORE 1: HEADLINE SCORE
# ===============================================================

# Optimal headline length range (words)
OPTIMAL_HEADLINE_MIN = 7
OPTIMAL_HEADLINE_MAX = 14

# Power keywords that boost CTR
POWER_KEYWORDS = [
    "exclusive", "breaking", "new", "first", "revealed", "leaked",
    "shocking", "record", "launch", "massive", "urgent", "official",
    "confirmed", "biggest", "fastest", "cheapest"
]

# EV-specific high-value keywords
EV_KEYWORDS = [
    "tesla", "byd", "ev", "electric", "battery", "charging", "range",
    "subsidy", "policy", "tata", "mahindra", "ola", "ather", "hyundai"
]


def compute_headline_score(headline: str) -> dict:
    words = headline.split()
    word_count = len(words)
    h_lower = headline.lower()

    # Length optimization (0-25 pts)
    if OPTIMAL_HEADLINE_MIN <= word_count <= OPTIMAL_HEADLINE_MAX:
        length_score = 25
    elif word_count < OPTIMAL_HEADLINE_MIN:
        length_score = max(5, 25 - (OPTIMAL_HEADLINE_MIN - word_count) * 5)
    else:
        length_score = max(5, 25 - (word_count - OPTIMAL_HEADLINE_MAX) * 3)

    # Power keyword boost (0-25 pts)
    power_hits = sum(1 for kw in POWER_KEYWORDS if kw in h_lower)
    keyword_score = min(25, power_hits * 10)

    # EV relevance (0-25 pts)
    ev_hits = sum(1 for kw in EV_KEYWORDS if kw in h_lower)
    ev_score = min(25, ev_hits * 8)

    # Has number (data-driven headlines perform better)
    number_bonus = 10 if re.search(r'\d', headline) else 0

    # Pattern performance from library
    pattern_bonus = 0
    try:
        from headline_engine import classify_headline_type, get_top_headline_patterns
        htype = classify_headline_type(headline)
        patterns = get_top_headline_patterns(limit=1)
        if patterns and patterns[0]["type"] == htype:
            pattern_bonus = int(patterns[0]["weight"] * 15)
    except:
        pass

    raw = length_score + keyword_score + ev_score + number_bonus + pattern_bonus
    final = min(100, raw)

    return {
        "score": final,
        "length_score": length_score,
        "keyword_score": keyword_score,
        "ev_relevance": ev_score,
        "number_bonus": number_bonus,
        "pattern_bonus": pattern_bonus
    }


# ===============================================================
# SUB-SCORE 2: TOPIC TREND
# ===============================================================

def compute_topic_trend(topic: str, title: str) -> dict:
    score = 50  # Base score

    try:
        # Check trend_memory for velocity
        with get_db() as conn:
            cur = conn.cursor()

            # Check if topic is actively trending
            cur.execute("""
                SELECT signal_count, velocity FROM trend_memory
                WHERE topic LIKE ? AND is_active = 1
                ORDER BY velocity DESC LIMIT 1
            """, (f"%{topic}%",))
            row = cur.fetchone()

            if row:
                signals = row[0]
                velocity = row[1]
                # More signals + higher velocity = better trend score
                trend_boost = min(30, signals * 3 + velocity * 5)
                score += trend_boost

            # Check topic_clusters for historical performance
            cur.execute("SELECT avg_performance, article_count FROM topic_clusters WHERE topic = ?", (topic,))
            cluster = cur.fetchone()
            if cluster:
                perf = cluster[0] or 0
                count = cluster[1] or 0
                history_boost = min(20, perf * 20 + min(10, count))
                score += history_boost

    except Exception:
        pass

    return {"score": min(100, max(0, score)), "topic": topic}


# ===============================================================
# SUB-SCORE 3: READABILITY
# ===============================================================

def compute_readability(content: str, sections: list = None) -> dict:
    sentences = re.split(r'[.!?]+', content)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    words = content.split()
    word_count = len(words)

    # Average sentence length (target: 15-20 words)
    avg_sentence_len = word_count / max(len(sentences), 1)
    if 12 <= avg_sentence_len <= 22:
        sentence_score = 30
    elif avg_sentence_len < 12:
        sentence_score = 20
    else:
        sentence_score = max(10, 30 - int((avg_sentence_len - 22) * 2))

    # Structure quality (has sections with headings)
    section_count = len(sections) if sections else 0
    if section_count >= 3:
        structure_score = 30
    elif section_count >= 2:
        structure_score = 20
    elif section_count >= 1:
        structure_score = 10
    else:
        structure_score = 5

    # Word count target (600-1200 optimal)
    if 600 <= word_count <= 1200:
        length_score = 25
    elif 400 <= word_count < 600:
        length_score = 15
    elif word_count > 1200:
        length_score = 20
    else:
        length_score = max(5, word_count // 40)

    # Paragraph breaks (good formatting)
    para_count = content.count('\n\n') + content.count('<p>') + 1
    format_score = min(15, para_count * 3)

    raw = sentence_score + structure_score + length_score + format_score
    return {
        "score": min(100, raw),
        "avg_sentence_length": round(avg_sentence_len, 1),
        "word_count": word_count,
        "section_count": section_count,
        "paragraph_count": para_count
    }


# ===============================================================
# SUB-SCORE 4: SOURCE CREDIBILITY
# ===============================================================

def compute_source_credibility(source_url: str, publisher: str = "") -> dict:
    score = 50  # Base

    try:
        from urllib.parse import urlparse
        domain = urlparse(source_url).netloc.lower().replace("www.", "")

        # Tier 1 sources (maximum credibility)
        tier1 = ["reuters.com", "bloomberg.com", "economictimes.com", "livemint.com",
                 "autocarindia.com", "carandbike.com", "overdrive.in", "ndtv.com",
                 "thehindu.com", "moneycontrol.com"]
        tier2 = ["electrek.co", "insideevs.com", "cleantechnica.com", "teslarati.com",
                 "topgear.com", "motortrend.com", "carbuzz.com"]

        if any(t in domain for t in tier1):
            score = 90
        elif any(t in domain for t in tier2):
            score = 75
        else:
            # Check dynamic score from worker_memory
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT worker_score FROM worker_memory WHERE source_id LIKE ? LIMIT 1", (f"%{domain}%",))
                row = cur.fetchone()
                if row:
                    score = int(row[0] * 100)
    except:
        pass

    return {"score": min(100, max(10, score))}


# ===============================================================
# SUB-SCORE 5: FRESHNESS
# ===============================================================

def compute_freshness(published_timestamp: str = "") -> dict:
    try:
        pub_time = float(published_timestamp)
    except:
        pub_time = time.time()

    hours_old = (time.time() - pub_time) / 3600

    if hours_old < 1:
        score = 100
    elif hours_old < 6:
        score = 85
    elif hours_old < 24:
        score = 70
    elif hours_old < 48:
        score = 50
    elif hours_old < 72:
        score = 30
    else:
        # Exponential decay after 72h
        score = max(5, int(30 * math.exp(-0.02 * (hours_old - 72))))

    return {"score": score, "hours_old": round(hours_old, 1)}


# ===============================================================
# COMPOSITE CONTENT SCORE
# ===============================================================

def compute_content_score(headline: str, content: str, topic: str = "EV",
                          source_url: str = "", publisher: str = "",
                          published_timestamp: str = "", sections: list = None) -> dict:
    """
    ContentScore =
      0.30 × HeadlineScore +
      0.25 × TopicTrend +
      0.20 × Readability +
      0.15 × SourceCredibility +
      0.10 × Freshness
    """
    hs = compute_headline_score(headline)
    tt = compute_topic_trend(topic, headline)
    rd = compute_readability(content, sections)
    sc = compute_source_credibility(source_url, publisher)
    fr = compute_freshness(published_timestamp)

    composite = (
        0.30 * hs["score"] +
        0.25 * tt["score"] +
        0.20 * rd["score"] +
        0.15 * sc["score"] +
        0.10 * fr["score"]
    )

    # Decision
    if composite >= 75:
        decision = "APPROVE"
    elif composite >= 60:
        decision = "IMPROVE"
    else:
        decision = "REJECT"

    return {
        "content_score": round(composite, 1),
        "decision": decision,
        "sub_scores": {
            "headline": hs,
            "topic_trend": tt,
            "readability": rd,
            "source_credibility": sc,
            "freshness": fr
        }
    }


# ===============================================================
# LEARNING: Compare predicted vs actual
# ===============================================================

SCORING_ALPHA = 0.05

# Weight calibration storage
_weight_adjustments = {
    "headline": 0.30,
    "topic_trend": 0.25,
    "readability": 0.20,
    "source_credibility": 0.15,
    "freshness": 0.10
}


def calibrate_scoring_weights(predicted_score: float, actual_performance: float):
    """
    After publish: compare predicted vs actual.
    Adjust scoring weights to reduce prediction error over time.
    """
    error = actual_performance - predicted_score
    # Positive error = we underestimated → boost weights of sub-scores that contributed
    # Negative error = we overestimated → reduce weights
    # For now, log the error for manual analysis
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scoring_calibration (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    predicted REAL,
                    actual REAL,
                    error REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("INSERT INTO scoring_calibration (predicted, actual, error) VALUES (?, ?, ?)",
                        (predicted_score, actual_performance, error))
            conn.commit()

            # If we have enough data, compute average error direction
            cur.execute("SELECT AVG(error) FROM scoring_calibration WHERE timestamp > datetime('now', '-7 days')")
            avg_error = cur.fetchone()[0]
            if avg_error is not None:
                print(f"[CONTENT SCORE] 7-day avg prediction error: {avg_error:.2f} (positive = underestimating)")
    except Exception as e:
        print(f"[CONTENT SCORE] Calibration error: {e}")


print("[CONTENT SCORE] Engine initialized.")
