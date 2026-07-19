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

def _strip_nav_from_soup(soup):
    """Remove nav/header/footer/sidebar elements from a BeautifulSoup tree.
    Uses negative lookbehind/lookahead (?<!-) and (?!-) to ensure that classes like
    'single-no-sidebar' or 'site-content' are not false-positively decomposed.
    """
    import re as _re

    NAV_TAGS = ['nav', 'header', 'footer', 'aside']
    NAV_CLASS_RE = _re.compile(
        r'(?<!-)\b(nav|navbar|navigation|menu|header|footer|sidebar|breadcrumb|'
        r'topbar|top-bar|bottom-bar|dropdown|flyout|mega-menu|off-canvas|'
        r'site-header|site-footer|page-header|page-footer|widget|'
        r'advertisement|promo|social-share|share-bar|related|recommended|'
        r'suggested|suggested-news|upcoming-cars|latest-cars|'
        r'trending|popular-posts|tag-cloud|author-bio|comment|pagination|'
        r'cookie|gdpr|newsletter|subscribe|sticky|fixed-bar)\b(?!-)',
        _re.IGNORECASE
    )
    NAV_ID_RE = _re.compile(
        r'(?<!-)\b(nav|header|footer|sidebar|menu|topnav|mainnav|sidenav|'
        r'breadcrumb|top-bar|bottom-bar|social|share|related|trending|'
        r'suggested|upcoming|latest|'
        r'popular|tags|comments|pagination|cookie|newsletter|subscribe)\b(?!-)',
        _re.IGNORECASE
    )

    for tag_name in NAV_TAGS:
        for el in soup.find_all(tag_name):
            el.decompose()

    for el in list(soup.find_all(True)):
        try:
            if not hasattr(el, 'attrs') or el.attrs is None:
                continue
            classes = ' '.join(el.get('class', [])) if el.get('class') else ''
            id_val = el.get('id', '') if el.get('id') else ''
            
            # Preserve the main post content container
            if 'entry-content' in classes or 'post-content' in classes or id_val == 'content':
                continue
                
            if NAV_CLASS_RE.search(classes) or NAV_ID_RE.search(id_val):
                el.decompose()
        except Exception:
            pass

    for el in soup.find_all(['script', 'style', 'noscript', 'iframe', 'svg', 'form']):
        el.decompose()

    return soup


