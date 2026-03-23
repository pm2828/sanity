"""
STEP 2 - Run this DAILY
Uses saved session.json to skip login.
Tests all ATT Atlas UI pages and generates HTML report.

Run:
    python att_sanity.py
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ─── CONFIG ───────────────────────────────────────────────
CHROME_DRIVER_PATH = r"C:\chromedriver\chromedriver.exe"  # Update this path
SESSION_FILE = "session.json"
BASE_URL = "https://atlasui-eastus2-prod.az.3pc.att.com"
APP_NAME = "ATT Atlas UI"

PAGES = [
    {
        "name": "Home",
        "url": "/",
        "checks": [
            {"type": "visible", "selector": "body"}
        ]
    },
    {
        "name": "Job",
        "url": "/job",
        "checks": [
            {"type": "visible", "selector": "body"}
        ]
    },
    {
        "name": "Customer",
        "url": "/customer",
        "checks": [
            {"type": "visible", "selector": "body"}
        ]
    },
    {
        "name": "Customer History",
        "url": "/customer-history",
        "checks": [
            {"type": "visible", "selector": "body"}
        ]
    },
    {
        "name": "Facilities",
        "url": "/facilities",
        "checks": [
            {"type": "visible", "selector": "body"}
        ]
    },
    {
        "name": "Tests Dynamic",
        "url": "/tests-dynamic",
        "checks": [
            {"type": "visible", "selector": "body"}
        ]
    },
    {
        "name": "CPE Test",
        "url": "/cpe-test",
        "checks": [
            {"type": "visible", "selector": "body"}
        ]
    },
    {
        "name": "Trouble Shoot",
        "url": "/trouble-shoot",
        "checks": [
            {"type": "visible", "selector": "body"}
        ]
    },
    {
        "name": "Sync No Service",
        "url": "/sync-no-service",
        "checks": [
            {"type": "visible", "selector": "body"}
        ]
    },
    {
        "name": "Troubleshoot VOIP",
        "url": "/troubleshoot-voip",
        "checks": [
            {"type": "visible", "selector": "body"}
        ]
    },
    {
        "name": "System Health",
        "url": "/system-health",
        "checks": [
            {"type": "visible", "selector": "body"}
        ]
    }
]
# ──────────────────────────────────────────────────────────

REPORTS_DIR = Path("reports")
SCREENSHOTS_DIR = Path("screenshots")
REPORTS_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def create_driver():
    """Create Chrome driver in headless mode."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    service = Service(CHROME_DRIVER_PATH)
    return webdriver.Chrome(service=service, options=options)


def load_session(driver):
    """Load saved cookies into browser."""
    if not os.path.exists(SESSION_FILE):
        print("❌ session.json not found!")
        print("   Run capture_session.py first!")
        return False

    with open(SESSION_FILE) as f:
        session_data = json.load(f)

    # Must visit domain first before adding cookies
    driver.get(BASE_URL)
    time.sleep(2)

    for cookie in session_data["cookies"]:
        # Remove unsupported keys
        cookie.pop("sameSite", None)
        cookie.pop("expiry", None)
        try:
            driver.add_cookie(cookie)
        except Exception:
            pass

    print(f"✅ Session loaded ({len(session_data['cookies'])} cookies)")
    print(f"   Saved at: {session_data.get('saved_at', 'unknown')}")
    return True


def check_page(driver, page):
    """Test a single page."""
    name = page["name"]
    url = BASE_URL + page["url"]
    result = {
        "name": name,
        "url": url,
        "status": "PASS",
        "load_time_ms": 0,
        "checks": [],
        "error": None,
        "session_expired": False,
        "screenshot": None
    }

    try:
        start = time.time()
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        result["load_time_ms"] = round((time.time() - start) * 1000)

        # Check if redirected to login
        current_url = driver.current_url.lower()
        if any(x in current_url for x in ["login", "signin", "auth", "sso"]):
            result["session_expired"] = True
            result["status"] = "FAIL"
            result["error"] = f"Redirected to login page! URL: {driver.current_url}"
            print(f"  🔒 [{name}] SESSION EXPIRED")
            return result

        # Run UI checks
        for check in page.get("checks", []):
            check_result = {
                "selector": check["selector"],
                "status": "PASS",
                "detail": ""
            }
            try:
                if check["type"] == "visible":
                    el = WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, check["selector"]))
                    )
                    check_result["detail"] = "Visible ✓"

                elif check["type"] == "text":
                    el = driver.find_element(By.CSS_SELECTOR, check["selector"])
                    actual = el.text.strip()
                    if check["expect"].lower() in actual.lower():
                        check_result["detail"] = f"Text OK: '{actual[:40]}'"
                    else:
                        check_result["status"] = "FAIL"
                        check_result["detail"] = f"Expected '{check['expect']}' got '{actual[:40]}'"
                        result["status"] = "FAIL"

                elif check["type"] == "not_visible":
                    elements = driver.find_elements(By.CSS_SELECTOR, check["selector"])
                    if elements:
                        check_result["status"] = "FAIL"
                        check_result["detail"] = "Element should not exist but found"
                        result["status"] = "FAIL"
                    else:
                        check_result["detail"] = "Correctly absent ✓"

            except Exception as e:
                check_result["status"] = "WARN"
                check_result["detail"] = f"Not found: {check['selector']}"

            result["checks"].append(check_result)

        # Take screenshot
        safe_name = name.lower().replace(" ", "_")
        screenshot_path = SCREENSHOTS_DIR / f"{safe_name}.png"
        driver.save_screenshot(str(screenshot_path))
        result["screenshot"] = str(screenshot_path)

        status_icon = "✅" if result["status"] == "PASS" else "❌"
        print(f"  {status_icon} [{name}] {result['status']} ({result['load_time_ms']}ms)")

    except Exception as e:
        result["status"] = "FAIL"
        result["error"] = str(e)
        print(f"  ❌ [{name}] ERROR: {str(e)[:80]}")

    return result


