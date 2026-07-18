"""
Playwright-based publisher for Zapway Blogs.
Logs into zapway.app and fills the insert_blog form under Blogs, handles multiple sections
by switching to the 'Detail Page' tab and clicking '+ Add Section', and submits.
"""
import sys
import asyncio
import json
import re
import os
from playwright.async_api import async_playwright

ZAPWAY_EMAIL = "prerak.sg@gmail.com"
ZAPWAY_PASSWORD = "132325"
ZAPWAY_BLOGS_INSERT_URL = "https://zapway.app/Blogs/insert"


async def _login(page):
    """Log in using confirmed field IDs: #email and #password."""
    print("[BLOG PUBLISHER] Filling login credentials...")
    await page.wait_for_selector("#email", timeout=10000)
    await page.fill("#email", ZAPWAY_EMAIL)
    await page.fill("#password", ZAPWAY_PASSWORD)

    for sel in ['button[type="submit"]', 'button:has-text("Login")',
                'button:has-text("Sign in")', 'button:has-text("Log in")']:
        try:
            btn = page.locator(sel).first
            if await btn.count() > 0 and await btn.is_visible():
                await btn.click()
                print(f"[BLOG PUBLISHER] Login submitted via: {sel}")
                break
        except Exception:
            continue

    try:
        await page.wait_for_load_state("load", timeout=20000)
    except Exception:
        pass
    await asyncio.sleep(1)
    print(f"[BLOG PUBLISHER] Post-login URL: {page.url}")


