import re
import json
import os
from urllib.parse import urlparse
from backend.db.queries import get_db
from groq import Groq

def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or "YOUR_GROQ_API_KEY" in api_key:
        return None
    return Groq(api_key=api_key)

SPAM_DOMAINS = {"bit.ly", "goo.gl", "t.co", "tinyurl.com", "instagram.com", "facebook.com", "wa.me"}

def extract_candidate_sources(raw_content: str):
    """Scan incoming parsed text strings specifically for outbound links to novel sources."""
    # Find all URLs
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', raw_content)
    
    unique_domains = set()
    for u in urls:
        parsed = urlparse(u)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
            
        # Hard Filter
        if domain in SPAM_DOMAINS:
            continue
            
        unique_domains.add(domain)
        
    for domain in unique_domains:
        process_discovered_domain(domain)

def process_discovered_domain(domain: str):
    with get_db() as conn:
        cur = conn.cursor()
        
        # Check if already a known source
        cur.execute("SELECT source_id FROM sources WHERE domain = ?", (domain,))
        if cur.fetchone():
            return
            
        # Check if already discovered
        cur.execute("SELECT frequency_count, status FROM discovered_sources WHERE domain = ?", (domain,))
        row = cur.fetchone()
        
        if not row:
            # First time seeing it -> store and await frequency trigger
            cur.execute("INSERT INTO discovered_sources (domain, frequency_count) VALUES (?, 1)", (domain,))
        else:
            freq = row["frequency_count"] + 1
            cur.execute("UPDATE discovered_sources SET frequency_count = ? WHERE domain = ?", (freq, domain))
            
            # If hit frequency threshold and pending, execute cheap signals + LLM validation
            if freq >= 2 and row["status"] == "pending":
                evaluate_and_promote_source(domain, freq, conn)
                
        conn.commit()

def evaluate_and_promote_source(domain: str, frequency: int, conn):
    """Hybrid pipeline validating a source candidate before adding to active roster."""
    # 1. Cheap Signals (Mocked relevance evaluation)
    # E.g. Check if domain name explicitly has EV terms
    ev_keywords = ["ev", "electric", "auto", "motor", "drive", "battery", "tesla"]
    keyword_hit = any(kw in domain for kw in ev_keywords)
    
    # Cheap initial validation score
    validation_score = (0.2 if keyword_hit else 0.0) + min(0.3, frequency * 0.05)
    
    # Fast reject if absolutely terrible
    if validation_score < 0.1:
        conn.cursor().execute("UPDATE discovered_sources SET status = 'rejected' WHERE domain = ?", (domain,))
        return
        
    # Call LLM Validator for the Mid Range Edge Cases
    try:
        sys_prompt = """You are ZAPWAY Auto-Discovery Engine.
Analyze the provided domain pattern and determine if it belongs to an EV manufacturer, News Outlet, Government organ, or is irrelevant.
Output STRICT JSON:
{
    "relevant": true/false,
    "confidence": 0-1.0,
    "category": "OEM / Media / Govt / Blog",
    "tier": "1 / 2 / 3"
}"""
        client = get_groq_client()
        if not client:
            return # Skip if no API key
            
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"DOMAIN: {domain}"}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        res = json.loads(completion.choices[0].message.content)
        
        if res.get("relevant") and res.get("confidence", 0) > 0.6:
            # PROMOTION
            sid = f"src_{hash(domain) % 999999}"
            conn.cursor().execute(
                "INSERT INTO sources (source_id, name, domain, type, category, tier) VALUES (?, ?, ?, ?, ?, ?)",
                (sid, domain, domain, "discovered", res.get("category", "Media"), str(res.get("tier", "2")))
            )
            conn.cursor().execute("UPDATE discovered_sources SET status = 'active', validation_score = ? WHERE domain = ?", (res.get("confidence", 0.5), domain))
        else:
            conn.cursor().execute("UPDATE discovered_sources SET status = 'rejected' WHERE domain = ?", (domain,))
            
    except Exception as e:
        print(f"Discovery LLM Error for {domain}: {e}")
