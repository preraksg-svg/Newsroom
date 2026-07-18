"""
Restores scrape_single_article_page at the correct location in workers/website_worker.py
since it was accidentally omitted during regex update.
"""
import os

target = 'workers/website_worker.py'

with open(target, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the updated helper function with negative lookbehind/lookahead for hyphens
UPDATED_HELPER = """def _strip_nav_from_soup(soup):
    \"\"\"Remove nav/header/footer/sidebar elements from a BeautifulSoup tree.
    Uses negative lookbehind/lookahead (?<!-) and (?!-) to ensure that classes like
    'single-no-sidebar' or 'site-content' are not false-positively decomposed.
    \"\"\"
    import re as _re

    NAV_TAGS = ['nav', 'header', 'footer', 'aside']
    NAV_CLASS_RE = _re.compile(
        r'(?<!-)\\b(nav|navbar|navigation|menu|header|footer|sidebar|breadcrumb|'
        r'topbar|top-bar|bottom-bar|dropdown|flyout|mega-menu|off-canvas|'
        r'site-header|site-footer|page-header|page-footer|widget|'
        r'advertisement|promo|social-share|share-bar|related|recommended|'
        r'trending|popular-posts|tag-cloud|author-bio|comment|pagination|'
        r'cookie|gdpr|newsletter|subscribe|sticky|fixed-bar)\\b(?!-)',
        _re.IGNORECASE
    )
    NAV_ID_RE = _re.compile(
        r'(?<!-)\\b(nav|header|footer|sidebar|menu|topnav|mainnav|sidenav|'
        r'breadcrumb|top-bar|bottom-bar|social|share|related|trending|'
        r'popular|tags|comments|pagination|cookie|newsletter|subscribe)\\b(?!-)',
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
    \"\"\"Direct HTML parser for a single article page.
    Strips nav/header/footer/sidebar from the DOM BEFORE parsing
    so navigation menus can NEVER appear as article content.
    \"\"\"
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

                if is_heading:
                    layout_noise = [
                        "top stories", "latest videos", "network18 updates", "recent posts",
                        "popular tags", "related content", "recommended stories", "trending",
                        "must read", "popular videos", "latest news", "overdrive sites",
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

                min_len = 3 if is_heading else (3 if is_li else 30)

                if len(txt) >= min_len and not bool(re.search(r'(subscribe|cookie|privacy|advertisement)', txt, re.I)):
                    if is_heading:
                        extracted_text.append(f"## {txt}" if tag.name in ['h1', 'h2'] else f"### {txt}")
                    elif is_li:
                        extracted_text.append(f"* {txt}")
                    else:
                        extracted_text.append(txt)

            if extracted_text:
                return "\\n".join(extracted_text)
    except Exception as e:
        print(f"Error scraping single page {url}: {e}")
    return \"\"\""""

# Replace _strip_nav_from_soup definition in content
start_idx = content.find("def _strip_nav_from_soup(soup):")
end_idx = content.find("def llm_filter_website(text: str):")
if end_idx == -1:
    end_idx = content.find("def llm_filter_website(text: str) -> str:")

if start_idx != -1 and end_idx != -1:
    before = content[:start_idx]
    after = content[end_idx:]
    new_content = before + UPDATED_HELPER + "\n\n\n" + after
    with open(target, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: Restored scrape_single_article_page in website_worker.py")
else:
    print(f"FAILED: start_idx={start_idx}, end_idx={end_idx}")
