"""
Rewrites workers/website_worker.py to use a refined, robust _strip_nav_from_soup function
that prevents false-positive decomposition of layout containers like "single-no-sidebar".
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

    return soup"""

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
    print("SUCCESS: Refined _strip_nav_from_soup in website_worker.py")
else:
    print(f"FAILED: start_idx={start_idx}, end_idx={end_idx}")
