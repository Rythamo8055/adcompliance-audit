"""
Outreach automation helper for LinkedIn.
Uses the authenticated patchright profile from Agent-Reach / mcp-server-linkedin.
"""

import sys
import time
import json
from pathlib import Path
from patchright.sync_api import sync_playwright

USER_DATA_DIR = "/home/rythamo/.linkedin-mcp/profile"
CHROME_PATH = "/home/rythamo/.linkedin-mcp/patchright-browsers/chromium-1234/chrome-linux64/chrome"

def send_invitation(profile_username: str, note_text: str = None) -> dict:
    url = f"https://www.linkedin.com/in/{profile_username}/"
    result = {
        "username": profile_username,
        "url": url,
        "status": "unknown",
        "note_sent": False,
        "message": ""
    }

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=True,
            executable_path=CHROME_PATH,
            viewport={"width": 1280, "height": 800}
        )
        page = browser.pages[0] if browser.pages else browser.new_page()

        try:
            print(f"Navigating to {url}...")
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)

            # Check page title
            title = page.title()
            print(f"Page loaded: {title}")

            # Look for Connect button or More menu in main section
            # Check if already connected or pending
            main_text = page.locator("main").inner_text()
            if "Pending" in main_text:
                result["status"] = "already_pending"
                result["message"] = "Connection request is already pending."
                browser.close()
                return result

            # Check for direct Connect button
            connect_btn = None
            buttons = page.locator("main button").all()
            for b in buttons:
                txt = b.inner_text().strip().lower()
                aria = (b.get_attribute("aria-label") or "").lower()
                if "connect" in txt or "invite" in aria and "connect" in aria:
                    connect_btn = b
                    break

            # If not found directly, check More button
            if not connect_btn:
                print("Connect button not found in top card. Checking 'More' menu...")
                more_btn = None
                for b in buttons:
                    txt = b.inner_text().strip().lower()
                    aria = (b.get_attribute("aria-label") or "").lower()
                    if txt == "more" or "more actions" in aria or b.get_attribute("aria-expanded") is not None:
                        more_btn = b
                        break

                if more_btn:
                    more_btn.click()
                    page.wait_for_timeout(1000)
                    # Look for Connect in dropdown/menu
                    menu_items = page.locator("[role='menu'] [role='menuitem'], [role='menu'] button, .artdeco-dropdown__content button").all()
                    for item in menu_items:
                        txt = item.inner_text().strip().lower()
                        aria = (item.get_attribute("aria-label") or "").lower()
                        if "connect" in txt or "connect" in aria:
                            connect_btn = item
                            break

            if not connect_btn:
                result["status"] = "connect_unavailable"
                result["message"] = "No Connect option found on profile (may be follow-only or restricted)."
                browser.close()
                return result

            print("Clicking Connect button...")
            connect_btn.click()
            page.wait_for_timeout(2000)

            # Check if modal opened
            dialog = page.locator("div[role='dialog'], dialog[open]")
            if dialog.count() == 0:
                # Some profiles connect immediately without a modal!
                result["status"] = "connected_directly"
                result["message"] = "Connected directly without modal."
                browser.close()
                return result

            dialog_el = dialog.first
            dialog_text = dialog_el.inner_text()
            print("Dialog opened. Text preview:", dialog_text[:120].replace('\n', ' '))

            # Check if note is requested and if "Add a note" button exists
            if note_text:
                add_note_btn = None
                dialog_btns = dialog_el.locator("button").all()
                for b in dialog_btns:
                    txt = b.inner_text().strip().lower()
                    aria = (b.get_attribute("aria-label") or "").lower()
                    if "add a note" in txt or "add a note" in aria:
                        add_note_btn = b
                        break

                if add_note_btn:
                    print("Clicking 'Add a note'...")
                    add_note_btn.click()
                    page.wait_for_timeout(1000)

                # Find textarea
                textarea = dialog_el.locator("textarea")
                if textarea.count() > 0 and textarea.first.is_visible():
                    print("Filling note textarea...")
                    # Truncate to 195 chars to avoid limit
                    safe_note = note_text[:195]
                    textarea.first.fill(safe_note)
                    page.wait_for_timeout(500)
                    result["note_sent"] = True

                # Click Send button
                send_btn = None
                dialog_btns = dialog_el.locator("button").all()
                for b in dialog_btns:
                    txt = b.inner_text().strip().lower()
                    aria = (b.get_attribute("aria-label") or "").lower()
                    if txt == "send" or "send invitation" in aria or "send now" in txt:
                        send_btn = b
                        break

                if send_btn:
                    print("Clicking Send invitation...")
                    send_btn.click()
                    page.wait_for_timeout(2500)
                    result["status"] = "sent"
                    result["message"] = "Connection invitation sent with personalized note."
                else:
                    result["status"] = "error"
                    result["message"] = "Send button not found in dialog."
            else:
                # No note, click "Send without a note" or "Send"
                send_btn = None
                dialog_btns = dialog_el.locator("button").all()
                for b in dialog_btns:
                    txt = b.inner_text().strip().lower()
                    if "send without" in txt or txt == "send":
                        send_btn = b
                        break
                if send_btn:
                    send_btn.click()
                    page.wait_for_timeout(2500)
                    result["status"] = "sent"
                    result["message"] = "Connection invitation sent without note."
                else:
                    result["status"] = "error"
                    result["message"] = "Could not find send button."

        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)
            print(f"Exception: {e}")
        finally:
            browser.close()

    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python send_invitation.py <username> [note]")
        sys.exit(1)
    username = sys.argv[1]
    note = sys.argv[2] if len(sys.argv) > 2 else None
    res = send_invitation(username, note)
    print(json.dumps(res, indent=2))
