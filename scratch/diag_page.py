import requests
from bs4 import BeautifulSoup
import re
import sys, os
sys.path.append(os.getcwd())

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}

# Test the direct page fetch  
url = 'https://www.overdrive.in/news-cars/range-rover-sport-goes-electric-jlr-unveils-new-ev-at-goodwood/'
r = requests.get(url, headers=headers, timeout=10)
print(f"Status: {r.status_code}")
print(f"Content length: {len(r.text)}")

soup = BeautifulSoup(r.text, 'html.parser')
# Count all parseable tags
tags = soup.find_all(['h1', 'h2', 'h3', 'p', 'li', 'table'])
print(f"Total tags found: {len(tags)}")

# Show first 15 tags with raw text
print("\n--- First 15 tags ---")
for tag in tags[:15]:
    txt = tag.get_text(" ", strip=True)
    print(f"[{tag.name}] ({len(txt)} chars): {txt[:80]!r}")

# Check what article body containers exist
article_containers = soup.find_all(['article', 'main', 'div'], attrs={'class': re.compile(r'article|story|content|body|post', re.I)})
print(f"\n\nArticle containers: {len(article_containers)}")
for c in article_containers[:5]:
    cls = c.get('class', [])
    ptags = c.find_all('p')
    print(f"  <{c.name} class={cls[:2]}> => {len(ptags)} <p> tags")
