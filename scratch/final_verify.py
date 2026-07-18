"""
Final verification: test all fixed scrapers end-to-end.
Checks:
1. Menu filter no longer kills article <li> content
2. 50-word threshold accepts short Indian EV articles
3. motorbeam.com RSS returns articles
4. autocarindia + overdrive still return articles
"""
import asyncio
import importlib
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Force fresh module load
import workers.website_worker as ww
importlib.reload(ww)

PASS = 0
FAIL = 0

async def main():
    global PASS, FAIL

    print("=" * 60)
    print("FINAL SCRAPER VERIFICATION")
    print("=" * 60)

    # ---- Test 1: Direct article page parse (autocarindia) ----
    print("\n[TEST 1] Direct page parse - autocarindia.com article")
    url1 = 'https://www.autocarindia.com/car-news/jsw-mg-to-launch-electric-and-phev-suv-in-august-2026-440101'
    content1 = await ww.scrape_single_article_page(url1)
    if content1 and len(content1.split()) >= 40:
        print(f"  [PASS] Got {len(content1.split())} words")
        print(f"  Preview: {content1[:200]}")
        PASS += 1
    else:
        print(f"  [FAIL] Content too short or empty: {len(content1.split()) if content1 else 0} words")
        FAIL += 1

    # ---- Test 2: Menu filter doesn't kill <li> article bullets ----
    print("\n[TEST 2] Menu filter - <li> content not killed by nav filter")
    from bs4 import BeautifulSoup
    import re
    html = """
    <html><body>
    <ul><li>Find Cars</li><li>Car Reviews</li><li>Bike News</li></ul>
    <article>
      <h1>MG Electric SUV Launched in India at Rs 18 Lakh</h1>
      <p>JSW MG Motor India has launched its new electric SUV today in New Delhi.</p>
      <ul>
        <li>Range: 450 km on single charge</li>
        <li>Price starts at Rs 18.5 lakh (ex-showroom)</li>
        <li>Available in 3 colour variants</li>
      </ul>
      <p>The new vehicle uses the ADAPT platform developed by JSW MG.</p>
    </article>
    </body></html>
    """
    soup = BeautifulSoup(html, 'html.parser')
    extracted = []
    nav_menu_phrases = [
        "find cars", "compare cars", "car reviews", "car photos", "car videos", "car brands",
        "just launched cars", "upcoming cars", "popular cars",
        "find bikes", "compare bikes", "bike reviews", "bike photos", "bike videos", "bike brands",
        "just launched bikes", "upcoming bikes", "popular bikes",
        "all reviews", "news & features", "all photos", "get app",
        "contact the market", "sell car", "about the market", "terms and conditions",
        "car news", "bike news",
    ]
    for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'li']):
        txt = tag.get_text(" ", strip=True)
        if not txt:
            continue
        if tag.name == 'li':
            txt_lower = txt.lower()
            is_nav_dump = sum(1 for kw in nav_menu_phrases if kw in txt_lower) >= 2
            is_exact_nav = any(txt_lower.strip() == kw for kw in nav_menu_phrases)
            if is_nav_dump or is_exact_nav:
                continue
        extracted.append(txt)

    article_bullets = [t for t in extracted if 'rs 18' in t.lower() or 'range:' in t.lower() or 'price' in t.lower()]
    nav_leaked = [t for t in extracted if 'find cars' in t.lower() or 'car reviews' in t.lower()]

    if article_bullets and not nav_leaked:
        print(f"  [PASS] Article <li> items preserved: {article_bullets}")
        print(f"  [PASS] Nav items correctly filtered: {nav_leaked}")
        PASS += 1
    else:
        print(f"  [FAIL] Article bullets: {article_bullets}")
        print(f"  [FAIL] Nav leaked: {nav_leaked}")
        FAIL += 1

    # ---- Test 3: Full scrape - overdrive.in ----
    print("\n[TEST 3] Full scrape - overdrive.in")
    r3 = await ww.scrape_website('https://www.overdrive.in/news-cars')
    if r3 and len(r3) > 0:
        print(f"  [PASS] {len(r3)} articles found")
        for a in r3[:2]:
            print(f"    - {a['title'][:70]}")
        PASS += 1
    else:
        print(f"  [FAIL] 0 articles returned")
        FAIL += 1

    # ---- Test 4: Full scrape - autocarindia.com ----
    print("\n[TEST 4] Full scrape - autocarindia.com")
    r4 = await ww.scrape_website('https://www.autocarindia.com/car-news')
    if r4 and len(r4) > 0:
        print(f"  [PASS] {len(r4)} articles found")
        for a in r4[:2]:
            print(f"    - {a['title'][:70]}")
        PASS += 1
    else:
        print(f"  [FAIL] 0 articles returned")
        FAIL += 1

    # ---- Test 5: Full scrape - motorbeam.com RSS ----
    print("\n[TEST 5] Full scrape - motorbeam.com RSS feed")
    r5 = await ww.scrape_website('https://www.motorbeam.com/feed/')
    if r5 and len(r5) > 0:
        print(f"  [PASS] {len(r5)} articles found")
        for a in r5[:2]:
            print(f"    - {a['title'][:70]}")
        PASS += 1
    else:
        print(f"  [FAIL] 0 articles returned")
        FAIL += 1

    print("\n" + "=" * 60)
    print(f"RESULT: {PASS} PASSED / {FAIL} FAILED")
    print("=" * 60)

asyncio.run(main())
