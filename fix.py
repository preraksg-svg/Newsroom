import re

def fix_website_worker():
    with open('workers/website_worker.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    pattern = re.compile(r'    if not results:\n        # Fallback LLM news generator.*?(?=    return results)', re.DOTALL)
    new_content = pattern.sub('', content)
    
    with open('workers/website_worker.py', 'w', encoding='utf-8') as f:
        f.write(new_content)

def fix_twitter_worker():
    with open('workers/twitter_worker.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    pattern = re.compile(r'    if not results:\n        title_val = f\"Update from \{handle\}\".*?(?=    return results)', re.DOTALL)
    new_content = pattern.sub('', content)
    
    with open('workers/twitter_worker.py', 'w', encoding='utf-8') as f:
        f.write(new_content)

fix_website_worker()
fix_twitter_worker()
print('Cleaned scrapers!')
