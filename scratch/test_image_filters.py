import sys
import os

sys.path.append(os.getcwd())
from zapway_publisher import fetch_all_image_urls

urls = [
    "https://www.mercomindia.com/coal-india-announces-winner-of-auction-for-20-mw-floating-solar-consultancy",
    "https://moderndiplomacy.eu/2026/07/04/can-europe-keep-up-with-chinas-export-surge/",
]

for url in urls:
    print(f"\nURL: {url}")
    images = fetch_all_image_urls(url)
    print("Found Images:")
    for img in images:
        print(f"  - {img}")
