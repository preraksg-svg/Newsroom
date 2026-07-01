"""
ZAPWAY Social Distribution Engine
=================================
Generates viral social content: Tweets, LinkedIn, Reels Scripts, and Carousels.
"""
import json

def generate_viral_bundle(title, summary, news_type="EV"):
    """Generate a full social media package for an article using LLM."""
    from backend.llm import get_groq_client, log_groq_usage
    
    title_clean = title.replace('"', "'")
    summary_clean = summary.replace('"', "'") if summary else ""
    
    client = get_groq_client()
    
    import re
    ev_companies = ["Tata", "Mahindra", "Ola", "Ather", "Tesla", "BYD", "Hyundai", "MG Motor", "TVS"]
    matched_company = None
    for company in ev_companies:
        if company.lower() in title_clean.lower():
            matched_company = company
            break
    topic = matched_company if matched_company else "EV"

    if not client:
        return {
            "tweet": {
                "text": (
                    f"🧵 1/3: {title_clean} ⚡\n"
                    f"This major {topic} announcement is accelerating clean mobility adoption. Core details below: 👇 #EVNews #Zapway #{topic}EV\n\n"
                    f"2/3: Key developments show optimized supply chain execution, localized manufacturing, and battery tech advancements that lower TCO.\n\n"
                    f"3/3: Ultimately, this drives convenience with charging infrastructure expansions and direct-to-consumer savings."
                ),
                "hook": f"The electric vehicle market is shifting quickly with this {topic} update."
            },
            "linkedin": {
                "headline": f"In-Depth Analysis: How {title_clean} Redefines EV Mobility", 
                "body": (
                    f"⚡ THE ANNOUNCEMENT\n"
                    f"Recent updates around {topic} mark a major milestone in clean tech transportation. {title_clean}.\n\n"
                    f"📈 KEY IMPLICATIONS\n"
                    f"- Supply Chain Optimization: Localizing parts to drive down costs.\n"
                    f"- Technology Maturation: Enhanced battery/charging integration for range.\n"
                    f"- Market Viability: Driving consumer transition from ICE to EV.\n\n"
                    f"🔮 ZAPWAY'S TAKE\n"
                    f"This shift indicates the market is moving into mass viability. As infrastructure scales, TCO parity becomes reality. Read more on ZAPWAY."
                ),
                "hook": f"Important news regarding {topic} EV strategy."
            },
            "reel_script": {"hook": "Wait...", "scenes": []},
            "carousel": []
        }

    prompt = f"""
    Generate an in-depth, high-converting social media bundle for this EV news:
    Title: {title_clean}
    Summary: {summary_clean}
    
    CRITICAL RULES FOR TWITTER/X (IN-DEPTH):
    - Do NOT generate a simple one-sentence overview. Create a structured 3-part thread (or a highly detailed multi-part tweet text block).
    - Part 1 must hook the reader and announce the news.
    - Part 2 must detail key figures, numbers, or technical/supply developments.
    - Part 3 must focus on driver benefits, charging network expansion, or market trends.
    - Use relevant emojis and hashtags (#EVNews, #Zapway, and #{topic}EV).
    
    CRITICAL RULES FOR LINKEDIN (IN-DEPTH):
    - Do NOT generate a basic copy of the tweet. Provide a highly professional, 250+ word strategic industry analysis post.
    - Structure it with headers:
      ⚡ THE ANNOUNCEMENT
      📈 KEY STRATEGIC IMPLICATIONS (use bullet points)
      🔮 ZAPWAY'S TAKE ON SMART MOBILITY
    
    Return strictly JSON:
    {{
        "tweet": {{"text": "...", "hook": "..."}},
        "linkedin": {{"headline": "...", "body": "...", "hook": "..."}},
        "reel_script": {{"hook": "...", "scenes": [{{"visual": "...", "audio": "..."}}]}},
        "carousel": [{{"title": "...", "content": "..."}}]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.7,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": "You are a viral social media strategist. Output JSON only."}, 
                      {"role": "user", "content": prompt}]
        )
        if hasattr(response, 'usage') and response.usage:
            log_groq_usage(response.usage.total_tokens)
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Social bundle generation error: {e}")
        # Fallback to dynamic template if LLM fails
        return {
            "tweet": {
                "text": (
                    f"🧵 1/3: {title_clean} ⚡\n"
                    f"This major {topic} announcement is accelerating clean mobility adoption. Core details below: 👇 #EVNews #Zapway #{topic}EV\n\n"
                    f"2/3: Key developments show optimized supply chain execution, localized manufacturing, and battery tech advancements that lower TCO.\n\n"
                    f"3/3: Ultimately, this drives convenience with charging infrastructure expansions and direct-to-consumer savings."
                ),
                "hook": f"The electric vehicle market is shifting quickly with this {topic} update."
            },
            "linkedin": {
                "headline": f"In-Depth Analysis: How {title_clean} Redefines EV Mobility", 
                "body": (
                    f"⚡ THE ANNOUNCEMENT\n"
                    f"Recent updates around {topic} mark a major milestone in clean tech transportation. {title_clean}.\n\n"
                    f"📈 KEY IMPLICATIONS\n"
                    f"- Supply Chain Optimization: Localizing parts to drive down costs.\n"
                    f"- Technology Maturation: Enhanced battery/charging integration for range.\n"
                    f"- Market Viability: Driving consumer transition from ICE to EV.\n\n"
                    f"🔮 ZAPWAY'S TAKE\n"
                    f"This shift indicates the market is moving into mass viability. As infrastructure scales, TCO parity becomes reality. Read more on ZAPWAY."
                ),
                "hook": f"Important news regarding {topic} EV strategy."
            },
            "reel_script": {"hook": "Wait...", "scenes": []},
            "carousel": []
        }

def schedule_social_campaign(story_id, bundle):
    """Save the social bundle to the database for distribution."""
    from backend.db.queries import create_social_campaign
    
    # Schedule for multiple platforms
    platforms = ["Twitter", "LinkedIn", "Instagram"]
    for p in platforms:
        content = bundle.get(p.lower(), bundle.get("tweet"))
        create_social_campaign(
            story_id=story_id,
            platform=p,
            hook=content.get("hook", ""),
            caption=content.get("text", content.get("body", "")),
            expected_ctr=0.05,
            priority_score=0.8,
            distribution_logic="viral_hook_v1"
        )
    return True
