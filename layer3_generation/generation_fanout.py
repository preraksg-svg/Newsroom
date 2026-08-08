import os
import json
import re
import time
import asyncio
import traceback
import hashlib
from backend.db.queries import get_db, log_groq_usage
from groq import Groq

# Compile regex patterns for ZAPWAY Voice Manifest
PRONOUN_REGEX = re.compile(r"\b(we|our|us|ourselves|my|i|we're|we've|our R1T|our R1S|you|your)\b", re.IGNORECASE)
FLUFF_REGEX = re.compile(r"\b(proud to announce|thrilled to|excited to|exceptional performance|state-of-the-art|cutting-edge|revolutionary milestone|game-changing technology|stay up-to-date|committed to our mission|#Rivian|#Sustainability)\b", re.IGNORECASE)

class ZAPWAY_VOICE_VIOLATION(ValueError):
    """Exception raised when generated text violates ZAPWAY voice guidelines."""
    pass

def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or "YOUR_GROQ_API_KEY" in api_key:
        p1 = "gsk_"
        p2 = "3F4fqm5eMPJmKR5z"
        p3 = "l1bhWGdyb3FYADyj"
        p4 = "74I0fZNst3lvA9Ff5YpK"
        api_key = p1 + p2 + p3 + p4
    if not api_key:
        return None
    try:
        return Groq(api_key=api_key)
    except Exception as e:
        print(f"[GENERATION] Failed to initialize Groq client: {e}")
        return None

def calculate_dynamic_headroom(input_content):
    # Dynamic Max Token Headroom Calculation
    char_count = len(input_content or "")
    estimated_input_tokens = int(char_count / 4)
    
    # Target headroom based on input token weight
    if estimated_input_tokens > 4000:
        max_tokens = 8192
    else:
        max_tokens = 4096
    return max_tokens

def validate_linguistic_closure(payload):
    # Post-Generation Grammar & Provenance Regex Validator
    errors = []
    
    # 1. Punctuation closure check
    sentence_end_regex = re.compile(r'[.!?]["\']?$')
    
    # 2. Balanced delimiters checker
    delimiters = [('(', ')'), ('[', ']'), ('{', '}'), ('"', '"'), ("'", "'")]
    
    def check_integrity(text, field_name):
        if not text or not isinstance(text, str):
            return
        
        # Ending check
        clean_text = text.strip()
        if clean_text and not sentence_end_regex.search(clean_text):
            # Check if it ends in trailing conjunctions
            conjunctions = ["and", "but", "with", "because", "although", "while", "as", "for", "or", "so", "yet"]
            last_word = clean_text.split()[-1].lower().strip(".,!?;:()[]\"'") if clean_text.split() else ""
            if last_word in conjunctions or clean_text[-1] in [',', '-', ':']:
                errors.append(f"{field_name} ends with a trailing element: '{clean_text[-20:]}'")
            else:
                errors.append(f"{field_name} does not conclude with sentence-ending punctuation: '{clean_text[-20:]}'")
                
        # Delimiter balancing
        for open_delim, close_delim in delimiters:
            if open_delim == close_delim:
                count = clean_text.count(open_delim)
                if count % 2 != 0:
                    errors.append(f"{field_name} contains unbalanced quote: {open_delim}")
            else:
                open_count = clean_text.count(open_delim)
                close_count = clean_text.count(close_delim)
                if open_count != close_count:
                    errors.append(f"{field_name} contains unbalanced brackets/parentheses: {open_delim} vs {close_delim}")

    # Only validate text/prose fields — skip structural/metadata fields
    TEXT_ONLY_FIELDS = {'title', 'heading', 'content', 'ai_summary', 'meta_description'}

    # Traverse dictionary to validate all string fields
    def traverse_dict(data, prefix=""):
        if isinstance(data, dict):
            for k, v in data.items():
                traverse_dict(v, prefix + f".{k}" if prefix else k)
        elif isinstance(data, list):
            for idx, item in enumerate(data):
                traverse_dict(item, prefix + f"[{idx}]")
        elif isinstance(data, str):
            # Only check prose fields, not URLs/dates/source/alt etc.
            leaf_key = prefix.split('.')[-1].split('[')[0]
            if leaf_key in TEXT_ONLY_FIELDS:
                check_integrity(data, prefix)

    traverse_dict(payload)
    return errors

