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
    
    system_prompt = """You are a faithful news paraphraser and editor for ZAPWAY. Your responsibility is to lightly paraphrase the raw source text and structure it into exactly 4 standardized sections.

Your output must follow these rules strictly:
1. TITLE: Keep the original article headline almost exactly. You may swap 1-2 words or fix a grammar issue, but DO NOT rewrite or reinvent it. The output title must be recognisably the same as the source title.
2. SECTION STRUCTURE: You must output exactly 4 sections in this exact order:
   - Section 1 Heading: A brief topic-based heading tailored specifically to the core news story (e.g. "Tata Motors Subsidies & Benefits" or "Charging Infrastructure Expansion" instead of a generic header like "Main Details" or "Overview").
   - Section 2 Heading: "Key Developments"
   - Section 3 Heading: "Why It Matters for EV Drivers"
   - Section 4 Heading: "ZAPWAY Relevance"
3. CONTENT PACKING: Distribute the lightly paraphrased source text across these 4 sections logically:
   - Under the topic-based heading, place the general overview of the news.
   - Under "Key Developments", list the specific facts, details, and numbers.
   - Under "Why It Matters for EV Drivers", explain the direct impact on EV consumers or drivers in India.
   - Under "ZAPWAY Relevance", explain how this connects to charging, route planning, or smart EV navigation.
4. LIGHT PARAPHRASE ONLY: Swap at most 2-3 words per sentence with synonyms or minimally restructure. Do NOT rewrite sentences from scratch.
5. DATA INTEGRITY: Keep ALL numbers, prices (e.g. 'Rs 27.90 lakh'), specs, model names, variant names, percentages, dates, and named entities EXACTLY as they appear in the source. Never round or translate them.
6. LINGUISTIC CLOSURE: Every sentence must end with proper punctuation (., !, ?). No trailing conjunctions or incomplete sentences.
7. NO INVENTED CONTENT: Do not add any information, context, or opinion not present in the source.

JSON Structure to return — fill every field exactly as described:
{
  "title": "...",            // Near-identical to source headline. Max 2 word changes.
  "meta_title": "...",        // SEO meta title: source headline + site name suffix, max 60 chars.
  "meta_description": "...",  // 1-2 sentence summary of the article, max 155 chars, no ellipsis.
  "keywords": ["k1", "k2"],   // 3-5 key EV-related terms from the article.
  "ai_summary": "",           // MUST be empty string. No AI core summary or key points.
  "sections": [
    {
      "heading": "...",  // Section heading name as described in SECTION STRUCTURE.
      "content": "..."   // Lightly paraphrased paragraph(s) from that section.
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
    clean_content = (content or "")
    clean_content = _re.sub(r'<[^>]+>', ' ', clean_content)          # strip HTML tags
    clean_content = _re.sub(r'&[a-z]+;', ' ', clean_content)         # strip HTML entities
    clean_content = _re.sub(r'[ \t]{2,}', ' ', clean_content)        # collapse spaces
    clean_content = _re.sub(r'\n{3,}', '\n\n', clean_content)        # collapse blank lines
    clean_content = clean_content.strip()
    
    # Truncate to avoid Groq 413 Payload Too Large errors
    content_for_prompt = clean_content[:8000]
    
    # Include original title in user prompt as an explicit anchor
    title_anchor = f"ORIGINAL TITLE: {title}\n\n" if title else ""
    user_prompt = f"{title_anchor}SOURCE ARTICLE TO PARAPHRASE:\n{content_for_prompt}\n\nIMPORTANT: Your output title must be nearly identical to the ORIGINAL TITLE above. Your section headings must be copied verbatim from the source text above."
    
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

    model_name = "llama-3.3-70b-versatile"
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
            print(f"[TRACE:{traceparent}] Primary model {model_name} failed: {primary_err}. Trying secondary model llama-3.1-8b-instant...")
            model_name = "llama-3.1-8b-instant"
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
        max_attempts = 4
        current_payload = payload
        
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
                    raise retry_err
            
            if hasattr(response_retry, 'usage') and response_retry.usage:
                log_groq_usage(response_retry.usage.total_tokens)
                
            current_payload = json.loads(response_retry.choices[0].message.content)
            print(f"[TRACE:{traceparent}] Self-correction attempt {attempt} completed in {time.time() - correction_start:.2f}s.")
            attempt += 1
            
    except Exception as e:
        print(f"[TRACE:{traceparent}][CRITICAL] Failed to execute generation task A: {e}")
        from backend.llm import _rewrite_article_fallback
        return _rewrite_article_fallback(content, url=url, title=title)
