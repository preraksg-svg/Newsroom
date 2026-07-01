import urllib.request
import feedparser

variants = [
    "https://www.saurenergy.com/feed/",
    "https://www.saurenergy.com/rss/",
    "https://cleantechnica.com/category/india/feed/",
    "https://cleantechnica.com/tag/india/feed/",
    "https://cleantechnica.com/feed/" # CleanTechnica global feed is known to work
]

for url in variants:
    print(f"Testing: {url}")
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read()
            f = feedparser.parse(html)
            print(f" -> SUCCESS! Entries count: {len(f.entries)}")
    except Exception as e:
        print(f" -> FAILED: {e}")