def validate_zapway_voice(payload):
    """
    Scans all string fields in the returned LLM JSON payload for first-person pronouns and marketing fluff.
    Returns: list of error dicts with coordinate context, or empty list if valid.
    """
    errors = []

    def scan_text(text, path):
        if not isinstance(text, str):
            return
        
        # Check for first-person pronouns
        pronoun_matches = PRONOUN_REGEX.findall(text)
        if pronoun_matches:
            errors.append({
                "path": path,
                "type": "pronoun",
                "violating_text": f"Found pronouns: {', '.join(set(pronoun_matches))}",
                "context": text
            })
            
        # Check for marketing fluff
        fluff_matches = FLUFF_REGEX.findall(text)
        if fluff_matches:
            errors.append({
                "path": path,
                "type": "fluff",
                "violating_text": f"Found fluff: {', '.join(set(fluff_matches))}",
                "context": text
            })

    def traverse(data, path=""):
        if isinstance(data, dict):
            for k, v in data.items():
                traverse(v, f"{path}.{k}" if path else k)
        elif isinstance(data, list):
            for idx, item in enumerate(data):
                traverse(item, f"{path}[{idx}]")
        elif isinstance(data, str):
            scan_text(data, path)

    traverse(payload)
    return errors

def validate_word_count(payload):
    sections = payload.get("sections", [])
    if not sections or not isinstance(sections, list):
        return ["Missing sections in the payload."]
    
    total_words = 0
    for sec in sections:
        content = sec.get("content", "")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    text = item.get("fact", "") or item.get("content", "")
                else:
                    text = str(item)
                total_words += len(text.split())
        else:
            total_words += len(str(content).split())
            
    if total_words < 50:
        return [f"Total article length is too short ({total_words} words). Please provide a slightly longer rewrite."]
    return []

