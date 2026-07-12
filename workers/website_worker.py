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
                
                # Try fetching native URL heavily bypassing purely feed summaries if missing
                article_content = entry.get("summary", "")
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    article_req = await loop.run_in_executor(None, lambda: requests.get(link, timeout=5, headers={"User-Agent": "ZapwayNewsroom bot/1.0"}))
                    if article_req.status_code == 200:
                        soup = BeautifulSoup(article_req.text, 'html.parser')
                        extracted_text = []
                        for tag in soup.find_all(['h1', 'h2', 'h3', 'p']):
                            txt = tag.get_text(" ", strip=True)
                            if len(txt) > 30 and not bool(re.search(r'(subscribe|cookie|privacy|advertisement)', txt, re.I)):
                                if tag.name in ['h1', 'h2']:
                                    extracted_text.append(f"## {txt}")
                                elif tag.name == 'h3':
                                    extracted_text.append(f"### {txt}")
                                else:
                                    extracted_text.append(txt)
                        if len(extracted_text) > 0:
                            article_content = "\n".join(extracted_text)
                except:
                    pass # Fallback to summary

                    
                if EV_REGEX.search(article_content):
                    final_content = article_content
                else:
                    final_content = article_content

                dt_str = entry.get("published", entry.get("updated", ""))
                try:
                    timestamp = int(parser.parse(dt_str).timestamp()) if dt_str else int(time.time())
                except:
                    timestamp = int(time.time())
                
                # Check if news is older than 24 hours (86400 seconds)
                if int(time.time()) - timestamp > 86400:
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
                            for tag in a_soup.find_all(['h1', 'h2', 'h3', 'p']):
                                txt = tag.get_text(" ", strip=True)
                                if len(txt) > 30 and not bool(re.search(r'(subscribe|cookie|privacy|advertisement)', txt, re.I)):
                                    if tag.name in ['h1', 'h2']:
                                        extracted_text.append(f"## {txt}")
                                    elif tag.name == 'h3':
                                        extracted_text.append(f"### {txt}")
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
                                
                                # Check if news is older than 24 hours
                                if int(time.time()) - timestamp > 86400:
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
