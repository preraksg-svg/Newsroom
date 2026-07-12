"""
Playwright-based publisher for Zapway Newsroom.
Logs into zapway.app and fills the insert_news form, handles multiple sections
by clicking the "+ Section" button, and submits via "Publish Story" button.
"""
import sys
import asyncio
import json
import re
import os
from playwright.async_api import async_playwright

# Force UTF-8 output to avoid Windows cp1252 codec errors with emoji/unicode
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ZAPWAY_EMAIL = "prerak.sg@gmail.com"
ZAPWAY_PASSWORD = "132325"
ZAPWAY_INSERT_URL = "https://zapway.app/News/insert_news"


async def _login(page):
    """Log in using confirmed field IDs: #email and #password."""
    print("[PUBLISHER] Filling login credentials...")
    await page.wait_for_selector("#email", timeout=10000)
    await page.fill("#email", ZAPWAY_EMAIL)
    await page.fill("#password", ZAPWAY_PASSWORD)

    for sel in ['button[type="submit"]', 'button:has-text("Login")',
                'button:has-text("Sign in")', 'button:has-text("Log in")']:
        try:
            btn = page.locator(sel).first
            if await btn.count() > 0 and await btn.is_visible():
                await btn.click()
                print(f"[PUBLISHER] Login submitted via: {sel}")
                break
        except Exception:
            continue

    await page.wait_for_load_state("networkidle", timeout=20000)
    await asyncio.sleep(1)
    print(f"[PUBLISHER] Post-login URL: {page.url}")


def fetch_main_image_url(url: str) -> str:
    """Fetches the og:image or twitter:image metadata from the original source URL."""
    if not url:
        return ""
    try:
        import requests
        from bs4 import BeautifulSoup
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            
            # 1. og:image
            og_img = soup.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                return og_img.get("content")
                
            # 2. twitter:image
            tw_img = soup.find("meta", name="twitter:image")
            if tw_img and tw_img.get("content"):
                return tw_img.get("content")
                
            # 3. link[rel="image_src"]
            img_src = soup.find("link", rel="image_src")
            if img_src and img_src.get("href"):
                return img_src.get("href")
    except Exception as e:
        print(f"[PUBLISHER] WARNING: Could not fetch image URL from original source: {e}")
    return ""


def extract_bullets_from_content(content: str):
    """
    Parses section content and extracts lines that represent bullet points.
    Returns (cleaned_content, bullet_list).
    """
    if not content:
        return "", []
    
    lines = content.split("\n")
    bullet_list = []
    cleaned_lines = []
    
    for line in lines:
        stripped = line.strip()
        # Match standard markdown bullets (*, -, •, or digits followed by dot)
        match = re.match(r"^([\*\-\u2022]|(?:\d+\.))\s+(.*)$", stripped)
        if match:
            bullet_list.append(match.group(2).strip())
        else:
            cleaned_lines.append(line)
            
    cleaned_content = "\n".join(cleaned_lines).strip()
    return cleaned_content, bullet_list