def generate_report(results, run_date, elapsed):
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    expired = sum(1 for r in results if r.get("session_expired"))
    overall = "PASS" if failed == 0 else "FAIL"
    overall_color = "#22c55e" if overall == "PASS" else "#ef4444"

    rows = ""
    for r in results:
        bg = "#f0fdf4" if r["status"] == "PASS" else "#fee2e2"
        status_color = "#16a34a" if r["status"] == "PASS" else "#dc2626"

        checks_html = ""
        for c in r.get("checks", []):
            icon = "✅" if c["status"] == "PASS" else "⚠️"
            checks_html += f'<div style="font-size:11px;padding:1px 0">{icon} <code>{c["selector"]}</code> — {c["detail"]}</div>'

        error_html = ""
        if r.get("error"):
            error_html = f'<div style="color:#dc2626;font-size:11px;margin-top:4px">⚠️ {r["error"]}</div>'
        if r.get("session_expired"):
            error_html += '<div style="color:#b45309;font-weight:600;font-size:11px">🔒 Session expired — re-run capture_session.py</div>'

        rows += f"""
        <tr style="background:{bg}">
          <td style="padding:10px 14px;font-weight:500">{r['name']}</td>
          <td style="padding:10px 14px"><span style="color:{status_color};font-weight:700">{r['status']}</span></td>
          <td style="padding:10px 14px;font-size:12px;color:#6b7280">{r['url']}</td>
          <td style="padding:10px 14px;font-size:12px">{r['load_time_ms']}ms</td>
          <td style="padding:10px 14px">{checks_html}{error_html}</td>
        </tr>"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"att_sanity_{timestamp}.html"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ATT Sanity Report — {run_date}</title>
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;padding:24px;background:#f8fafc;color:#1e293b}}
  .header{{background:#1e293b;color:white;border-radius:12px;padding:28px 32px;margin-bottom:24px}}
  .header h1{{margin:0 0 4px;font-size:22px}}
  .header p{{margin:0;opacity:0.6;font-size:14px}}
  .badge{{display:inline-block;padding:6px 20px;border-radius:999px;font-size:18px;font-weight:700;margin-top:12px;background:{overall_color};color:white}}
  .cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}}
  .card{{background:white;border-radius:10px;padding:20px 24px;box-shadow:0 1px 3px rgba(0,0,0,0.08)}}
  .card .num{{font-size:32px;font-weight:700}}
  .card .lbl{{font-size:13px;color:#94a3b8;margin-top:2px}}
  table{{width:100%;border-collapse:collapse;background:white;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08)}}
  th{{background:#f1f5f9;padding:12px 14px;text-align:left;font-size:13px;color:#64748b;font-weight:600;border-bottom:1px solid #e2e8f0}}
  td{{border-bottom:1px solid #f1f5f9;vertical-align:top}}
  code{{background:#f1f5f9;padding:2px 5px;border-radius:4px;font-size:11px}}
  .footer{{margin-top:20px;text-align:center;font-size:12px;color:#94a3b8}}
</style>
</head>
<body>
<div class="header">
  <h1>🧪 {APP_NAME} — Daily Sanity Report</h1>
  <p>{run_date} &nbsp;|&nbsp; Completed in {elapsed}s &nbsp;|&nbsp; Selenium</p>
  <div class="badge">{overall}</div>
</div>
<div class="cards">
  <div class="card"><div class="num">{len(results)}</div><div class="lbl">Pages tested</div></div>
  <div class="card"><div class="num" style="color:#16a34a">{passed}</div><div class="lbl">Passed</div></div>
  <div class="card"><div class="num" style="color:{'#dc2626' if failed else '#16a34a'}">{failed}</div><div class="lbl">Failed</div></div>
  <div class="card"><div class="num">{elapsed}s</div><div class="lbl">Total time</div></div>
</div>
<table>
  <thead>
    <tr><th>Page</th><th>Status</th><th>URL</th><th>Load Time</th><th>Details</th></tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
{'<div style="margin-top:16px;padding:16px;background:#fef9c3;border-radius:8px;color:#854d0e">⚠️ ' + str(expired) + ' page(s) redirected to login. Run capture_session.py to refresh your session.</div>' if expired else ''}
<div class="footer">ATT Atlas UI Sanity Automation (Selenium) — {run_date}</div>
</body>
</html>"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)
    return report_path


def run_sanity():
    start_time = time.time()
    run_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'='*60}")
    print(f"  ATT ATLAS UI — DAILY SANITY (Selenium)")
    print(f"  {run_date}")
    print(f"{'='*60}\n")

    driver = create_driver()
    results = []

    try:
        # Load session
        if not load_session(driver):
            driver.quit()
            return

        print(f"\n[TESTING] Checking {len(PAGES)} pages...\n")

        for page in PAGES:
            result = check_page(driver, page)
            results.append(result)
            time.sleep(1)  # Small delay between pages

    finally:
        driver.quit()

    elapsed = round(time.time() - start_time, 1)
    report_path = generate_report(results, run_date, elapsed)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    expired = sum(1 for r in results if r.get("session_expired"))

    print(f"\n{'='*60}")
    print(f"  ✅ PASSED: {passed}  |  ❌ FAILED: {failed}  |  ⏱ {elapsed}s")
    if expired:
        print(f"  🔒 {expired} pages session expired — run capture_session.py")
    print(f"  📄 Report: {report_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run_sanity()
