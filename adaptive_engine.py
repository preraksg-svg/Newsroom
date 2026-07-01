import json
import os
import time
from groq import Groq
from backend.db.queries import get_db

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def extract_input_features(title, content):
    """
    Extracts the structured feature vector.
    """
    sys_prompt = """You are the Feature Extractor.
Extract the structural attributes of this input text.
Return ONLY valid JSON.

FORMAT:
{
  "headline_features": {
    "length": 0, // Number of words
    "power_words_score": 0.0, // 0.0 to 1.0 based on impact
    "curiosity_score": 0.0 // 0.0 to 1.0
  },
  "content_features": {
    "structure_type": "standard", // e.g., insight_heavy, breaking_news
    "section_count": 0,
    "readability": 0.0 // 0.0 to 1.0
  },
  "topic_features": {
    "category": "ev", 
    "trend_score": 0.0 // 0.0 to 1.0
  },
  "media_features": {
    "visual_score": 0.0 // 0.0 to 1.0 (visual potential)
  }
}"""
    
    user_prompt = f"TITLE: {title}\n\nCONTENT: {content[:1000]}"
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"Feature Extraction Error: {e}")
        return {
            "headline_features": {"length": 5, "power_words_score": 0.5, "curiosity_score": 0.5},
            "content_features": {"structure_type": "standard", "section_count": 3, "readability": 0.5},
            "topic_features": {"category": "general", "trend_score": 0.5},
            "media_features": {"visual_score": 0.5}
        }

def performance_predictor(feature_vector):
    """
    y = Σ (Wi × Featurei)
    Retrieves current weights from sqlite to multiply against extracted features.
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT feature, weight FROM model_weights")
        weights = {row["feature"]: row["weight"] for row in cur.fetchall()}
    
    score = 0.0
    try:
        # Flatten vector and multiply
        score += feature_vector["headline_features"]["length"] * weights.get("headline.length", 0.0)
        score += feature_vector["headline_features"]["power_words_score"] * weights.get("headline.power_words_score", 0.0)
        score += feature_vector["headline_features"]["curiosity_score"] * weights.get("headline.curiosity_score", 0.0)
        score += feature_vector["content_features"]["readability"] * weights.get("content.readability", 0.0)
        score += feature_vector["topic_features"]["trend_score"] * weights.get("topic.trend_score", 0.0)
        score += feature_vector["media_features"]["visual_score"] * weights.get("media.visual_score", 0.0)
    except KeyError:
        pass
        
    # Cap score at 1.0 or 100 based on preference
    return min(max(score, 0.0), 1.0) 

def fetch_rag_patterns():
    """
    Retrieves the top-performing patterns logic simulation.
    Uses SQlite ORDER BY score DESC as a stand-in for Pinecone Top K.
    """
    patterns = {"headline": [], "hook": [], "structure": [], "template": []}
    with get_db() as conn:
        cur = conn.cursor()
        for ptype in patterns.keys():
            cur.execute("SELECT pattern FROM pattern_memory WHERE type = ? ORDER BY score DESC LIMIT 3", (ptype,))
            rows = cur.fetchall()
            patterns[ptype] = [row["pattern"] for row in rows]
    return patterns

def policy_engine(predicted_score, feature_vector, rag_patterns):
    """
    Policy = argmax(ExpectedReward | Features, PastLearning)
    Returns string recommendations to pass dynamically into the llm generator prompt.
    """
    policy = {
        "recommended_headline_style": rag_patterns["headline"][0] if rag_patterns["headline"] else "curiosity_gap",
        "recommended_structure": rag_patterns["structure"][0] if rag_patterns["structure"] else "event → breakdown → implication",
        "recommended_tone": "insight_heavy" if predicted_score < 0.5 else "viral_short",
        "target_audience": "Advanced EV owners" if feature_vector["content_features"].get("readability", 0) < 0.6 else "General public"
    }
    return policy

def record_learning_prediction(story_id, feature_vector, predicted_score):
    """Saves to learning_predictions table for posterior async update."""
    with get_db() as conn:
        cur = conn.cursor()
        pid = f"pred_{int(time.time() * 1000)}"
        cur.execute(
            "INSERT INTO learning_predictions (id, story_id, feature_vector, predicted_engagement) VALUES (?, ?, ?, ?)",
            (pid, story_id, json.dumps(feature_vector), predicted_score)
        )
        conn.commit()

def apply_pattern_decay():
    """
    PatternScore = PatternScore × e^(-λt)
    Run periodically (e.g. daily)
    """
    LAMBDA = 0.05
    with get_db() as conn:
        cur = conn.cursor()
        # Just reducing all scores slightly for decay to simulate time passing
        cur.execute("UPDATE pattern_memory SET score = score * ?", (2.71828 ** -LAMBDA,))
        conn.commit()

def update_learning_weights(story_id, actual_reward):
    """
    Wi = Wi + α × Error × Featurei
    Called from API when performance stats are received.
    """
    ALPHA = 0.01
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT feature_vector, predicted_engagement FROM learning_predictions WHERE story_id = ?", (story_id,))
        row = cur.fetchone()
        if not row:
            return False
            
        features = json.loads(row["feature_vector"])
        # predicted_engagement is 0.0 to 1.0. Let's assume actual_reward is also scaled 0.0 to 1.0.
        predicted = row["predicted_engagement"]
        error = actual_reward - predicted
        
        # We need to flatten features to match weights
        flat_feats = {
            "headline.length": features.get("headline_features", {}).get("length", 0),
            "headline.power_words_score": features.get("headline_features", {}).get("power_words_score", 0),
            "headline.curiosity_score": features.get("headline_features", {}).get("curiosity_score", 0),
            "content.readability": features.get("content_features", {}).get("readability", 0),
            "topic.trend_score": features.get("topic_features", {}).get("trend_score", 0),
            "media.visual_score": features.get("media_features", {}).get("visual_score", 0)
        }
        
        # Fetch current weights
        cur.execute("SELECT feature, weight FROM model_weights")
        weights = {r["feature"]: r["weight"] for r in cur.fetchall()}
        
        for k, f_val in flat_feats.items():
            current_w = weights.get(k, 0.0)
            new_w = current_w + (ALPHA * error * f_val)
            # Update DB
            cur.execute("INSERT OR REPLACE INTO model_weights (feature, weight) VALUES (?, ?)", (k, new_w))
            
        cur.execute("UPDATE learning_predictions SET actual_reward = ?, status = 'processed' WHERE story_id = ?", (actual_reward, story_id))
        conn.commit()
    return True

