"""
save_session.py
---------------
Run this ONCE to save your login session.
After this, sanity.py will never ask you to log in again.

Usage:
    python save_session.py
"""

import pickle, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

URL         = "https://atlasui-eastus2-prod.az.3pc.att.com"
COOKIE_FILE = "session.pkl"

options = Options()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(options=options)
driver.get(URL)

print("\n" + "="*50)
print("  Browser is open. Please log in manually.")
print("  Once you see the HOME PAGE, come back here.")
print("="*50)
input("\n  Press ENTER after you are fully logged in...")

pickle.dump(driver.get_cookies(), open(COOKIE_FILE, "wb"))
print(f"\n  Session saved to {COOKIE_FILE}")
print("  You can now run: python sanity.py\n")

driver.quit()
