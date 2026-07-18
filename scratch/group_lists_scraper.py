"""
Modifies website_worker.py to extract lists (ul/ol) as structured blocks
rather than sequential flat <li> strings.
"""
import os

target = 'workers/website_worker.py'

with open(target, 'r', encoding='utf-8') as f:
    content = f.read()

# Define updated scrape_single_article_page body parser section
OLD_EXTRACTION = """            for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'li', 'table']):
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
                    layout_noise = [
                        "top stories", "latest videos", "network18 updates", "recent posts",
                        "popular tags", "related content", "recommended stories", "trending",
                        "must read", "popular videos", "latest news", "overdrive sites",
                        "better photography", "better interiors", "moneycontrol", "firstpost",
                        "news18", "copyright", "follow the market", "follow us", "latest updates"
                    ]
                    is_date = False
                    try:
                        from dateutil import parser as date_parser
                        date_parser.parse(txt)
                        is_date = True
                    except:
                        pass
                    if (is_date or txt_lower.startswith("by ")
                            or any(kw in txt_lower for kw in layout_noise)):
                        skip_until_next_heading = True
                        continue
                    else:
                        skip_until_next_heading = False

                if skip_until_next_heading:
                    continue

                general_noise = [
                    "copyright ©", "all rights reserved", "india's largest auto media",
                    "better photography", "better interiors", "moneycontrol", "firstpost", "news18"
                ]
                if any(noise in txt_lower for noise in general_noise):
                    continue

                min_len = 3 if is_heading else (3 if is_li else 30)

                if len(txt) >= min_len and not bool(re.search(r'(subscribe|cookie|privacy|advertisement)', txt, re.I)):
                    if is_heading:
                        extracted_text.append(f"## {txt}" if tag.name in ['h1', 'h2'] else f"### {txt}")
                    elif is_li:
                        extracted_text.append(f"* {txt}")
                    else:
                        extracted_text.append(txt)"""

NEW_EXTRACTION = """            # Group list tags (ul/ol) into cohesive blocks BEFORE sequential tag parsing
            # by replacing their DOM structures with pre-formatted markdown blocks.
            for list_tag in soup.find_all(['ul', 'ol']):
                is_ordered = list_tag.name == 'ol'
                list_items = []
                for idx, li in enumerate(list_tag.find_all('li')):
                    li_txt = li.get_text(" ", strip=True)
                    if li_txt:
                        prefix = f"{idx+1}." if is_ordered else "*"
                        list_items.append(f"{prefix} {li_txt}")
                if list_items:
                    # Create a new paragraph node containing the full list block
                    new_p = soup.new_tag("p")
                    new_p.string = "\\n".join(list_items)
                    list_tag.replace_with(new_p)

            for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'table']):
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
                    layout_noise = [
                        "top stories", "latest videos", "network18 updates", "recent posts",
                        "popular tags", "related content", "recommended stories", "trending",
                        "must read", "popular videos", "latest news", "overdrive sites",
                        "better photography", "better interiors", "moneycontrol", "firstpost",
                        "news18", "copyright", "follow the market", "follow us", "latest updates"
                    ]
                    is_date = False
                    try:
                        from dateutil import parser as date_parser
                        date_parser.parse(txt)
                        is_date = True
                    except:
                        pass
                    if (is_date or txt_lower.startswith("by ")
                            or any(kw in txt_lower for kw in layout_noise)):
                        skip_until_next_heading = True
                        continue
                    else:
                        skip_until_next_heading = False

                if skip_until_next_heading:
                    continue

                general_noise = [
                    "copyright ©", "all rights reserved", "india's largest auto media",
                    "better photography", "better interiors", "moneycontrol", "firstpost", "news18"
                ]
                if any(noise in txt_lower for noise in general_noise):
                    continue

                # If this paragraph represents a list block we created above
                is_list_block = txt.startswith("* ") or (txt and txt[0].isdigit() and ". " in txt[:5])
                min_len = 3 if is_heading else (5 if is_list_block else 30)

                if len(txt) >= min_len and not bool(re.search(r'(subscribe|cookie|privacy|advertisement)', txt, re.I)):
                    if is_heading:
                        extracted_text.append(f"## {txt}" if tag.name in ['h1', 'h2'] else f"### {txt}")
                    else:
                        extracted_text.append(txt)"""

if OLD_EXTRACTION in content:
    new_content = content.replace(OLD_EXTRACTION, NEW_EXTRACTION, 1)
    with open(target, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: Updated scrape_single_article_page in website_worker.py to group lists.")
else:
    print("FAILED: Could not find OLD_EXTRACTION pattern in website_worker.py")
