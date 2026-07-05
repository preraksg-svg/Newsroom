import json
import math
from datetime import datetime, timezone
from groq import Groq
import os
from dateutil import parser

from backend.llm import get_groq_client

KNOWN_PUBLISHERS = {
    "reuters": 95, "bloomberg": 95, "insideevs": 85, "electrek": 85, 
    "cleantechnica": 80, "teslarati": 75, "autocar": 80, "drive tesla": 70,
    "ev arena": 65
}

def analyze_article_heuristics(title, content):
    """Uses LLM to extract normalized [0-100] sub-scores for Intelligence and Virality."""
    sys_prompt = """You are the ZAPWAY Analytical Engine. 
Read the EV news article and return a strict JSON payload with structural heuristics.
Score everything from 0 to 100.
Do NOT include markdown wrapping like ```json. ONLY return valid JSON.

{
  "intelligence": {
    "topic_importance": 0,
    "novelty": 0,
    "data_richness": 0,
    "ecosystem_impact": 0,
    "technical_depth": 0
  },
  "virality": {
    "topic_trend": 0,
    "emotion": 0,
    "shareability": 0
  },
  "relevance": {
    "india_relevance": 0,
    "user_utility": 0,
    "category_importance": 0
  },
  "news_type": "Launch" // Launch, Policy, Event, Product, General
}"""
    
    user_prompt = f"TITLE: {title}\n\nCONTENT Snippet: {content[:2000]}"
    
    client = get_groq_client()
    if not client:
        print("Scoring Heuristic LLM Error: AI client unavailable.")
        # Fallback empty heuristic
        return {
            "intelligence": {"topic_importance": 50, "novelty": 50, "data_richness": 50, "ecosystem_impact": 50, "technical_depth": 50},
            "virality": {"topic_trend": 50, "emotion": 50, "shareability": 50},
            "relevance": {"india_relevance": 50, "user_utility": 50, "category_importance": 50},
            "news_type": "General"
        }

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1, # Highly deterministic
            response_format={"type": "json_object"}
        )
        res = json.loads(completion.choices[0].message.content)
        return res
    except Exception as e:
        print(f"Scoring Heuristic LLM Error: {e}")
        # Fallback empty heuristic
        return {
            "intelligence": {"topic_importance": 50, "novelty": 50, "data_richness": 50, "ecosystem_impact": 50, "technical_depth": 50},
            "virality": {"topic_trend": 50, "emotion": 50, "shareability": 50},
            "relevance": {"india_relevance": 50, "user_utility": 50, "category_importance": 50},
            "news_type": "General"
        }

def calculate_time_score(published_date_str):
    try:
        if not published_date_str:
            return 50 # Default decay penalty
        pub_dt = parser.parse(published_date_str)
        # Ensure timezone parsing safe
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        now_dt = datetime.now(timezone.utc)
        
        diff_hours = max((now_dt - pub_dt).total_seconds() / 3600.0, 0)
        # TimeScore = 100 * e^(-λ * Δt), λ ≈ 0.1
        LAMBDA = 0.1
        return 100 * math.exp(-LAMBDA * diff_hours)
    except:
        return 50


def run_scoring_engine(title, content, publisher, published_date):
    """The master mathematical deterministic routing matrix for ZAPWAY."""
    
    # Rule 4: Source Score (0.4 Authority + 0.25 Accuracy + 0.2 Speed + 0.15 India relevance)
    pub_base = KNOWN_PUBLISHERS.get(str(publisher).lower().strip(), 50)
    authority = pub_base
    accuracy = pub_base
    speed_source = 70 # Default proxy
    
    # Retrieve LLM Sub-metrics
    metrics = analyze_article_heuristics(title, content)
    india_rel = metrics.get("relevance", {}).get("india_relevance", 50)
    
    source_score = (0.4 * authority) + (0.25 * accuracy) + (0.2 * speed_source) + (0.15 * india_rel)
    
    # Time Sensitivity (Logarithmic Decay -> Freshness)
    freshness = calculate_time_score(published_date)
    speed_signal = freshness # Using freshness as proxy for speed signal currently
    
    # Rule 4: Priority Score (0.5 Speed + 0.3 Freshness + 0.2 SourceScore)
    priority_score = (0.5 * speed_signal) + (0.3 * freshness) + (0.2 * source_score)
    
    # Rule 4: Virality Score (0.4 TopicTrend + 0.3 Emotion + 0.3 Shareability)
    viral = metrics.get("virality", {})
    virality_score = (
        0.4 * viral.get("topic_trend", 50) +
        0.3 * viral.get("emotion", 50) +
        0.3 * viral.get("shareability", 50)
    )
    
    intel = metrics.get("intelligence", {})
    intel_score = (
        0.2 * intel.get("topic_importance", 50) +
        0.2 * intel.get("novelty", 50) +
        0.2 * intel.get("data_richness", 50) +
        0.2 * intel.get("ecosystem_impact", 50) +
        0.2 * intel.get("technical_depth", 50)
    )
    
    final_score = (priority_score + virality_score) / 2
    final_score = min(max(final_score, 0), 100)
    
    # 5. DECISION ENGINE
    decision = "Reject"
    priority = "Normal"
    
    # FAST MODE RULE: Priority Score threshold
    if priority_score > 85:
        decision = "BREAKING"
        priority = "Highest"
    else:
        if final_score >= 80:
            decision = "Auto-Draft"
            priority = "High"
        elif 70 <= final_score < 80:
            decision = "Draft"
            priority = "Normal"
        elif 50 <= final_score < 70:
            decision = "Review"
            priority = "Low"
        else:
            decision = "Reject"
            priority = "Stash"

    return {
        "intelligence": intel_score,
        "virality": virality_score,
        "time": freshness,
        "relevance": india_rel,
        "source": source_score,
        "priority_score": priority_score,
        "final_score": final_score,
        "decision": decision,
        "priority": priority,
        "news_type": metrics.get("news_type", "General")
    }

# Quick Test Function
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print("Testing ZAPWAY Scoring Algorithm Engine...")
    t_data = "Tesla is planning a massive 50% price cut on Megapacks in India starting next year."
    res = run_scoring_engine("Massive Tesla Drop", t_data, "Reuters", "2023-11-20T12:00:00Z")
    print(json.dumps(res, indent=2))
