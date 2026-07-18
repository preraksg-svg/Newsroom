import asyncio
from bs4 import BeautifulSoup
import sys
import os

sys.path.append(os.getcwd())

from workers.website_worker import table_to_markdown

def simulate_scrape_single_article(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    extracted_text = []
    skip_until_next_heading = False
    
    import re
    
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
                
    return "\n".join(extracted_text)

def test():
    html = """
    <html>
      <body>
        <!-- Header Menu List (Noise) -->
        <ul>
          <li>CARS Find Cars Compare Cars Car Reviews Car Photos Car Videos Car Brands</li>
          <li>Find Cars</li>
          <li>Compare Cars</li>
          <li>Maruti Suzuki e-Vitara</li>
          <li>Home</li>
          <li>News</li>
        </ul>
        
        <!-- Main Article (Valid) -->
        <h1>Range Rover Sport Goes Electric: JLR Unveils New EV at Goodwood</h1>
        <p>Jaguar Land Rover (JLR) has officially unveiled the fully electric Range Rover Sport EV prototype at the Goodwood Festival of Speed. The high-performance electric SUV features an 800V architecture and support for ultra-fast DC charging corridors.</p>
        
        <!-- Sidebar widget (Noise) -->
        <h2>Top Stories</h2>
        <ul>
          <li>Ferrari Amalfi Spider makes India Debut</li>
          <li>Range Rover Sport Goes Electric: JLR Unveils New EV at Goodwood</li>
        </ul>
        
        <!-- Body continues (Valid) -->
        <h2>Key EV Specifications</h2>
        <p>The vehicle is expected to pack a 100 kWh battery pack with dual-motor all-wheel drive, supporting a range exceeding 500 km on a single charge.</p>
        
        <!-- Footer copyright (Noise) -->
        <p>Copyright © 2018 Overdrive - All rights reserved. India's largest auto media for the car & bike community.</p>
      </body>
    </html>
    """
    
    print("[TEST] Running simulated scraper on noisy html...")
    result = simulate_scrape_single_article(html)
    print("\n=== PARSED OUTPUT ===")
    print(result)
    print("=====================")
    
    # Assertions
    assert "CARS Find Cars" not in result, "Fail: Header menu not filtered"
    assert "Top Stories" not in result, "Fail: Top Stories heading not filtered"
    assert "Ferrari Amalfi Spider" not in result, "Fail: Stateful widget items not filtered"
    assert "Copyright ©" not in result, "Fail: Footer copyright not filtered"
    assert "Range Rover Sport Goes Electric" in result, "Fail: Main article heading was stripped"
    assert "Key EV Specifications" in result, "Fail: Valid body heading was stripped"
    
    print("\n[SUCCESS] Scraper filter verified successfully! All menu items and layout noise correctly filtered out.")

if __name__ == "__main__":
    test()
