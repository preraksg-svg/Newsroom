import asyncio
import sys
import os

sys.path.append(os.getcwd())

from layer3_generation.generation_fanout import run_microtask_a_with_retry

async def verify():
    test_url = "https://electrek.co/best-electric-vehicle-prices/"
    test_title = "Electric Vehicle Price Guide"
    test_content = """
    Electric vehicles prices are dropping across the market.
    * Model Y is starting at a lower price point now.
    * Chevrolet Bolt remains a strong budget option.
    * Tesla Superchargers are widely accessible.
    
    This guide shows the best prices available for electric cars today.
    """
    
    print("[VERIFICATION] Running generation fanout microtask...")
    result = await run_microtask_a_with_retry(test_content, url=test_url, title=test_title)
    
    print("\n=== VERIFICATION RESULTS ===")
    print("Title:", result.get("title"))
    print("\nImages Found:", len(result.get("images", [])))
    for idx, img in enumerate(result.get("images", [])[:5]):
        print(f"  - Image #{idx+1}: {img.get('url')}")
        
    print("\nSections & Bullet Points:")
    for sec in result.get("sections", []):
        print(f"\n  Section: {sec.get('heading')}")
        print(f"  Content: {sec.get('content')}")
        
    print("\n============================")

if __name__ == "__main__":
    asyncio.run(verify())
