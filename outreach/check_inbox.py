"""
Check LinkedIn conversations and new incoming connection acceptances.
"""

import json
from patchright.sync_api import sync_playwright

USER_DATA_DIR = "/home/rythamo/.linkedin-mcp/profile"
CHROME_PATH = "/home/rythamo/.linkedin-mcp/patchright-browsers/chromium-1234/chrome-linux64/chrome"

def check_messages():
    print("Checking LinkedIn messaging inbox...")
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=True,
            executable_path=CHROME_PATH,
            viewport={"width": 1280, "height": 800}
        )
        page = browser.pages[0] if browser.pages else browser.new_page()
        try:
            page.goto("https://www.linkedin.com/messaging/", wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)

            threads = []
            items = page.locator(".msg-conversation-listitem, [role='listitem']").all()
            for item in items[:10]:
                txt = item.inner_text().strip().replace("\n", " | ")
                threads.append(txt)

            print(f"Found {len(threads)} conversation threads.")
            for i, t in enumerate(threads[:5], 1):
                print(f"[{i}] {t[:100]}")

            return threads
        except Exception as e:
            print(f"Error checking inbox: {e}")
            return []
        finally:
            browser.close()

if __name__ == "__main__":
    check_messages()