async def publish_blog_to_zapway(blog_data: dict) -> dict:
    """
    Logs into zapway.app and submits the blog post via the /Blogs/insert form.
    Fills Basic Info, switches to Detail Page tab, and adds multiple sections.
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
            print(f"[BLOG PUBLISHER] Opening {ZAPWAY_BLOGS_INSERT_URL}...")
            await page.goto(ZAPWAY_BLOGS_INSERT_URL, wait_until="load", timeout=60000)
            await asyncio.sleep(1)

            # -- Step 1: Login if required ------------------------------------
            email_el = page.locator("#email")
            if await email_el.count() > 0 and await email_el.is_visible():
                await _login(page)
                if "Blogs/insert" not in page.url:
                    await page.goto(ZAPWAY_BLOGS_INSERT_URL, wait_until="load", timeout=60000)
                    await asyncio.sleep(1)

            # -- Step 2: Extract blog structure ------------------------------
            title = blog_data.get("title", "").strip()
            meta_title = blog_data.get("meta_title", title)
            meta_desc = blog_data.get("meta_description", "")
            cover_image_url = blog_data.get("cover_image_url", "")
            
            sections_list = blog_data.get("sections", [])
            if isinstance(sections_list, str):
                try:
                    sections_list = json.loads(sections_list)
                except Exception:
                    sections_list = []
            
            # Simple excerpt from the first section
            excerpt = meta_desc
            if not excerpt and sections_list:
                body_text = sections_list[0].get("body", "")
                m = re.match(r"^[^.!?]+[.!?]", body_text)
                excerpt = m.group(0) if m else body_text[:200]
            excerpt = excerpt.strip()

            # Word count and read time
            word_count = len(title.split()) + len(excerpt.split())
            for s in sections_list:
                word_count += len(s.get("heading", "").split())
                word_count += len(s.get("body", "").split())
            read_time = f"{max(1, round(word_count / 200))} min read"

            # Select category chip (Technology by default, or auto-detect from content/title)
            category = blog_data.get("category", "")
            if not category:
                text_content = (title + " " + excerpt).lower()
                if "charging" in text_content or "station" in text_content or "charger" in text_content:
                    category = "EV Charging"
                elif "policy" in text_content or "subsidy" in text_content or "government" in text_content:
                    category = "News"
                elif "academy" in text_content or "guide" in text_content or "how to" in text_content or "science" in text_content:
                    category = "Academy"
                elif "product" in text_content or "update" in text_content or "features" in text_content or "spec" in text_content:
                    category = "Product Updates"
                else:
                    category = "Technology"
                    
            try:
                # Find the bi-chip button matching the category
                chip_btn = page.locator(f'button.bi-chip:has-text("{category}")').first
                if await chip_btn.count() > 0:
                    await chip_btn.click()
                    print(f"[BLOG PUBLISHER] Selected category chip: {category}")
                else:
                    # Fallback to filling the category input directly
                    cat_input = page.locator('input[name="category"]').first
                    if await cat_input.count() > 0:
                        await cat_input.fill(category)
                        print(f"[BLOG PUBLISHER] Filled category input: {category}")
            except Exception as e:
                print(f"[BLOG PUBLISHER] WARNING: Could not select category chip: {e}")

            await page.fill('input[name="meta_title"]', meta_title)
            await page.fill('textarea[name="meta_description"]', meta_desc)
            await page.fill('input[name="title"]', title)
            await page.fill('textarea[name="excerpt"]', excerpt)
            await page.fill('input[name="author"]', "Zapway Team")
            await page.fill('input[name="initials"]', "ZT")
            await page.fill('input[name="read_time"]', read_time)
            
            if cover_image_url:
                if cover_image_url.startswith("/static/"):
                    local_path = cover_image_url.lstrip("/")
                    abs_path = os.path.abspath(local_path)
                    if os.path.exists(abs_path):
                        try:
                            # Locate the file input on the active tab (Basic Info)
                            file_input = page.locator('input[type="file"]').first
                            await file_input.set_input_files(abs_path)
                            print(f"[BLOG PUBLISHER] Uploaded cover image file: {abs_path}")
                            # Wait for upload to complete
                            await asyncio.sleep(4)
                        except Exception as upload_err:
                            print(f"[BLOG PUBLISHER] ERROR uploading cover image file: {upload_err}")
                            await page.fill('input[name="image_url"]', cover_image_url)
                    else:
                        print(f"[BLOG PUBLISHER] Local image path not found: {abs_path}")
                        await page.fill('input[name="image_url"]', cover_image_url)
                else:
                    await page.fill('input[name="image_url"]', cover_image_url)

            # -- Step 4: Switch to Detail Page Tab ---------------------------
            tab_btn = page.locator('button.bi-tab:has-text("Detail Page")').first
            await tab_btn.click()
            await asyncio.sleep(1)
            print("[BLOG PUBLISHER] Switched to Detail Page tab")

            # -- Step 5: Fill Sections ---------------------------------------
            for idx, sec in enumerate(sections_list):
                if idx > 0:
                    add_sec_btn = page.locator('button:has-text("+ Add Section")').first
                    if await add_sec_btn.count() > 0:
                        await add_sec_btn.click()
                        await asyncio.sleep(0.3)
                        print(f"[BLOG PUBLISHER] Added Section field #{idx}")
                    else:
                        print(f"[BLOG PUBLISHER] WARNING: + Add Section button not found at index {idx}")
                        break

                sec_heading = sec.get("heading", "")
                sec_body = sec.get("body", "")
                sec_image = sec.get("image_url", "")

                # Append source attribution to the last section's body
                if idx == len(sections_list) - 1:
                    source_name = blog_data.get("source", "Zapway Team")
                    sec_body = f"{sec_body}\n\nsource : {source_name}"

                # Heading input
                heading_el = page.locator('input[placeholder*="e.g. Introduction"]').nth(idx)
                await heading_el.fill(sec_heading)

                # Body textarea
                body_el = page.locator('textarea[placeholder*="Write the section body here"]').nth(idx)
                await body_el.fill(sec_body)

                # Optional section image
                if sec_image:
                    if sec_image.startswith("/static/"):
                        local_path = sec_image.lstrip("/")
                        abs_path = os.path.abspath(local_path)
                        if os.path.exists(abs_path):
                            try:
                                # Locate the file input inside the bi-section-block at the current index
                                file_input = page.locator('.bi-section-block').nth(idx).locator('input[type="file"]').first
                                if await file_input.count() > 0:
                                    await file_input.set_input_files(abs_path)
                                    print(f"[BLOG PUBLISHER] Uploaded section #{idx} image file: {abs_path}")
                                    await asyncio.sleep(3)
                                else:
                                    img_el = page.locator('input[placeholder*="section visual or diagram"]').nth(idx)
                                    await img_el.fill(sec_image)
                            except Exception as upload_err:
                                print(f"[BLOG PUBLISHER] ERROR uploading section #{idx} image file: {upload_err}")
                                try:
                                    img_el = page.locator('input[placeholder*="section visual or diagram"]').nth(idx)
                                    await img_el.fill(sec_image)
                                except Exception:
                                    pass
                        else:
                            print(f"[BLOG PUBLISHER] Local section image not found: {abs_path}")
                            try:
                                img_el = page.locator('input[placeholder*="section visual or diagram"]').nth(idx)
                                await img_el.fill(sec_image)
                            except Exception:
                                pass
                    else:
                        try:
                            img_el = page.locator('input[placeholder*="section visual or diagram"]').nth(idx)
                            await img_el.fill(sec_image)
                        except Exception:
                            pass

            # -- Step 6: Submit -----------------------------------------------
            print("[BLOG PUBLISHER] Submitting blog...")
            submit_btn = page.locator('button:has-text("Publish Post")').first
            if await submit_btn.count() > 0:
                await submit_btn.click()
                await asyncio.sleep(5)
                print(f"[BLOG PUBLISHER] Submission done. Landed URL: {page.url}")
                
                # Check screenshot for validation
                screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blog_publisher_debug.png")
                await page.screenshot(path=screenshot_path)
                return {"success": True, "final_url": page.url}
            else:
                return {"success": False, "error": "Publish Post button not found"}

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
        finally:
            await browser.close()
