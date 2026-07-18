"""
Updates website_worker.py direct direct HTML scraper loop (lines 318-365)
to group list elements before parsing them into text.
"""
import os

target = 'workers/website_worker.py'

with open(target, 'r', encoding='utf-8') as f:
    content = f.read()

OLD_FALLBACK = """                            extracted_text = []
                            skip_until_next_heading = False
                            for tag in a_soup.find_all(['h1', 'h2', 'h3', 'p', 'li', 'table']):
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
                                
                                if is_heading:
                                    layout_noise = ["top stories", "latest videos", "network18 updates", "recent posts", "popular tags", "related content", "recommended stories", "trending", "must read", "popular videos", "latest news", "overdrive sites", "better photography", "better interiors", "moneycontrol", "firstpost", "news18", "copyright", "follow the market", "follow us", "latest updates"]
                                    is_date = False
                                    try:
                                        from dateutil import parser as date_parser
                                        date_parser.parse(txt)
                                        is_date = True
                                    except:
                                        pass
                                    
                                    if is_date or txt_lower.startswith("by ") or any(kw in txt_lower for kw in layout_noise):
                                        skip_until_next_heading = True
                                        continue
                                    else:
                                        skip_until_next_heading = False
                                
                                if skip_until_next_heading:
                                    continue
                                    
                                min_len = 3 if is_heading else (3 if is_li else 30)
                                general_noise = ["copyright ©", "all rights reserved", "india’s largest auto media", "better photography", "better interiors", "moneycontrol", "firstpost", "news18"]
                                if any(noise in txt_lower for noise in general_noise):
                                    continue
                                    
                                if len(txt) >= min_len and not bool(re.search(r'(subscribe|cookie|privacy|advertisement)', txt, re.I)):
                                    if is_heading:
                                        extracted_text.append(f"## {txt}" if tag.name in ['h1', 'h2'] else f"### {txt}")
                                    elif is_li:
                                        extracted_text.append(f"* {txt}")
                                    else:
                                        extracted_text.append(txt)"""

NEW_FALLBACK = """                            # Group list tags (ul/ol) into cohesive blocks BEFORE sequential tag parsing
                            for list_tag in a_soup.find_all(['ul', 'ol']):
                                is_ordered = list_tag.name == 'ol'
                                list_items = []
                                for idx, li in enumerate(list_tag.find_all('li')):
                                    li_txt = li.get_text(" ", strip=True)
                                    if li_txt:
                                        prefix = f"{idx+1}." if is_ordered else "*"
                                        list_items.append(f"{prefix} {li_txt}")
                                if list_items:
                                    new_p = a_soup.new_tag("p")
                                    new_p.string = "\\n".join(list_items)
                                    list_tag.replace_with(new_p)

                            extracted_text = []
                            skip_until_next_heading = False
                            for tag in a_soup.find_all(['h1', 'h2', 'h3', 'p', 'table']):
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
                                txt_lower = txt.lower()
                                
                                if is_heading:
                                    layout_noise = ["top stories", "latest videos", "network18 updates", "recent posts", "popular tags", "related content", "recommended stories", "trending", "must read", "popular videos", "latest news", "overdrive sites", "better photography", "better interiors", "moneycontrol", "firstpost", "news18", "copyright", "follow the market", "follow us", "latest updates"]
                                    is_date = False
                                    try:
                                        from dateutil import parser as date_parser
                                        date_parser.parse(txt)
                                        is_date = True
                                    except:
                                        pass
                                    
                                    if is_date or txt_lower.startswith("by ") or any(kw in txt_lower for kw in layout_noise):
                                        skip_until_next_heading = True
                                        continue
                                    else:
                                        skip_until_next_heading = False
                                
                                if skip_until_next_heading:
                                    continue
                                    
                                is_list_block = txt.startswith("* ") or (txt and txt[0].isdigit() and ". " in txt[:5])
                                min_len = 3 if is_heading else (5 if is_list_block else 30)
                                general_noise = ["copyright ©", "all rights reserved", "india’s largest auto media", "better photography", "better interiors", "moneycontrol", "firstpost", "news18"]
                                if any(noise in txt_lower for noise in general_noise):
                                    continue
                                    
                                if len(txt) >= min_len and not bool(re.search(r'(subscribe|cookie|privacy|advertisement)', txt, re.I)):
                                    if is_heading:
                                        extracted_text.append(f"## {txt}" if tag.name in ['h1', 'h2'] else f"### {txt}")
                                    else:
                                        extracted_text.append(txt)"""

if OLD_FALLBACK in content:
    new_content = content.replace(OLD_FALLBACK, NEW_FALLBACK, 1)
    with open(target, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: Updated scrape_website fallback loop to group list elements.")
else:
    # Try with raw variations in content
    print("FAILED: Could not find exact OLD_FALLBACK pattern match.")
