"""
ZAPWAY Headline Pattern Library
================================
Learns, stores, and optimizes headline styles from real performance data.
Pattern -> Performance -> Weight -> Reuse
"""
import json
import re
import time
from backend.db.queries import get_db


# ===============================================================
# PATTERN TYPES
# ===============================================================

PATTERN_TYPES = {
    "breaking":    {"regex": r"(launches|unveils|reveals|announces|introduces|rolls out|debuts)", "template": "[Company] [Action] [Product/Feature]", "default_weight": 0.7},
    "contrarian":  {"regex": r"(why|despite|however|may slow|could fail|risk|challenges)", "template": "Why [Topic] May [Unexpected Outcome]", "default_weight": 0.5},
    "data_driven": {"regex": r"(\d+%|\d+ million|\d+ billion|\d+x|record|surge|growth|rise|fall|drop)", "template": "[Topic] [Metric] [Direction] [Number]", "default_weight": 0.6},
    "curiosity":   {"regex": r"(shocking|surprised|unexpected|secret|revealed|you won't believe|this)", "template": "This [Subject] [Surprising Action/Result]", "default_weight": 0.55},
    "impact":      {"regex": r"(could change|transforms|disrupts|game.changer|revolution|future|shift)", "template": "New [Subject] Could [Major Impact]", "default_weight": 0.6},
}


