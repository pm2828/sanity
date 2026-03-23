"""
STEP 1 - Run this FIRST (only once or when session expires)
Opens browser so you can log in manually.
Saves cookies to session.json automatically.

Run:
    python capture_session.py
"""

import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

LOGIN_URL = "https://atlasui-eastus2-prod.az.3pc.att.com/"
SESSION_FILE = "session.json"
CHROME_DRIVER_PATH = r"C:\chromedriver\chromedriver.exe"  # Update this path


def capture_session():
    print("\n" + "="*50)
    print("  ATT SESSION CAPTURE")
    print("="*50)

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Use chromedriver
    service = Service(CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)

    print(f"\nOpening: {LOGIN_URL}")
    driver.get(LOGIN_URL)

    print("\n--- ACTION REQUIRED ---")
    print("1. Log in with your username and password")
    print("2. Complete 2FA if required")
    print("3. Wait until you reach the dashboard")
    print("4. Come back here and press Enter")
    input("\nPress Enter AFTER you are fully logged in...")

    # Save all cookies
    cookies = driver.get_cookies()
    session_data = {
        "cookies": cookies,
        "url": driver.current_url,
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    with open(SESSION_FILE, "w") as f:
        json.dump(session_data, f, indent=2)

    print(f"\n✅ Session saved! ({len(cookies)} cookies captured)")
    print(f"   File: {SESSION_FILE}")
    driver.quit()


if __name__ == "__main__":
    capture_session()