async def publish_to_zapway(article: dict) -> dict:
    """
    Logs into zapway.app and submits the article via the insert_news form.
    Clicks the '+ Section' button to insert multiple sections.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )
        context = await browser.new_context(
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/125.0.0.0 Safari/537.36'
            ),
            viewport={'width': 1280, 'height': 900},
            locale='en-US',
        )
        page = await context.new_page()

        try:
            print(f"[PUBLISHER] Opening {ZAPWAY_INSERT_URL}...")
            await page.goto(ZAPWAY_INSERT_URL, wait_until="load", timeout=30000)
            await asyncio.sleep(1)

            # -- Step 1: Login -----------------------------------------------
            email_el = page.locator("#email")
            if await email_el.count() > 0 and await email_el.is_visible():
                await _login(page)
                if "insert_news" not in page.url:
                    await page.goto(ZAPWAY_INSERT_URL, wait_until="load", timeout=30000)
                    await asyncio.sleep(1)

            # -- Step 2: Prepare article data ---------------------------------
            title = article.get("title", "").strip()

            sections_raw = article.get("sections", [])
            if isinstance(sections_raw, str):
                try:
                    sections_raw = json.loads(sections_raw)
                except Exception:
                    sections_raw = []
            sections_list = sections_raw if isinstance(sections_raw, list) else []

            # Filter out AI Summary and Key Points/Highlights sections per user rule
            filtered_sections = []
            for s in sections_list:
                if isinstance(s, dict):
                    heading = s.get("heading", "").lower()
                    if any(kw in heading for kw in ["summary", "key points", "key highlights"]):
                        continue
                    filtered_sections.append(s)
            sections_list = filtered_sections

            # Fallback to single section if empty
            if not sections_list:
                sections_list = [{
                    "heading": title,
                    "content": article.get("original_content", "")
                }]

            meta_title = article.get("meta_title", title)
            meta_desc = article.get("meta_description", article.get("meta_desc", ""))
            source_name = article.get("source", "Zapway Newsroom")

            # Excerpt/summary
            excerpt = meta_desc
            if not excerpt:
                body_text = sections_list[0].get("content", "")
                m = re.match(r"^[^.!?]+[.!?]", body_text)
                excerpt = m.group(0) if m else body_text[:200]
            excerpt = excerpt.strip()

            # Read time estimate
            word_count = sum(len(s.get("content", "").split()) for s in sections_list if isinstance(s, dict))
            read_time = f"{max(1, round(word_count / 200))} min read"

            # -- Step 3: Fill form fields ------------------------------------
            print("[PUBLISHER] Filling form fields...")

            # A. Select category in dropdown
            try:
                sel = page.locator("select").first
                if await sel.count() > 0:
                    # Select Technology for EV news by default, or match Politics/Economy
                    text_content = (title + " " + excerpt).lower()
                    if "policy" in text_content or "government" in text_content:
                        await sel.select_option(value="Politics")
                    elif "economy" in text_content or "budget" in text_content:
                        await sel.select_option(value="Economy")
                    elif "climate" in text_content or "environment" in text_content:
                        await sel.select_option(value="Climate")
                    else:
                        await sel.select_option(value="Technology")
                    print("[PUBLISHER] Selected category in dropdown")
            except Exception as e:
                print(f"[PUBLISHER] WARNING: Could not select category: {e}")

            # B. Fill core metadata fields
            async def fill_partial(fragment, value, label):
                if not value:
                    return
                sel = f'input[placeholder*="{fragment}"], textarea[placeholder*="{fragment}"]'
                try:
                    el = page.locator(sel).first
                    if await el.count() > 0:
                        await el.scroll_into_view_if_needed()
                        await el.fill(value)
                        print(f"[PUBLISHER] Filled {label!r}")
                except Exception as e:
                    print(f"[PUBLISHER] ERROR filling {label!r}: {e}")

            async def fill_exact(placeholder, value, label):
                if not value:
                    return
                sel = f'input[placeholder="{placeholder}"], textarea[placeholder="{placeholder}"]'
                try:
                    el = page.locator(sel).first
                    if await el.count() > 0:
                        await el.scroll_into_view_if_needed()
                        await el.fill(value)
                        print(f"[PUBLISHER] Filled {label!r}")
                except Exception as e:
                    print(f"[PUBLISHER] ERROR filling {label!r}: {e}")

            await fill_partial("Reuters", source_name, "source_name")
            await fill_exact("DBC Evening News", "Zapway EV News", "source_channel")
            await fill_partial("Enter the news headline", title, "title")
            await fill_partial("Brief 1", excerpt, "excerpt")
            await fill_partial("Google search results", meta_title, "meta_title")
            await fill_partial("under the title in Google", meta_desc, "meta_description")
            await fill_exact("Jane Doe", "Zapway Team", "author_name")
            await fill_exact("JD", "ZT", "author_initials")
            await fill_partial("Senior correspondent", "EV News Correspondent", "author_bio")
            await fill_exact("4 min read", read_time, "read_time")

            # Fill Main Image URL (crawled dynamically from the original source)
            try:
                main_image_url = fetch_main_image_url(article.get("url", ""))
                if main_image_url:
                    img_el = page.locator('input[placeholder="images/hero.jpg"]').first
                    if await img_el.count() > 0:
                        await img_el.scroll_into_view_if_needed()
                        await img_el.fill(main_image_url)
                        print(f"[PUBLISHER] Filled Main Image URL: {main_image_url}")
            except Exception as img_err:
                print(f"[PUBLISHER] WARNING: Could not fill main image URL: {img_err}")


            # C. Toggle checkmarks (First toggle = Add to Top Stories, set to True)
            try:
                cbs = page.locator('input[type="checkbox"]')
                if await cbs.count() > 0:
                    cb = cbs.first
                    if not await cb.is_checked():
                        # Click the parent label/div wrapper to change React state correctly
                        wrapper = page.locator('span:has-text("ADD TO TOP STORIES")').first
                        if await wrapper.count() > 0:
                            await wrapper.click()
                        else:
                            await cb.click()
                        print("[PUBLISHER] Enabled 'ADD TO TOP STORIES' checkbox")
            except Exception as e:
                print(f"[PUBLISHER] WARNING: Could not toggle checkboxes: {e}")

            # D. Fill multiple sections using '+ Section' button
            print(f"[PUBLISHER] Filling {len(sections_list)} sections...")
            for idx, sec in enumerate(sections_list):
                if not isinstance(sec, dict):
                    continue

                sec_heading = sec.get("heading", "")
                sec_content = sec.get("content", "")

                # If not the first section, click '+ Section' to add fields
                if idx > 0:
                    add_btn = page.get_by_text("+ Section")
                    if await add_btn.count() > 0:
                        await add_btn.first.scroll_into_view_if_needed()
                        await add_btn.first.click()
                        await asyncio.sleep(0.3)
                        print(f"[PUBLISHER] Clicked '+ Section' button for section #{idx}")
                    else:
                        print(f"[PUBLISHER] WARNING: '+ Section' button not found for section #{idx}")
                        break

                # Fill heading
                try:
                    heading_el = page.locator('input[placeholder*="Overview, Key Findings"]').nth(idx)
                    await heading_el.scroll_into_view_if_needed()
                    await heading_el.fill(sec_heading)
                except Exception as e:
                    print(f"[PUBLISHER] ERROR filling section #{idx} heading: {e}")

                # Extract bullets from content
                cleaned_body, bullets = extract_bullets_from_content(sec_content)

                # Fill body content
                try:
                    body_el = page.locator('textarea[placeholder*="Section body text"]').nth(idx)
                    await body_el.scroll_into_view_if_needed()
                    await body_el.fill(cleaned_body if cleaned_body.strip() else "Detailed updates provided in the source.")
                except Exception as e:
                    print(f"[PUBLISHER] ERROR filling section #{idx} body: {e}")

                # Fill bullet points if they exist
                if bullets:
                    print(f"[PUBLISHER] Section #{idx} has {len(bullets)} bullets to fill...")
                    for b_idx, bullet_text in enumerate(bullets):
                        try:
                            # Locate the + Bullet button inside the current section container
                            add_bullet_btn = page.locator('.na-sec').nth(idx).locator('.na-bullets-head .na-add-btn')
                            if await add_bullet_btn.count() > 0:
                                await add_bullet_btn.scroll_into_view_if_needed()
                                await add_bullet_btn.click()
                                await asyncio.sleep(0.3)  # Wait for bullet field to render in UI
                            else:
                                print(f"[PUBLISHER] WARNING: + Bullet button not found in section #{idx}")
                                break

                            # Locate the newly added input field under .na-bullet-row
                            bullet_inputs = page.locator('.na-sec').nth(idx).locator('.na-bullet-row input')
                            if await bullet_inputs.count() > b_idx:
                                input_field = bullet_inputs.nth(b_idx)
                                await input_field.scroll_into_view_if_needed()
                                await input_field.fill(bullet_text)
                                print(f"[PUBLISHER] Filled bullet #{b_idx+1} in section #{idx}")
                        except Exception as bullet_err:
                            print(f"[PUBLISHER] ERROR filling bullet #{b_idx} in section #{idx}: {bullet_err}")


            # -- Step 4: Click the "Publish Story" submit button -------------
            print("[PUBLISHER] Submitting form...")
            submitted = False
            try:
                btn = page.get_by_text("Publish Story", exact=False)
                if await btn.count() > 0:
                    await btn.first.scroll_into_view_if_needed()
                    await asyncio.sleep(0.3)
                    await btn.first.click()
                    submitted = True
                    print("[PUBLISHER] Clicked 'Publish Story' button")
            except Exception as e:
                print(f"[PUBLISHER] Submit error: {e}")

            if not submitted:
                return {
                    "success": False,
                    "error": "Publish Story button not found",
                    "url": page.url,
                }

            await asyncio.sleep(5)  # Wait for submission/network to complete
            final_url = page.url
            print(f"[PUBLISHER] Done. Final URL: {final_url}")

            # Check for error toast
            try:
                err_toast = page.locator('text=Network error')
                if await err_toast.count() > 0:
                    print("[PUBLISHER] ERROR: Network error toast detected")
                    return {"success": False, "error": "Network error from API", "final_url": final_url}
            except Exception:
                pass

            # Save debug screenshot
            screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "publisher_debug.png")
            await page.screenshot(path=screenshot_path, full_page=False)

            return {"success": True, "final_url": final_url}

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
        finally:
            await browser.close()


if __name__ == "__main__":
    test = {
        "title": "India EV Market Grows 40 Percent in H1 2026",
        "sections": [
            {"heading": "Introduction", "content": "India's EV market saw strong growth in H1 2026, led by Tata Motors."},
            {"heading": "Key Highlights", "content": "Charging stations increased by 50% across major expressways."}
        ],
        "meta_description": "India EV market grew 40 percent in H1 2026, driven by Tata and Ola.",
        "meta_title": "India EV Market Grows 40% | Zapway",
        "source": "EVUpdateMedia",
    }
    result = asyncio.run(publish_to_zapway(test))
    print("\n[RESULT]", json.dumps(result, indent=2))
