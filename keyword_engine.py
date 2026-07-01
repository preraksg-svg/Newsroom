"""
ZAPWAY Keyword Strategy Engine
==============================
Implements 5-layer keyword strategy for India EV market.
Layers: Breaking, Trending, Buyer Intent, Location-Based, Educational.
"""
from backend.db.queries import get_db
import json
import re

class KeywordEngine:
    LAYERS = {
        "BREAKING": "Layer 1: Capture spikes (Tata EV launch, Ola update)",
        "TRENDING": "Layer 2: Cluster search (EV battery life, fire issues)",
        "BUYER": "Layer 3: High conversion (Best EV under 10L, EV vs Petrol)",
        "LOCATION": "Layer 4: Programmatic (EV charging in Mumbai, Delhi)",
        "EDUCATIONAL": "Layer 5: Myth-busting (Are EVs safe, battery life)"
    }

    CITIES = ["Mumbai", "Delhi", "Bangalore", "Pune", "Hyderabad", "Chennai"]
    STATES = ["Maharashtra", "Karnataka", "Tamil Nadu", "Gujarat"]

    @staticmethod
    def generate_keyword_strategy(title, content, news_type="EV"):
        """
        Generate primary, secondary, and long-tail keywords for an article.
        """
        # 1. Extract base terms
        base_term = title.lower().replace("launch", "").replace("new", "").strip()
        
        # 2. Layer 1: Primary (Breaking/Contextual)
        primary = f"{base_term} launch 2026" if "launch" in title.lower() else base_term
        
        # 3. Layer 2 & 3: Secondary Keywords
        secondary = [
            f"{base_term} price in india",
            f"{base_term} range",
            f"{base_term} features",
            f"best {news_type} car india",
            f"{news_type} subsidy india"
        ]
        
        # 4. Layer 4 & 5: Long-tail
        long_tail = [
            f"{base_term} vs petrol cost comparison",
            f"is {base_term} safe for long drives in india",
            f"{base_term} charging time and cost"
        ]
        
        # 5. Geo-targeting (Location-based)
        geo_keywords = []
        for city in KeywordEngine.CITIES[:2]:
            geo_keywords.append(f"{base_term} available in {city}")
            
        return {
            "primary": primary,
            "secondary": secondary,
            "long_tail": long_tail,
            "geo": geo_keywords
        }

    @staticmethod
    def calculate_keyword_score(intent=0.8, trend=0.7, competition=0.4, relevance=0.9):
        """
        KeywordScore = 0.4 Intent + 0.3 Trend + 0.2 Competition + 0.1 Relevance
        """
        return (0.4 * intent) + (0.3 * trend) + (0.2 * (1 - competition)) + (0.1 * relevance)

    @staticmethod
    def map_content_type(layer):
        mapping = {
            "BREAKING": "News Article",
            "TRENDING": "Explainer",
            "BUYER": "Comparison",
            "LOCATION": "Programmatic Page",
            "EDUCATIONAL": "Guide"
        }
        return mapping.get(layer, "News")

def generate_keyword_faq(keyword):
    """
    Auto-generate FAQs for a specific keyword.
    """
    return [
        {"q": f"What is {keyword}?", "a": f"{keyword} is a key topic in the Indian EV market focus on efficiency and sustainability."},
        {"q": f"Why is {keyword} important for India?", "a": "As India shifts towards green mobility, understanding this topic helps buyers make informed decisions."},
        {"q": f"How does {keyword} affect EV prices?", "a": "It influences market trends, manufacturing costs, and government subsidies."}
    ]

def get_internal_links_strategy(article_id, primary_keyword):
    """
    Each article links to 2 related news, 1 programmatic, 1 buyer-intent.
    """
    # Placeholder logic to return link types
    return [
        {"type": "news", "label": "Related News 1"},
        {"type": "news", "label": "Related News 2"},
        {"type": "programmatic", "label": f"EV Charging in India"},
        {"type": "buyer", "label": "Best EV Cars under 10 Lakh"}
    ]
