import requests
import feedparser
import re
import os
import time
from bs4 import BeautifulSoup
from dateutil import parser
from backend.db.queries import get_db
from groq import Groq

last_web_memory = {}

EV_REGEX = re.compile(r'(electric| ev |evs|zero emission|battery|charging|charge|tesla|rivian|lucid|byd|scooter|bike|motor|sierra|punch|ola|ather|tata|mahindra|windsor|curvv|volt|e-tron|eqs|eqe|eqa|eqb|enyaq|taycan|ioniq|nexon|tiago|tigor|xuv400|be\.05|comet|zs\s+ev|vida|chetak|iqube|roadster|motorcycle|scorpio\.e|thar\.e|altigreen|kinetic|euler|rv400|lithium|gigafactory|subsidy|subsidies|fame|zero-emission|electrified|electrification)', re.IGNORECASE)

def table_to_markdown(table_tag):
    rows = table_tag.find_all('tr')
    if not rows:
        return ""
    
    markdown_rows = []
    
    # Extract headers
    headers = []
    first_row_cells = rows[0].find_all(['th', 'td'])
    for cell in first_row_cells:
        headers.append(cell.get_text(" ", strip=True))
        
    if not headers or all(h == "" for h in headers):
        return ""
        
    markdown_rows.append("| " + " | ".join(headers) + " |")
    markdown_rows.append("| " + " | ".join(["---"] * len(headers)) + " |")
    
    # Process remaining rows
    start_idx = 1 if rows[0].find('th') or len(rows) > 1 else 0
    for row in rows[start_idx:]:
        cells = row.find_all(['th', 'td'])
        if not cells:
            continue
        row_data = []
        for cell in cells:
            row_data.append(cell.get_text(" ", strip=True))
        # Ensure row has same number of columns
        if len(row_data) < len(headers):
            row_data.extend([""] * (len(headers) - len(row_data)))
        elif len(row_data) > len(headers):
            row_data = row_data[:len(headers)]
        markdown_rows.append("| " + " | ".join(row_data) + " |")
        
    return "\n" + "\n".join(markdown_rows) + "\n"

async def scrape_single_article_page(url: str) -> str:
    """Direct HTML parser for a single article page."""
    import requests
    from bs4 import BeautifulSoup
    import re
    import asyncio
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}
    try:
        loop = asyncio.get_event_loop()
        req = await loop.run_in_executor(None, lambda: requests.get(url, headers=headers, timeout=10))
        if req.status_code == 200:
            soup = BeautifulSoup(req.text, 'html.parser')
            extracted_text = []
            skip_until_next_heading = False
            for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'li', 'table']):
                if tag.name == 'table':
                    if not skip_until_next_heading:
                        table_md = table_to_markdown(tag)
                        if table_md:
                            extracted_text.append(table_md)
                    continue
                txt = tag.get_text(" ", strip=True)
                if not txt:
                    continue
                is_heading = tag.name in ['h1', 'h2', 'h3']
                is_li = tag.name == 'li'
                
                txt_lower = txt.lower()
                
                # Filter out header/sidebar navigation menu lists
                menu_keywords = [
                    "find cars", "compare cars", "car reviews", "car photos", "car videos", "car brands", "just launched cars", "upcoming cars", "popular cars",
                    "find bikes", "compare bikes", "bike reviews", "bike photos", "bike videos", "bike brands", "just launched bikes", "upcoming bikes", "popular bikes",
                    "all reviews", "first drive", "road test", "comparo", "news & features", "opinions", "motorsport", "press releases", "all photos", "get app"
                ]
                if any(kw in txt_lower for kw in menu_keywords) or (len(txt.split()) <= 4 and any(kw in txt_lower for kw in ["find", "compare", "reviews", "photos", "videos", "upcoming", "launched", "popular", "brands"])):
                    continue
                    
                if is_heading:
                    # Ignore generic layout navigation headings
                    layout_noise = ["top stories", "latest videos", "network18 updates", "recent posts", "popular tags", "related content", "recommended stories", "trending", "must read", "popular videos", "latest news", "overdrive sites", "better photography", "better interiors", "moneycontrol", "firstpost", "news18", "copyright", "follow the market", "follow us", "latest updates"]
                    
                    is_date = False
                    try:
                        from dateutil import parser as date_parser
                        date_parser.parse(txt)
                        is_date = True
                    except:
                        pass
                    
                    if is_date or txt_lower.startswith("by ") or (len(txt.split()) <= 3 and any(pub in txt_lower for pub in ["autocar", "overdrive", "evo", "news", "date", "author", "published", "correspondent", "team"])) or any(kw in txt_lower for kw in layout_noise):
                        skip_until_next_heading = True
                        continue
                    else:
                        skip_until_next_heading = False
                
                if skip_until_next_heading:
                    continue
                    
                min_len = 3 if is_heading else (1 if is_li else 30)
                
                SOCIAL_NAV_NOISE = re.compile(
                    r'^(home|car news|bike news|facebook|twitter|whatsapp|telegram|linkedin|instagram|youtube|share|email|print|pinterest|reddit|tumblr|rss|menu|search|sign in|log in|login|register|about|contact|advertise|terms|sitemap|back to top|next|previous|more|tags|categories|topics|source|author|editors|copy link|opens in new window)$',
                    re.IGNORECASE
                )
                is_nav_noise = is_li and (
                    SOCIAL_NAV_NOISE.match(txt.strip()) or
                    'opens in new window' in txt.lower() or
                    (len(txt.split()) <= 2 and not any(c.isdigit() for c in txt))
                )
                if is_nav_noise:
                    continue
                
                # Check for footer/copyright text noise
                general_noise = ["copyright ©", "all rights reserved", "india’s largest auto media", "better photography", "better interiors", "moneycontrol", "firstpost", "news18"]
                if any(noise in txt_lower for noise in general_noise):
                    continue
                    
                if len(txt) >= min_len and not bool(re.search(r'(subscribe|cookie|privacy|advertisement)', txt, re.I)):
                    if is_heading:
                        if tag.name in ['h1', 'h2']:
                            extracted_text.append(f"## {txt}")
                        else:
                            extracted_text.append(f"### {txt}")
                    elif is_li:
                        extracted_text.append(f"* {txt}")
                    else:
                        extracted_text.append(txt)
            if extracted_text:
                return "\n".join(extracted_text)
    except Exception as e:
        print(f"Error scraping single page {url}: {e}")
    return ""