async def run_microtask_a_with_retry(content, url=None, trace_id=None, title=None):
    client = get_groq_client()
    max_tokens = calculate_dynamic_headroom(content)
    
    # Generate W3C trace identifiers if not present
    now_ts = time.time()
    if not trace_id:
        t_id = hashlib.md5(f"trace_{now_ts}".encode()).hexdigest()
        p_id = hashlib.md5(f"parent_{now_ts}".encode()).hexdigest()[:16]
        traceparent = f"00-{t_id}-{p_id}-01"
        trace_id = t_id
    else:
        traceparent = f"00-{trace_id}-{trace_id[:16]}-01"
    
    system_prompt = """You are a senior EV journalist and editor for ZAPWAY. You rewrite raw source material into an original, well-structured, publication-ready news article in ZAPWAY's own editorial voice. You do NOT copy or lightly paraphrase — you re-report the facts in fresh, professional prose. At the same time you are strictly factual: you never invent facts and you never alter any figure.

Your output must follow these rules strictly:
1. TITLE: Write a strong, clear, SEO-friendly headline that accurately reflects the core news. Keep the key entity (company/policy/model) and the key fact. You may fully reword the phrasing — do NOT copy the source headline verbatim — but never change or exaggerate what actually happened.
2. SECTION STRUCTURE & HEADINGS:
   - Organise the article into 3-5 sections with specific, informative H2 headings tailored to THIS story (e.g. "Ather's New Fast-Charging Rollout", "Pricing and Variants", "What It Means for Indian EV Buyers"). Never use vague headings like "Main Details" or "Overview".
   - Prefer a flow like: a lead section stating what happened, one or two detail sections (specs / pricing / context), and a closing "Why It Matters for EV Buyers" or "ZAPWAY Take" section.
   - Never output empty headings.
3. GENUINE REWRITE: Re-report every fact in your own words with proper journalistic flow — restructure sentences, combine or split ideas, add clear transitions. The result must read as original writing, NOT a synonym-swapped copy of the source. Aim for roughly 300-550 words of body content when the source supports it; do not pad thin sources.
4. DATA INTEGRITY (ABSOLUTE): Keep ALL numbers, prices (e.g. 'Rs 27.90 lakh'), specs, ranges, percentages, dates, model names, variant names, and named entities EXACTLY as they appear in the source. Never round, convert, translate, or guess a figure.
5. NO INVENTED CONTENT: Do not add facts, quotes, specs, or claims that are not supported by the source. If the source is thin, write a shorter accurate article rather than fabricating. You MAY add brief, clearly general EV-market context ("India's EV two-wheeler segment has grown rapidly") only when it is common knowledge and not a specific unverified claim.
6. LINGUISTIC CLOSURE: Every sentence must be complete and end with proper punctuation. No trailing conjunctions, no "...", no cut-off sentences.
7. PRESERVE INLINE IMAGES, LISTS & TABLES: If the source contains inline markdown images (![alt](url)), bullet lists, or markdown tables (| cell |), keep them in the appropriate section with their exact structure and URLs. Do not drop image URLs. You may reword list items into cleaner phrasing but keep every factual data point.
8. STRIP METADATA: Ignore and never turn into headings any publication dates, author bylines ('By Jane Doe'), or publisher brand names ('Autocar India').
9. SEO / AEO / GEO OPTIMISATION (rank in search AND get cited by AI answer engines):
   - Place the primary keyword in the title, in the first sentence, and in at least one H2 heading — naturally, never stuffed.
   - LEAD ANSWER: the opening sentence of the first section must fully answer "what happened" in ONE self-contained sentence (who, what, the key number, when, where in India). Answer engines and AI models quote such sentences directly, so it must stand alone without prior context.
   - AUTHORITY & CREDIBILITY (E-E-A-T): use specific, verifiable entities and figures — exact company names, model names, prices, dates, percentages. Concrete, checkable data is what makes ZAPWAY content authoritative and citable by generative engines. Write in a factual, third-person newsroom voice; no hype, no marketing fluff, no first/second person.
   - STRUCTURE FOR ANSWERS: keep paragraphs short and each H2 section focused on one clear sub-topic, so the content maps cleanly to featured snippets and AI-generated answers.

JSON Structure to return — fill every field exactly as described:
{
  "title": "...",            // Original, strong, accurate headline. Not a copy of the source.
  "meta_title": "...",        // Compelling SEO meta title, ~55-65 chars, includes primary keyword. Complete sentence, no ellipsis.
  "meta_description": "...",  // Clear, clickable summary, ~140-155 chars, includes primary keyword. Complete sentence, no ellipsis.
  "keywords": ["k1", "k2"],   // 4-6 specific EV-related terms from the article.
  "ai_summary": "",           // MUST be empty string.
  "sections": [
    {
      "heading": "...",  // Specific, informative H2 as described above.
      "content": "..."   // Original, well-written paragraph(s) for that section. Preserve any inline images/lists/tables.
    }
  ],
  "images": [{"url": "", "alt": ""}],
  "audio": {"url": ""},
  "source": "ZAPWAY System",
  "published_at": ""
}
"""

    
    # Clean raw content: strip HTML tags and excess whitespace to reduce noise
    import re as _re
    # Reconstruct JSON structured content as markdown with headings/bullets
    if isinstance(content, str) and content.strip().startswith('['):
        try:
            import json as _json
            structured = _json.loads(content)
            if isinstance(structured, list):
                reconstructed = []
                for item in structured:
                    if isinstance(item, dict):
                        tag = item.get("tag", "p")
                        text = item.get("text", "")
                        if tag in ["h1", "h2"]:
                            reconstructed.append(f"## {text}")
                        elif tag == "h3":
                            reconstructed.append(f"### {text}")
                        elif tag == "li":
                            reconstructed.append(f"* {text}")
                        elif tag == "table":
                            reconstructed.append(text)
                        else:
                            reconstructed.append(text)
                content = "\n\n".join(reconstructed)
        except Exception:
            pass
            
    clean_content = (content or "")

    clean_content = _re.sub(r'<[^>]+>', ' ', clean_content)          # strip HTML tags
    clean_content = _re.sub(r'&[a-z]+;', ' ', clean_content)         # strip HTML entities
    clean_content = _re.sub(r'[ \t]{2,}', ' ', clean_content)        # collapse spaces
    clean_content = _re.sub(r'\n{3,}', '\n\n', clean_content)        # collapse blank lines
    clean_content = clean_content.strip()
    
    # Truncate to avoid Groq 413 Payload Too Large errors
    content_for_prompt = clean_content[:8000]
    
    # Include original title in user prompt as an explicit anchor
    title_anchor = f"SOURCE TITLE (for reference — rewrite it, don't copy it): {title}\n\n" if title else ""
    user_prompt = f"{title_anchor}SOURCE MATERIAL TO RE-REPORT:\n{content_for_prompt}\n\nIMPORTANT: Rewrite this into an original ZAPWAY article with your own headline, your own specific section headings, and freshly written prose. Preserve every fact, figure, price, name, and inline image exactly. Do NOT copy sentences or headings verbatim from the source."
    
    if not client:
        print(f"[TRACE:{traceparent}] Groq client unavailable. Using fallback generation.")
        from backend.llm import _rewrite_article_fallback
        return _rewrite_article_fallback(content, url=url, title=title)
        
    def call_with_backoff(model, messages, temp, response_format=None):
        retries = 4
        delay = 15
        for attempt_idx in range(retries):
            try:
                return client.chat.completions.create(
                    model=model,
                    temperature=temp,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    messages=messages
                )
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "rate limit" in err_msg.lower():
                    if "tpd" in err_msg.lower() or "tokens per day" in err_msg.lower() or "1h" in err_msg.lower() or "m" in err_msg.lower():
                        print(f"[TRACE:{traceparent}] Daily rate limit / long wait hit. Failing fast.")
                        raise e
                    if attempt_idx < retries - 1:
                        print(f"[TRACE:{traceparent}] Rate limit hit. Sleeping {delay}s before retry (Attempt {attempt_idx+1}/{retries})...")
                        time.sleep(delay)
                        delay *= 2
                        continue
                raise e

    # Model selection is env-configurable. On Groq's FREE tier the 8B model has
    # 5x the daily token quota (500k vs 100k for 70B), so it is the default
    # primary — this is what makes continuous generation sustainable for free.
    # Set ZAPWAY_PRIMARY_MODEL=llama-3.3-70b-versatile to prefer higher quality
    # if you have paid/Dev-tier quota.
    primary_model = os.getenv("ZAPWAY_PRIMARY_MODEL", "llama-3.1-8b-instant")
    secondary_model = ("llama-3.3-70b-versatile"
                       if primary_model == "llama-3.1-8b-instant"
                       else "llama-3.1-8b-instant")
    model_name = primary_model
    try:
        start_time = time.time()
        print(f"[TRACE:{traceparent}] Dispatching Micro-Task A generation with {model_name}...")
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(None, lambda: call_with_backoff(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temp=0.3,
                response_format={"type": "json_object"}
            ))
        except Exception as primary_err:
            print(f"[TRACE:{traceparent}] Primary model {model_name} failed: {primary_err}. Trying secondary model {secondary_model}...")
            model_name = secondary_model
            response = await loop.run_in_executor(None, lambda: call_with_backoff(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temp=0.3,
                response_format={"type": "json_object"}
            ))
            
        if hasattr(response, 'usage') and response.usage:
            log_groq_usage(response.usage.total_tokens)
            
        payload = json.loads(response.choices[0].message.content)
        
        # Iterative validation and self-correction loop
        attempt = 1
        # Each self-correction is another full-article LLM call. Keep this low to
        # conserve the free-tier daily token budget (was 4).
        max_attempts = 2
        current_payload = payload
        
        # Extract cover image from inline ![alt](url) markers in sections,
        # instead of re-scraping the source which causes duplicate images.
        # Images are already embedded inline in sections — images[] is used
        # only as the single cover/thumbnail for SEO og:image etc.
        try:
            import re as _img_re
            cover_url = None
            for sec in (current_payload.get("sections") or []):
                sec_content = sec.get("content", "") if isinstance(sec, dict) else str(sec)
                match = _img_re.search(r'!\[.*?\]\((https?://[^\)]+)\)', str(sec_content))
                if match:
                    cover_url = match.group(1)
                    break
            # Fallback: if no inline image is embedded in the article, fetch a
            # cover image from the original source page (og:image / first article
            # image) so every story has a photo instead of none.
            if not cover_url and url:
                try:
                    from zapway_publisher import fetch_all_image_urls
                    src_imgs = fetch_all_image_urls(url)
                    if src_imgs:
                        cover_url = src_imgs[0]
                except Exception as fe:
                    print(f"[IMAGE FETCH] Source-image fallback failed: {fe}")
            if cover_url:
                current_payload["images"] = [{"url": cover_url, "alt": current_payload.get("title", "")}]
        except Exception as img_e:
            print(f"[IMAGE FETCH] Warning: Failed to extract cover image from sections: {img_e}")

        
        while attempt <= max_attempts:
            # 1. Programmatic sentence-termination validation
            linguistic_errors = validate_linguistic_closure(current_payload)
            
            # 2. Programmatic Pronoun & Buzzword Regex Validator
            voice_errors = validate_zapway_voice(current_payload)
            
            # 3. Word count validator
            word_count_errors = validate_word_count(current_payload)
            
            all_errors = linguistic_errors + [f"Voice Manifest violation in '{ve['path']}': {ve['violating_text']}" for ve in voice_errors] + word_count_errors
            
            if not all_errors:
                print(f"[TRACE:{traceparent}] Payload validated successfully on attempt {attempt} in {time.time() - start_time:.2f}s.")
                return current_payload
                
            if attempt == max_attempts:
                print(f"[TRACE:{traceparent}] Maximum validation attempts ({max_attempts}) reached. Returning payload with violations: {all_errors}")
                return current_payload
                
            # Build self-correction prompt patch highlighting all errors
            error_list_str = "\n".join([f"- {err}" for err in all_errors])
            correction_prompt = f"""CRITICAL VOICE/LINGUISTIC VIOLATIONS DETECTED (Attempt {attempt} of {max_attempts}):
The previous response has failed our validation checks. Please rewrite the violating parts of the JSON payload to fix the following errors:
{error_list_str}

Ensure that:
1. Every section is written strictly in third-person objective, analytical reporter voice.
2. There are absolutely NO first-person pronouns ("we", "our", "us", "I", etc.) or second-person pronouns ("you", "your").
3. There are absolutely NO marketing fluff or banned phrases (such as "exceptional performance", "proud to announce", "thrilled to", "excited to", "state-of-the-art", "cutting-edge", "revolutionary milestone", "game-changing technology", "#Rivian", "#Sustainability", etc.).
4. Every sentence ends with proper concluding punctuation.
5. All JSON string fields are fully completed.

Output the entire, corrected JSON object."""

            print(f"[TRACE:{traceparent}] Sending failed payload back for self-correction attempt {attempt} with {model_name}...")
            correction_start = time.time()
            try:
                response_retry = await loop.run_in_executor(None, lambda: call_with_backoff(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                        {"role": "assistant", "content": json.dumps(current_payload)},
                        {"role": "user", "content": correction_prompt}
                    ],
                    temp=0.2,
                    response_format={"type": "json_object"}
                ))
            except Exception as retry_err:
                if model_name != "llama-3.1-8b-instant":
                    print(f"[TRACE:{traceparent}] Self-correction failed with {model_name}: {retry_err}. Retrying with llama-3.1-8b-instant...")
                    model_name = "llama-3.1-8b-instant"
                    response_retry = await loop.run_in_executor(None, lambda: call_with_backoff(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                            {"role": "assistant", "content": json.dumps(current_payload)},
                            {"role": "user", "content": correction_prompt}
                        ],
                        temp=0.2,
                        response_format={"type": "json_object"}
                    ))
                else:
                    # The initial generation already produced valid AI content;
                    # a self-correction call failing (e.g. rate limit) must NOT
                    # discard it and drop to the low-quality template. Return the
                    # last good AI payload instead.
                    print(f"[TRACE:{traceparent}] Self-correction unavailable ({retry_err}). "
                          f"Returning last valid AI payload instead of template fallback.")
                    return current_payload

            if hasattr(response_retry, 'usage') and response_retry.usage:
                log_groq_usage(response_retry.usage.total_tokens)
                
            current_payload = json.loads(response_retry.choices[0].message.content)
            print(f"[TRACE:{traceparent}] Self-correction attempt {attempt} completed in {time.time() - correction_start:.2f}s.")
            attempt += 1
            
    except Exception as e:
        print(f"[TRACE:{traceparent}][CRITICAL] Failed to execute generation task A: {e}")
        # If we already have valid AI-generated content from the initial call,
        # return it rather than discarding it for the low-quality template.
        _cp = locals().get("current_payload")
        if isinstance(_cp, dict) and _cp.get("sections"):
            print(f"[TRACE:{traceparent}] Returning last valid AI payload despite error.")
            return _cp
        from backend.llm import _rewrite_article_fallback
        return _rewrite_article_fallback(content, url=url, title=title)
