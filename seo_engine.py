"""
ZAPWAY SEO Engine
=================
Generates meta data, structured headings, internal links, and programmatic SEO pages.
"""
from backend.db.queries import get_db
import json
import uuid

from keyword_engine import KeywordEngine, generate_keyword_faq

def truncate_word_safe(text, max_chars):
    if not text or len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_boundary = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?'))
    if last_boundary != -1 and last_boundary > 20:
        return text[:last_boundary+1].strip()
    return text

def clean_incomplete_ending(text):
    if not text:
        return text
    import re
    incomplete_endings = {
        'to', 'in', 'of', 'and', 'the', 'for', 'with', 'a', 'an', 'at', 'by', 'from', 'on', 'about', 
        'is', 'are', 'was', 'were', 'be', 'been', 'has', 'have', 'had', 'its', 'their', 'our', 'your',
        'will', 'would', 'shall', 'should', 'can', 'could', 'may', 'might', 'must', 'that', 'which', 'who',
        'as', 'but', 'or', 'nor', 'so', 'yet'
    }
    words = text.strip().split()
    while words and re.sub(r'[^\w]', '', words[-1]).lower() in incomplete_endings:
        words.pop()
    return " ".join(words)

def generate_seo_metadata(title, content, news_type="EV"):
    """Generate optimized meta title, description, and full keyword strategy."""
    strategy = KeywordEngine.generate_keyword_strategy(title, content, news_type)
    primary = strategy.get("primary", "EV")
    
    # Try calling LLM-based meta tags generator if available
    from backend.llm import generate_meta_tags, get_groq_client
    if get_groq_client() is not None:
        try:
            llm_meta = generate_meta_tags(primary, title, content[:200])
            if llm_meta and "meta_title" in llm_meta:
                meta_title_val = clean_incomplete_ending(llm_meta["meta_title"])
                meta_desc_val = clean_incomplete_ending(llm_meta.get("meta_description", llm_meta.get("meta_desc", "")))
                return {
                    "meta_title": meta_title_val,
                    "meta_desc": meta_desc_val,
                    "keywords": primary,
                    "strategy": strategy
                }
        except Exception as e:
            print(f"[SEO Engine] LLM meta generation failed, using fallback: {e}")

    # Fallback
    import re
    ev_companies = ["Tata", "Mahindra", "Ola", "Ather", "Tesla", "BYD", "Hyundai", "MG Motor", "TVS"]
    matched_company = None
    for company in ev_companies:
        if company.lower() in title.lower():
            matched_company = company
            break
    topic = matched_company if matched_company else "EV"
    
    meta_title = f"{title} | ZAPWAY"
    if len(meta_title) > 60:
        meta_title = truncate_word_safe(f"{title} | ZAPWAY EV News", 80)
    if len(meta_title) > 80 or not meta_title:
        meta_title = truncate_word_safe(f"{title}", 80)
    
    meta_title = clean_incomplete_ending(meta_title)

    # Extract sentences and build meta desc with complete sentences only
    desc_sentences = [
        f"Discover the latest electric vehicle updates and charging infrastructure developments for {topic}.",
        f"Read key smart mobility highlights, battery technology milestones, and EV market trends on ZAPWAY."
    ]
    
    if content:
        clean_content = re.sub(r'<[^>]+>', '', content)
        clean_content = re.sub(r'\s+', ' ', clean_content).strip()
        
        extracted_s = []
        for s in re.split(r'(?<=[.!?])\s+', clean_content):
            s = s.strip()
            if len(s) > 20:
                if not s.endswith(('.', '!', '?')):
                    s += '.'
                extracted_s.append(s)
                
        if extracted_s:
            desc_sentences.insert(0, extracted_s[0])
            if len(extracted_s) > 1:
                desc_sentences.insert(1, extracted_s[1])

    meta_desc_parts = []
    total_len = 0
    for s in desc_sentences:
        if total_len + len(s) + (1 if meta_desc_parts else 0) <= 150:
            meta_desc_parts.append(s)
            total_len += len(s) + 1
        else:
            break
            
    if not meta_desc_parts:
        meta_desc = f"Discover key electric vehicle developments, charging infrastructure updates, and smart mobility insights for {topic} on ZAPWAY."
    else:
        meta_desc = " ".join(meta_desc_parts)

    meta_desc = clean_incomplete_ending(meta_desc)
    
    return {
        "meta_title": meta_title,
        "meta_desc": meta_desc,
        "keywords": primary,
        "strategy": strategy
    }

def generate_faq(content, primary_keyword="EV"):
    """Automatically generate FAQ JSON for schema.org using KeywordEngine."""
    faqs = generate_keyword_faq(primary_keyword)
    return json.dumps(faqs)

def generate_internal_links(article_id, current_title):
    """Find related articles for internal linking."""
    with get_db() as conn:
        cur = conn.cursor()
        # Find 3 related stories by title similarity (simple mock)
        cur.execute("SELECT id, title FROM stories WHERE id != ? LIMIT 3", (article_id,))
        related = cur.fetchall()
        
        links = []
        for r in related:
            links.append({"id": r[0], "title": r[1]})
        return json.dumps(links)

def create_programmatic_page(type: str, context: dict):
    """
    Create a programmatic SEO page:
    types: 'charging', 'comparison', 'subsidy', 'calculator'
    """
    page_id = f"seo_{uuid.uuid4().hex[:8]}"
    slug = f"ev-{type}-{uuid.uuid4().hex[:4]}"
    
    # Mock content generation based on type
    content = f"Comprehensive guide to EV {type}. Everything you need to know about {context.get('topic', 'EVs')}."
    
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO seo_pages (id, type, slug, title, content, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (page_id, type, slug, f"Ultimate EV {type.title()} Guide", content))
        conn.commit()
    
    return {"id": page_id, "slug": slug}