def init_headline_library():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS headline_library (
                id TEXT PRIMARY KEY,
                pattern_type TEXT NOT NULL,
                template TEXT,
                example TEXT,
                topic TEXT,
                keyword_slots TEXT,
                usage_count INTEGER DEFAULT 0,
                avg_performance REAL DEFAULT 0.0,
                weight REAL DEFAULT 0.5,
                best_ctr REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Seed initial patterns if empty
        cur.execute("SELECT COUNT(*) FROM headline_library")
        if cur.fetchone()[0] == 0:
            seeds = [
                ("hp_break_1", "breaking", "[Company] Launches [Product] in India", "Tesla Launches Model 2 in India", "Launch", '["company","product"]'),
                ("hp_break_2", "breaking", "[Company] Unveils [Feature] for [Market]", "BYD Unveils New Battery for Global Market", "Launch", '["company","feature","market"]'),
                ("hp_contra_1", "contrarian", "Why [Topic] May [Negative] Despite [Positive]", "Why EV Adoption May Slow Despite Record Sales", "Market", '["topic","outcome"]'),
                ("hp_data_1", "data_driven", "[Topic] [Direction] [Number] in [Period]", "EV Sales Rise 40% in Q1 2026", "Market", '["topic","number","period"]'),
                ("hp_data_2", "data_driven", "[Number] [Metric] Hit by [Subject]", "500 Charging Stations Added by Tata Power", "Charging", '["number","metric","subject"]'),
                ("hp_curio_1", "curiosity", "This [Subject] Test [Surprised/Shocked] Everyone", "This EV Range Test Shocked Everyone", "Tech", '["subject","reaction"]'),
                ("hp_impact_1", "impact", "New [Subject] Could [Impact] for [Audience]", "New EV Policy Could Transform Indian Market", "Policy", '["subject","impact","audience"]'),
                ("hp_impact_2", "impact", "[Subject] Set to [Disrupt/Change] [Industry]", "Solid-State Batteries Set to Disrupt EV Industry", "Tech", '["subject","action","industry"]'),
            ]
            for s in seeds:
                cur.execute("INSERT OR IGNORE INTO headline_library (id, pattern_type, template, example, topic, keyword_slots, weight) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (s[0], s[1], s[2], s[3], s[4], s[5], PATTERN_TYPES.get(s[1], {}).get("default_weight", 0.5)))
        conn.commit()
    print("[HEADLINE LIB] Pattern library initialized.")


# ===============================================================
# CLASSIFY HEADLINE TYPE
# ===============================================================

def classify_headline_type(headline: str) -> str:
    h = headline.lower()
    scores = {}
    for ptype, config in PATTERN_TYPES.items():
        if re.search(config["regex"], h, re.IGNORECASE):
            scores[ptype] = 1
    if not scores:
        return "breaking"  # default
    return max(scores, key=scores.get)


# ===============================================================
# STORE NEW PATTERN FROM REAL NEWS
# ===============================================================

def learn_headline_pattern(headline: str, topic: str = "EV"):
    ptype = classify_headline_type(headline)
    pid = f"hp_{ptype}_{abs(hash(headline)) % 999999}"

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM headline_library WHERE id = ?", (pid,))
        if cur.fetchone():
            cur.execute("UPDATE headline_library SET usage_count = usage_count + 1, last_used = CURRENT_TIMESTAMP WHERE id = ?", (pid,))
        else:
            # Extract a template from the real headline
            template = _extract_template(headline)
            cur.execute("""
                INSERT INTO headline_library (id, pattern_type, template, example, topic, keyword_slots, weight)
                VALUES (?, ?, ?, ?, ?, '[]', ?)
            """, (pid, ptype, template, headline, topic, PATTERN_TYPES.get(ptype, {}).get("default_weight", 0.5)))
        conn.commit()
    return ptype


def _extract_template(headline: str) -> str:
    """Convert a real headline into a reusable template."""
    t = headline
    # Replace specific entities with slots
    t = re.sub(r'\b(Tesla|BYD|Tata|Mahindra|Hyundai|Kia|Ola|Ather|BMW|MG|Rivian|Lucid)\b', '[Company]', t, flags=re.IGNORECASE)
    t = re.sub(r'\b(India|China|US|Europe|UK|Japan|Germany)\b', '[Market]', t, flags=re.IGNORECASE)
    t = re.sub(r'\d+%', '[Number]%', t)
    t = re.sub(r'\$?\d+[\.\d]* (billion|million|crore|lakh)', '[Amount]', t, flags=re.IGNORECASE)
    t = re.sub(r'\d{4}', '[Year]', t)
    return t


# ===============================================================
# GET BEST PATTERNS FOR GENERATION
# ===============================================================

def get_top_headline_patterns(topic: str = None, limit: int = 5) -> list:
    with get_db() as conn:
        cur = conn.cursor()
        if topic:
            cur.execute("""
                SELECT id, pattern_type, template, example, weight, avg_performance, usage_count
                FROM headline_library WHERE topic = ? OR topic = 'EV'
                ORDER BY weight DESC, avg_performance DESC LIMIT ?
            """, (topic, limit))
        else:
            cur.execute("""
                SELECT id, pattern_type, template, example, weight, avg_performance, usage_count
                FROM headline_library
                ORDER BY weight DESC, avg_performance DESC LIMIT ?
            """, (limit,))
        return [{"id": r[0], "type": r[1], "template": r[2], "example": r[3],
                 "weight": r[4], "performance": r[5], "used": r[6]} for r in cur.fetchall()]


def generate_headline_variations(title: str, content: str, topic: str = None) -> list:
    """
    Generate 2-3 headline variations using top patterns.
    Returns list of {headline, pattern_type, pattern_id, predicted_score}.
    """
    from backend.llm import get_groq_client
    from backend.db.queries import log_groq_usage

    client = get_groq_client()
    if not client:
        return [{"headline": title, "pattern_type": "original", "pattern_id": None, "predicted_score": 50}]

    top_patterns = get_top_headline_patterns(topic, limit=3)
    if not top_patterns:
        return [{"headline": title, "pattern_type": "original", "pattern_id": None, "predicted_score": 50}]

    patterns_text = "\n".join([f"- {p['type'].upper()}: \"{p['example']}\" (template: {p['template']}, weight: {p['weight']:.2f})" for p in top_patterns])

    prompt = f"""Generate exactly 3 headline variations for this EV news article.

NEWS TITLE: {title}
NEWS CONTENT: {content[:500]}

USE THESE HIGH-PERFORMING HEADLINE PATTERNS:
{patterns_text}

RULES:
- Each headline must use a DIFFERENT pattern type
- Keep factual accuracy
- Optimize for clicks + credibility
- Max 15 words each
- CRITICAL: ALWAYS complete your sentences. DO NOT leave generated headlines or texts cut off.

Return STRICT JSON:
{{
  "variations": [
    {{"headline": "...", "pattern_type": "...", "score_estimate": 0-100}},
    {{"headline": "...", "pattern_type": "...", "score_estimate": 0-100}},
    {{"headline": "...", "pattern_type": "...", "score_estimate": 0-100}}
  ]
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.5,
            max_completion_tokens=1200,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a headline optimization engine. Output strict JSON only."},
                {"role": "user", "content": prompt}
            ]
        )
        if hasattr(response, 'usage') and response.usage:
            log_groq_usage(response.usage.total_tokens)

        data = json.loads(response.choices[0].message.content)
        variations = data.get("variations", [])

        # Attach pattern IDs
        for v in variations:
            matched = next((p for p in top_patterns if p["type"] == v.get("pattern_type")), None)
            v["pattern_id"] = matched["id"] if matched else None

        return variations
    except Exception as e:
        print(f"[HEADLINE LIB] Variation generation error: {e}")
        return [{"headline": title, "pattern_type": "original", "pattern_id": None, "score_estimate": 50}]


def pick_best_headline(variations: list) -> dict:
    """Pick the highest-scoring variation."""
    if not variations:
        return {"headline": "", "pattern_type": "none", "score_estimate": 0}
    return max(variations, key=lambda v: v.get("score_estimate", 0))


# ===============================================================
# LEARNING LOOP — Update after publish
# ===============================================================

HEADLINE_ALPHA = 0.1

def update_headline_performance(pattern_id: str, ctr: float, engagement: float, shares: float):
    """
    PatternScore = 0.4 × CTR + 0.3 × Engagement + 0.3 × Shares
    """
    score = 0.4 * ctr + 0.3 * engagement + 0.3 * shares
    normalized = min(score / 100.0, 1.0)

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT weight, avg_performance, usage_count FROM headline_library WHERE id = ?", (pattern_id,))
        row = cur.fetchone()
        if not row:
            return

        old_weight = row[0]
        old_perf = row[1]
        count = row[2]

        new_perf = (old_perf * count + normalized) / (count + 1) if count > 0 else normalized
        new_weight = old_weight + HEADLINE_ALPHA * (normalized - old_weight)
        new_weight = max(0.1, min(1.0, new_weight))

        cur.execute("""
            UPDATE headline_library SET
                avg_performance = ?,
                weight = ?,
                best_ctr = CASE WHEN best_ctr < ? THEN ? ELSE best_ctr END,
                usage_count = usage_count + 1,
                last_used = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_perf, new_weight, ctr, ctr, pattern_id))
        conn.commit()


def initialize_headline_engine():
    """Initialize headline learning tables from the application startup path."""
    init_headline_library()
