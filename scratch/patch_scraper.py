"""
Rewrites scrape_single_article_page AND the secondary loop in website_worker.py
to strip nav/header/footer/sidebar from the DOM BEFORE parsing any tags.
"""
import re

TARGET = 'workers/website_worker.py'

with open(TARGET, 'r', encoding='utf-8') as f:
    content = f.read()

# ── New scrape_single_article_page ────────────────────────────────────────────
NEW_SINGLE = '''async def scrape_single_article_page(url: str) -> str:
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

            for tag in soup.find_all([\'h1\', \'h2\', \'h3\', \'p\', \'li\', \'table\']):
                if tag.name == \'table\':
                    if not skip_until_next_heading:
                        table_md = table_to_markdown(tag)
                        if table_md:
                            extracted_text.append(table_md)
                    continue

                txt = tag.get_text(" ", strip=True)
                if not txt:
                    continue

                is_heading = tag.name in [\'h1\', \'h2\', \'h3\']
                is_li = tag.name == \'li\'
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
                    "copyright ©", "all rights reserved", "india\'s largest auto media",
                    "better photography", "better interiors", "moneycontrol", "firstpost", "news18"
                ]
                if any(noise in txt_lower for noise in general_noise):
                    continue

                min_len = 3 if is_heading else (3 if is_li else 30)

                if len(txt) >= min_len and not bool(re.search(r\'(subscribe|cookie|privacy|advertisement)\', txt, re.I)):
                    if is_heading:
                        extracted_text.append(f"## {txt}" if tag.name in [\'h1\', \'h2\'] else f"### {txt}")
                    elif is_li:
                        extracted_text.append(f"* {txt}")
                    else:
                        extracted_text.append(txt)

            if extracted_text:
                return "\\n".join(extracted_text)
    except Exception as e:
        print(f"Error scraping single page {url}: {e}")
    return ""
'''

# Helper function to add before llm_filter_website
HELPER_FN = '''

def _strip_nav_from_soup(soup):
    """Remove nav/header/footer/sidebar elements from a BeautifulSoup tree.
    This is the ONLY correct way to prevent nav menu content from leaking
    into article text — text-matching approaches are always fragile.
    """
    import re as _re

    NAV_TAGS = ['nav', 'header', 'footer', 'aside']
    NAV_CLASS_RE = _re.compile(
        r'\\b(nav|navbar|navigation|menu|header|footer|sidebar|breadcrumb|'
        r'topbar|top-bar|bottom-bar|dropdown|flyout|mega-menu|off-canvas|'
        r'site-header|site-footer|page-header|page-footer|widget|'
        r'advertisement|promo|social-share|share-bar|related|recommended|'
        r'trending|popular-posts|tag-cloud|author-bio|comment|pagination|'
        r'cookie|gdpr|newsletter|subscribe|sticky|fixed-bar)\\b',
        _re.IGNORECASE
    )
    NAV_ID_RE = _re.compile(
        r'\\b(nav|header|footer|sidebar|menu|topnav|mainnav|sidenav|'
        r'breadcrumb|top-bar|bottom-bar|social|share|related|trending|'
        r'popular|tags|comments|pagination|cookie|newsletter|subscribe)\\b',
        _re.IGNORECASE
    )

    for tag_name in NAV_TAGS:
        for el in soup.find_all(tag_name):
            el.decompose()

    for el in list(soup.find_all(True)):
        try:
            el_classes = ' '.join(el.get('class', []))
            el_id = el.get('id', '')
            if NAV_CLASS_RE.search(el_classes) or NAV_ID_RE.search(el_id):
                el.decompose()
        except Exception:
            pass

    for el in soup.find_all(['script', 'style', 'noscript', 'iframe', 'svg', 'form']):
        el.decompose()

    return soup

'''

# Replace the old scrape_single_article_page
old_start = 'async def scrape_single_article_page(url: str) -> str:\n    """Direct HTML parser for a single article page."""'
new_content = content.replace(old_start, NEW_SINGLE, 1)

# Also remove the old function body up to the next top-level function
# The function ends at "    return \"\"\n\n" before "def llm_filter_website"
old_body_end = '    return ""\n\n\ndef llm_filter_website'
new_body_end = '\n\n' + HELPER_FN + '\ndef llm_filter_website'

if old_body_end not in new_content:
    # Try alternate ending
    old_body_end = '    return ""\n\n\ndef llm_filter_website'

new_content = new_content.replace(old_body_end, new_body_end, 1)

if new_content == content:
    print("WARNING: No replacement was made. Checking substrings...")
    print("old_start found:", old_start in content)
    print("old_body_end found:", old_body_end in content)
else:
    with open(TARGET, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"SUCCESS: Rewrote {TARGET}")
    print(f"New file length: {len(new_content)} chars")
