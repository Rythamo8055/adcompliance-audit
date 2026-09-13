"""
Send a direct LinkedIn message to a 1st-degree connection.
"""

import sys
import json
from patchright.sync_api import sync_playwright

USER_DATA_DIR = "/home/rythamo/.linkedin-mcp/profile"
CHROME_PATH = "/home/rythamo/.linkedin-mcp/patchright-browsers/chromium-1234/chrome-linux64/chrome"

def send_dm(username: str, message_text: str) -> dict:
    url = f"https://www.linkedin.com/in/{username}/"
    result = {
        "username": username,
        "url": url,
        "status": "unknown",
        "sent": False,
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
            print(f"Opening profile: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)

            # Check if 1st degree
            main_text = page.locator("main").inner_text()
            if "1st" not in main_text and "Message" not in main_text:
                result["status"] = "not_connected"
                result["message"] = "Profile is not a 1st-degree connection or Message button missing."
                browser.close()
                return result

            # Click Message button
            msg_btn = page.locator('main button:has-text("Message"), main a:has-text("Message")').first
            if not msg_btn or not msg_btn.is_visible():
                result["status"] = "error"
                result["message"] = "Message button not visible on profile."
                browser.close()
                return result

            print("Clicking Message button on profile...")
            msg_btn.click()
            page.wait_for_timeout(3000)

            # Locate the message composition textbox
            # Typically div[role="textbox"][contenteditable="true"] or .msg-form__contenteditable
            textbox = page.locator('.msg-form__contenteditable, div[role="textbox"][contenteditable="true"]').last
            if not textbox or not textbox.is_visible():
                # Check if entire messaging page opened
                textbox = page.locator('div[role="textbox"][contenteditable="true"]').first

            if not textbox or not textbox.is_visible():
                result["status"] = "error"
                result["message"] = "Could not find message compose textbox."
                browser.close()
                return result

            print("Focusing textbox and typing message via keyboard...")
            textbox.click()
            page.wait_for_timeout(500)
            page.keyboard.insert_text(message_text)
            page.wait_for_timeout(1000)

            # Find Send button
            # Usually .msg-form__send-button or button:has-text("Send")
            send_btn = page.locator('.msg-form__send-button, form.msg-form button[type="submit"], button:has-text("Send")').last
            if not send_btn or not send_btn.is_visible():
                result["status"] = "error"
                result["message"] = "Could not find Send button in chat overlay."
                browser.close()
                return result

            print("Clicking Send button...")
            send_btn.click()
            page.wait_for_timeout(3000)

            result["status"] = "delivered"
            result["sent"] = True
            result["message"] = "Direct message successfully sent."

        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)
            print("Exception during send_dm:", e)
        finally:
            browser.close()

    return result

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python send_direct_message.py <username> <message>")
        sys.exit(1)
    uname = sys.argv[1]
    msg = sys.argv[2]
    res = send_dm(uname, msg)
    print(json.dumps(res, indent=2))
