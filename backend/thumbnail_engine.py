"""
ZAPWAY Auto Thumbnail Engine
==============================
Generates strategic thumbnail variations based on visual strategies.
Learns which styles perform best for specific topics.
"""
import json
import time
import random
from backend.db.queries import get_db

# ===============================================================
# THUMBNAIL STRATEGIES
# ===============================================================

STRATEGIES = {
    "CLEAN_NEWS": {
        "description": "Minimal text, Car/product focus, Professional",
        "prompt_suffix": "professional car photography, studio lighting, high-end commercial style, clean background, 8k resolution, minimalist, news style",
        "text_style": "minimalist overlay, subtle bottom text"
    },
    "HIGH_CONTRAST": {
        "description": "Bold colors, Highlight key element, Emotion/impact",
        "prompt_suffix": "high contrast, vibrant colors, dramatic lighting, bold composition, cinematic impact, attention-grabbing, vivid saturation",
        "text_style": "bold neon text, large font, high impact"
    },
    "DATA_INFO": {
        "description": "Numbers, Charts, Informational overlay",
        "prompt_suffix": "infographic style, data visualization elements, charts and numbers overlay, technical drawing background, informative and clear",
        "text_style": "statistical callouts, data points, technical labels"
    }
}

# ===============================================================
# STYLE LEARNING SYSTEM
# ===============================================================

def init_style_weights():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS thumbnail_style_weights (
                style_type TEXT PRIMARY KEY,
                weight REAL DEFAULT 1.0,
                avg_ctr REAL DEFAULT 0.0,
                test_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Seed initial weights
        for style in STRATEGIES.keys():
            cur.execute("INSERT OR IGNORE INTO thumbnail_style_weights (style_type) VALUES (?)", (style,))
        conn.commit()

def update_style_weight(style_type: str, performance: float, expected: float = 0.05):
    """
    Update style weight based on performance vs expected.
    StyleWeight = OldWeight + alpha * (Performance - Expected)
    """
    alpha = 0.1
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT weight, avg_ctr, test_count FROM thumbnail_style_weights WHERE style_type = ?", (style_type,))
        row = cur.fetchone()
        if not row: return

        old_weight, old_ctr, count = row
        new_count = count + 1
        new_ctr = (old_ctr * count + performance) / new_count
        
        # Simple reinforcement
        diff = performance - expected
        new_weight = max(0.1, old_weight + alpha * diff)
        
        cur.execute("""
            UPDATE thumbnail_style_weights 
            SET weight = ?, avg_ctr = ?, test_count = ?, last_updated = CURRENT_TIMESTAMP
            WHERE style_type = ?
        """, (new_weight, new_ctr, new_count, style_type))
        conn.commit()

# ===============================================================
# PROMPT GENERATION
# ===============================================================

def generate_thumbnail_prompts(headline: str, summary: str, topic: str = "EV") -> list:
    """
    Generate prompts for 3 different thumbnail variations.
    """
    prompts = []
    for style_type, config in STRATEGIES.items():
        # Build base prompt using LLM logic (simplified here for integration)
        base_subject = headline.split(":")[0] if ":" in headline else headline
        
        prompt = f"Create a thumbnail for EV news: {base_subject}. "
        prompt += f"Style: {config['description']}. "
        prompt += f"Visuals: {config['prompt_suffix']}. "
        
        # Add text instructions
        if style_type == "HIGH_CONTRAST":
            prompt += "Include bold text: 'NEW' or 'SHOCKING'."
        elif style_type == "DATA_INFO":
            prompt += "Include 40% growth chart or numbers."
            
        prompts.append({
            "style_type": style_type,
            "prompt": prompt,
            "text_style": config["text_style"]
        })
    
    return prompts

# ===============================================================
# IMAGE GENERATION MOCK (Real system would call DALL-E / SD)
# ===============================================================

def mock_generate_images(prompts: list) -> list:
    """
    Mock function to simulate image generation.
    In production, this would call an external API.
    """
    results = []
    for p in prompts:
        # For now, we use a placeholder or a deterministic URL
        # In a real system, this returns the URL of the generated image
        variant_id = f"thumb_{int(time.time())}_{random.randint(1000, 9999)}"
        results.append({
            "variant_id": variant_id,
            "style_type": p["style_type"],
            "image_url": f"/static/thumbnails/placeholder_{p['style_type'].lower()}.jpg",
            "prompt": p["prompt"]
        })
    return results

def get_best_styles(limit: int = 2) -> list:
    """Get top performing styles to prioritize generation."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT style_type, weight FROM thumbnail_style_weights ORDER BY weight DESC LIMIT ?", (limit,))
        return [row[0] for row in cur.fetchall()]

def initialize_thumbnail_engine():
    """Initialize thumbnail learning tables from the application startup path."""
    init_style_weights()
    print("[THUMBNAIL ENGINE] Initialized.")
