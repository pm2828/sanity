"""
save_session.py
---------------
Run this ONCE to save your login session.
Uses Playwright ASYNC API — no greenlet needed.

Usage:
    python save_session.py
"""

import asyncio, json
from playwright.async_api import async_playwright

URL          = "https://atlasui-eastus2-prod.az.3pc.att.com"
SESSION_FILE = "session.json"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page    = await context.new_page()

        await page.goto(URL)

        print("\n" + "="*50)
        print("  Browser is open. Please log in manually.")
        print("  Once you see the HOME PAGE, come back here.")
        print("="*50)
        input("\n  Press ENTER after you are fully logged in...")

        # Save cookies + localStorage to JSON
        storage = await context.storage_state(path=SESSION_FILE)
        print(f"\n  ✅ Session saved to {SESSION_FILE}")
        print("  You can now run: python sanity.py\n")

        await browser.close()

asyncio.run(main())