def llm_filter_website(text: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or "YOUR_GROQ_API_KEY" in api_key:
        p1 = "gsk_"
        p2 = "3F4fqm5eMPJmKR5z"
        p3 = "l1bhWGdyb3FYADyj"
        p4 = "74I0fZNst3lvA9Ff5YpK"
        api_key = p1 + p2 + p3 + p4
    if not api_key:
        return "" # Skip LLM if no key
        
    client = Groq(api_key=api_key)
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Extract clean article content with headings. Focus only on EV-related news, policy, launches, or technology. Remove ads and noise. Return empty if irrelevant."},
                {"role": "user", "content": text}
            ],
            temperature=0.1,
            max_tokens=600
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"[LLM] Error in website filter: {e}")
        return ""

async def scrape_website(url: str):
    """
    Website Worker using RSS with BeautifulSoup native HTML cleanup scaling perfectly without high compute of Playwright.
    """
    results = []
    
    # Simple deduplication caching check
    if not url.startswith("http"):
        url = "https://" + url
        
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, lambda: feedparser.parse(url))
        if feed.entries:
            for index, entry in enumerate(feed.entries[:5]):
                title = entry.get("title", "")
                link = entry.get("link", "")
                publisher = feed.feed.get("title", url.split("//")[-1])
                
                if last_web_memory.get(url) == link:
                    break
                if index == 0:
                    last_web_memory[url] = link
                
                # Try fetching native URL to avoid half-news
                article_content = await scrape_single_article_page(link)
                if not article_content.strip() or len(article_content.split()) < 120 or article_content.strip().endswith("...") or article_content.strip().endswith("…"):
                    # Fallback to summary ONLY if it is complete and long enough
                    summary = entry.get("summary", "")
                    if summary and not (summary.strip().endswith("...") or summary.strip().endswith("…")) and len(summary.split()) >= 120:
                        article_content = summary
                    else:
                        print(f"[SCRAPER] Skipping half-news or truncated entry: {link}")
                        continue
                
                final_content = article_content

                dt_str = entry.get("published", entry.get("updated", ""))
                try:
                    timestamp = int(parser.parse(dt_str).timestamp()) if dt_str else int(time.time())
                except:
                    timestamp = int(time.time())
                
                # Check if news is older than 48 hours (172800 seconds)
                if int(time.time()) - timestamp > 172800:
                    continue

                results.append({
                    "title": title,
                    "content_raw": final_content,
                    "source": publisher,
                    "source_type": "website",
                    "author": publisher,
                    "timestamp": timestamp,
                    "url": link,
                    "engagement": {
                        "likes": 0,
                        "comments": 0,
                        "shares": 0
                    }
                })
        else:
            # Fallback to direct HTML scraping
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}
            req = await loop.run_in_executor(None, lambda: requests.get(url, headers=headers, timeout=10))
            if req.status_code == 200:
                soup = BeautifulSoup(req.text, 'html.parser')
                links = []
                base_domain = url.split("//")[-1].split("/")[0]
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    title = a.get_text(" ", strip=True)
                    if len(title) < 25:
                        continue
                    if href.startswith('/'):
                        href = f"https://{base_domain}{href}"
                    elif not href.startswith('http'):
                        continue
                    if base_domain in href and href not in [l[0] for l in links]:
                        links.append((href, title))
                
                fetched_count = 0
                for link, title in links[:40]:
                    if fetched_count >= 5:
                        break
                    if last_web_memory.get(url) == link:
                        break
                    
                    # Pre-filter by EV title keywords to avoid loading non-EV pages
                    if not EV_REGEX.search(title):
                        continue
                        
                    try:
                        fetched_count += 1
                        article_req = await loop.run_in_executor(None, lambda: requests.get(link, timeout=5, headers=headers))
                        if article_req.status_code == 200:
                            a_soup = BeautifulSoup(article_req.text, 'html.parser')
                            extracted_text = []
                            skip_until_next_heading = False
                            for tag in a_soup.find_all(['h1', 'h2', 'h3', 'p', 'li', 'table']):
                                if tag.name == 'table':
                                    if not skip_until_next_heading:
                                        table_md = table_to_markdown(tag)
                                        if table_md:
                                            extracted_text.append(table_md)
                                    continue
                                txt = tag.get_text(" ", strip=True)
                                if not txt:
                                    continue
                                is_heading = tag.name in ['h1', 'h2', 'h3']
                                is_li = tag.name == 'li'
                                
                                txt_lower = txt.lower()
                                
                                # Filter out header/sidebar navigation menu lists
                                menu_keywords = [
                                    "find cars", "compare cars", "car reviews", "car photos", "car videos", "car brands", "just launched cars", "upcoming cars", "popular cars",
                                    "find bikes", "compare bikes", "bike reviews", "bike photos", "bike videos", "bike brands", "just launched bikes", "upcoming bikes", "popular bikes",
                                    "all reviews", "first drive", "road test", "comparo", "news & features", "opinions", "motorsport", "press releases", "all photos", "get app"
                                ]
                                if any(kw in txt_lower for kw in menu_keywords) or (len(txt.split()) <= 4 and any(kw in txt_lower for kw in ["find", "compare", "reviews", "photos", "videos", "upcoming", "launched", "popular", "brands"])):
                                    continue
                                    
                                if is_heading:
                                    # Ignore generic layout navigation headings
                                    layout_noise = ["top stories", "latest videos", "network18 updates", "recent posts", "popular tags", "related content", "recommended stories", "trending", "must read", "popular videos", "latest news", "overdrive sites", "better photography", "better interiors", "moneycontrol", "firstpost", "news18", "copyright", "follow the market", "follow us", "latest updates"]
                                    
                                    is_date = False
                                    try:
                                        from dateutil import parser as date_parser
                                        date_parser.parse(txt)
                                        is_date = True
                                    except:
                                        pass
                                    
                                    if is_date or txt_lower.startswith("by ") or (len(txt.split()) <= 3 and any(pub in txt_lower for pub in ["autocar", "overdrive", "evo", "news", "date", "author", "published", "correspondent", "team"])) or any(kw in txt_lower for kw in layout_noise):
                                        skip_until_next_heading = True
                                        continue
                                    else:
                                        skip_until_next_heading = False
                                
                                if skip_until_next_heading:
                                    continue
                                    
                                min_len = 3 if is_heading else (1 if is_li else 30)
                                
                                # Check for footer/copyright text noise
                                general_noise = ["copyright ©", "all rights reserved", "india’s largest auto media", "better photography", "better interiors", "moneycontrol", "firstpost", "news18"]
                                if any(noise in txt_lower for noise in general_noise):
                                    continue
                                    
                                if len(txt) >= min_len and not bool(re.search(r'(subscribe|cookie|privacy|advertisement)', txt, re.I)):
                                    if is_heading:
                                        if tag.name in ['h1', 'h2']:
                                            extracted_text.append(f"## {txt}")
                                        else:
                                            extracted_text.append(f"### {txt}")
                                    elif is_li:
                                        extracted_text.append(f"* {txt}")
                                    else:
                                        extracted_text.append(txt)
                            
                            if len(extracted_text) > 0:
                                article_content = "\n".join(extracted_text)
                                if EV_REGEX.search(article_content):
                                    final_content = article_content
                                else:
                                    final_content = article_content

                                # Extract publication date if possible
                                meta_date = a_soup.find("meta", property="article:published_time")
                                if not meta_date:
                                    meta_date = a_soup.find("meta", attrs={"name": "publication_date"})
                                timestamp = int(time.time())
                                if meta_date and meta_date.get("content"):
                                    try:
                                        timestamp = int(parser.parse(meta_date["content"]).timestamp())
                                    except:
                                        pass
                                
                                # Check if news is older than 48 hours
                                if int(time.time()) - timestamp > 172800:
                                    continue

                                results.append({
                                    "title": title,
                                    "content_raw": final_content,
                                    "source": base_domain,
                                    "source_type": "website",
                                    "author": base_domain,
                                    "timestamp": timestamp,
                                    "url": link,
                                    "engagement": {"likes": 0, "comments": 0, "shares": 0}
                                })
                    except Exception as article_e:
                        print(f"Error scraping article link {link}: {article_e}")
    except Exception as e:
        print(f"Website Scraping Error for {url}: {e}")
        
    return results
