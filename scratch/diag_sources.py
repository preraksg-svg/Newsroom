import requests
from bs4 import BeautifulSoup
import re
import sys, os
sys.path.append(os.getcwd())

EV_REGEX = re.compile(r'(electric| ev |evs|zero emission|battery|charging|charge|tesla|byd|ola|ather|tata|mahindra|nexon|tiago|xuv400|comet|vida|chetak|iqube|electrif)', re.IGNORECASE)

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}

for url in ['https://auto.ndtv.com', 'https://www.autocarindia.com', 'https://www.overdrive.in']:
    print(f"\n--- Testing: {url} ---")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {r.status_code}")
        soup = BeautifulSoup(r.text, 'html.parser')
        # Check for RSS feed
        rss_tag = soup.find('link', attrs={'type': 'application/rss+xml'})
        print(f"RSS: {rss_tag.get('href') if rss_tag else 'NONE'}")
        # Count EV article links
        links = [a.get_text(" ", strip=True) for a in soup.find_all('a', href=True)]
        ev_links = [l for l in links if EV_REGEX.search(l) and len(l) > 25]
        print(f"EV links found: {len(ev_links)}")
        for l in ev_links[:3]:
            print(f"  - {l[:70]}")
    except Exception as e:
        print(f"ERROR: {e}")