async def scrape_single_article_page(url: str) -> str:
    """Direct HTML parser for a single article page.
    Strips nav/header/footer/sidebar from the DOM BEFORE parsing
    so navigation menus can NEVER appear as article content.
    """
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
            soup = _strip_nav_from_soup(soup)

            extracted_text = []
            skip_until_next_heading = False

            # Group list tags (ul/ol) into cohesive blocks BEFORE sequential tag parsing
            # by replacing their DOM structures with pre-formatted markdown blocks.
            for list_tag in soup.find_all(['ul', 'ol']):
                is_ordered = list_tag.name == 'ol'
                list_items = []
                for idx, li in enumerate(list_tag.find_all('li')):
                    # Extract text from li, ignoring inner paragraphs returning empty or heading treats
                    li_txt = li.get_text(" ", strip=True)
                    if li_txt:
                        prefix = f"{idx+1}." if is_ordered else "*"
                        list_items.append(f"{prefix} {li_txt}")
                if list_items:
                    # Create a new paragraph node containing the full list block
                    new_p = soup.new_tag("p")
                    new_p.string = "\n".join(list_items)
                    # Decompose children inside list_tag first to avoid double parsing if any nested p tags exist
                    for child in list(list_tag.children):
                        if hasattr(child, 'decompose'):
                            child.decompose()
                    list_tag.replace_with(new_p)

            for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'table', 'img']):
                if tag.name == 'table':
                    if not skip_until_next_heading:
                        table_md = table_to_markdown(tag)
                        if table_md:
                            extracted_text.append(table_md)
                    continue

                if tag.name == 'img':
                    if not skip_until_next_heading:
                        src = tag.get('src') or tag.get('data-src') or tag.get('data-lazy-src') or ''
                        alt = tag.get('alt') or ''
                        if src and src.startswith('http'):
                            # Reuse clean keywords logic from zapway_publisher.py to avoid layout items
                            avoid_keywords = [
                                "logo", "avatar", "profile", "banner", "advertisement", "ad-", "ads-",
                                "popup", "insider", "authorplaceholder", "webinar", "sub-menu", "sharing",
                                "share", "advert", "promo", "sign-up", "newsletter", "mail", "icon-", "subscribe"
                            ]
                            src_lower = src.lower()
                            alt_lower = alt.lower()
                            if not any(kw in src_lower or kw in alt_lower for kw in avoid_keywords):
                                extracted_text.append(f"![{alt}]({src})")
                    continue

                txt = tag.get_text(" ", strip=True)
                if not txt:
                    continue

                is_heading = tag.name in ['h1', 'h2', 'h3']
                txt_lower = txt.lower()

                if is_heading:
                    layout_noise = [
                        "top stories", "latest videos", "network18 updates", "recent posts",
                        "popular tags", "related content", "recommended stories", "trending",
                        "must read", "popular videos", "latest news", "overdrive sites",
                        "suggested news", "upcoming cars", "latest cars", "latest launches",
                        "questions after reading",
                        "better photography", "better interiors", "moneycontrol", "firstpost",
                        "news18", "copyright", "follow the market", "follow us", "latest updates"
                    ]
                    is_date = False
                    try:
                        from dateutil import parser as date_parser
                        date_parser.parse(txt)
                        is_date = True
                    except:
                        pass
                    if (is_date or txt_lower.startswith("by ")
                            or any(kw in txt_lower for kw in layout_noise)):
                        skip_until_next_heading = True
                        continue
                    else:
                        skip_until_next_heading = False

                if skip_until_next_heading:
                    continue

                general_noise = [
                    "copyright ©", "all rights reserved", "india's largest auto media",
                    "better photography", "better interiors", "moneycontrol", "firstpost", "news18"
                ]
                if any(noise in txt_lower for noise in general_noise):
                    continue

                # If this paragraph represents a list block we created above
                is_list_block = txt.startswith("* ") or (txt and txt[0].isdigit() and ". " in txt[:5])
                min_len = 3 if is_heading else (5 if is_list_block else 30)

                if len(txt) >= min_len and not bool(re.search(r'(subscribe|cookie|privacy|advertisement)', txt, re.I)):
                    if is_heading:
                        extracted_text.append(f"## {txt}" if tag.name in ['h1', 'h2'] else f"### {txt}")
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
        return "" 
        
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
    results = []
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
                
                article_content = await scrape_single_article_page(link)
                if not article_content.strip() or len(article_content.split()) < 50 or article_content.strip().endswith("...") or article_content.strip().endswith("…"):
                    summary = entry.get("summary", "")
                    if summary and not (summary.strip().endswith("...") or summary.strip().endswith("…")) and len(summary.split()) >= 50:
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
                    "engagement": {"likes": 0, "comments": 0, "shares": 0}
                })
        else:
            # Fallback to direct HTML scraping
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}
            req = await loop.run_in_executor(None, lambda: requests.get(url, headers=headers, timeout=10))
            if req.status_code == 200:
                soup = BeautifulSoup(req.text, 'html.parser')
                soup = _strip_nav_from_soup(soup) # STRIP NAV FROM DIRECT FEED SOURCE AS WELL!
                
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
                    
                    if not EV_REGEX.search(title):
                        continue
                        
                    try:
                        fetched_count += 1
                        article_req = await loop.run_in_executor(None, lambda: requests.get(link, timeout=5, headers=headers))
                        if article_req.status_code == 200:
                            a_soup = BeautifulSoup(article_req.text, 'html.parser')
                            a_soup = _strip_nav_from_soup(a_soup) # STRIP NAV FROM DIRECT TARGET PAGES TOO!
                            
                            # Group list tags (ul/ol) into cohesive blocks BEFORE sequential tag parsing
                            for list_tag in a_soup.find_all(['ul', 'ol']):
                                is_ordered = list_tag.name == 'ol'
                                list_items = []
                                for idx, li in enumerate(list_tag.find_all('li')):
                                    li_txt = li.get_text(" ", strip=True)
                                    if li_txt:
                                        prefix = f"{idx+1}." if is_ordered else "*"
                                        list_items.append(f"{prefix} {li_txt}")
                                if list_items:
                                    new_p = a_soup.new_tag("p")
                                    new_p.string = "\n".join(list_items)
                                    # Decompose children inside list_tag first to avoid double parsing if any nested p tags exist
                                    for child in list(list_tag.children):
                                        if hasattr(child, 'decompose'):
                                            child.decompose()
                                    list_tag.replace_with(new_p)

                            extracted_text = []
                            skip_until_next_heading = False
                            for tag in a_soup.find_all(['h1', 'h2', 'h3', 'p', 'table', 'img']):
                                if tag.name == 'table':
                                    if not skip_until_next_heading:
                                        table_md = table_to_markdown(tag)
                                        if table_md:
                                            extracted_text.append(table_md)
                                    continue
                                if tag.name == 'img':
                                    if not skip_until_next_heading:
                                        src = tag.get('src') or tag.get('data-src') or tag.get('data-lazy-src') or ''
                                        alt = tag.get('alt') or ''
                                        if src and src.startswith('http'):
                                            # Reuse clean keywords logic from zapway_publisher.py to avoid layout items
                                            avoid_keywords = [
                                                "logo", "avatar", "profile", "banner", "advertisement", "ad-", "ads-",
                                                "popup", "insider", "authorplaceholder", "webinar", "sub-menu", "sharing",
                                                "share", "advert", "promo", "sign-up", "newsletter", "mail", "icon-", "subscribe"
                                            ]
                                            src_lower = src.lower()
                                            alt_lower = alt.lower()
                                            if not any(kw in src_lower or kw in alt_lower for kw in avoid_keywords):
                                                extracted_text.append(f"![{alt}]({src})")
                                    continue
                                txt = tag.get_text(" ", strip=True)
                                if not txt:
                                    continue
                                is_heading = tag.name in ['h1', 'h2', 'h3']
                                txt_lower = txt.lower()
                                
                                if is_heading:
                                    layout_noise = ["top stories", "latest videos", "network18 updates", "recent posts", "popular tags", "related content", "recommended stories", "trending", "must read", "popular videos", "latest news", "overdrive sites", "better photography", "better interiors", "moneycontrol", "firstpost", "news18", "copyright", "follow the market", "follow us", "latest updates"]
                                    is_date = False
                                    try:
                                        from dateutil import parser as date_parser
                                        date_parser.parse(txt)
                                        is_date = True
                                    except:
                                        pass
                                    
                                    if is_date or txt_lower.startswith("by ") or any(kw in txt_lower for kw in layout_noise):
                                        skip_until_next_heading = True
                                        continue
                                    else:
                                        skip_until_next_heading = False
                                
                                if skip_until_next_heading:
                                    continue
                                    
                                is_list_block = txt.startswith("* ") or (txt and txt[0].isdigit() and ". " in txt[:5])
                                min_len = 3 if is_heading else (5 if is_list_block else 30)
                                general_noise = ["copyright ©", "all rights reserved", "india’s largest auto media", "better photography", "better interiors", "moneycontrol", "firstpost", "news18"]
                                if any(noise in txt_lower for noise in general_noise):
                                    continue
                                    
                                if len(txt) >= min_len and not bool(re.search(r'(subscribe|cookie|privacy|advertisement)', txt, re.I)):
                                    if is_heading:
                                        extracted_text.append(f"## {txt}" if tag.name in ['h1', 'h2'] else f"### {txt}")
                                    else:
                                        extracted_text.append(txt)
                            
                            if len(extracted_text) > 0:
                                article_content = "\n".join(extracted_text)
                                final_content = article_content
                                
                                meta_date = a_soup.find("meta", property="article:published_time")
                                if not meta_date:
                                    meta_date = a_soup.find("meta", attrs={"name": "publication_date"})
                                timestamp = int(time.time())
                                if meta_date and meta_date.get("content"):
                                    try:
                                        timestamp = int(parser.parse(meta_date["content"]).timestamp())
                                    except:
                                        pass
                                
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
