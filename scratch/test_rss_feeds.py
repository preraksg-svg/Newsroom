import feedparser

feeds = [
    'https://auto.ndtv.com/rss/news',
    'https://auto.ndtv.com/rss',
    'https://www.motorbeam.com/feed/',
    'https://www.team-bhp.com/news/feed/',
    'https://www.carwale.com/news/rss/',
]

for f_url in feeds:
    f = feedparser.parse(f_url)
    print(f"{f_url}: {len(f.entries)} entries")
    for e in f.entries[:2]:
        title = e.get("title", "")
        print(f"  - {title[:70]}")
