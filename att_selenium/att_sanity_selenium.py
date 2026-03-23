"""
ATT Atlas UI - Daily Sanity Automation using Selenium
======================================================
Generates both HTML and DOCX reports with screenshots.

Run:
    python att_sanity_selenium.py           -- daily sanity
    python att_sanity_selenium.py --capture -- capture login session
"""

import json
import os
import sys
import time
import pickle
import subprocess
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_DIR        = Path(__file__).parent
PAGES_FILE      = BASE_DIR / "pages.json"
COOKIES_FILE    = BASE_DIR / "cookies.pkl"
REPORTS_DIR     = BASE_DIR / "reports"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
CHROMEDRIVER    = BASE_DIR / "chromedriver.exe"
REPORT_JS       = BASE_DIR / "generate_report.js"

REPORTS_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def get_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1366,768")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--log-level=3")

    if CHROMEDRIVER.exists():
        service = Service(str(CHROMEDRIVER))
        driver = webdriver.Chrome(service=service, options=options)
    else:
        try:
            driver = webdriver.Chrome(options=options)
        except Exception as e:
            print(f"\n❌ ChromeDriver not found: {e}")
            print("   Place chromedriver.exe in same folder as this script.")
            raise
    return driver


def capture_session():
    with open(PAGES_FILE) as f:
        config = json.load(f)
    base_url = config["base_url"]
    print("\n" + "="*60)
    print("  SESSION CAPTURE — Login manually")
    print("="*60)
    driver = get_driver(headless=False)
    driver.get(base_url)
    print(f"\nBrowser opened at: {base_url}")
    print("\n--- ACTION REQUIRED ---")
    print("1. Log in with your username and password")
    print("2. Complete 2FA / authentication steps")
    print("3. Wait until dashboard is fully loaded")
    input("\nPress Enter HERE after you are fully logged in...")
    cookies = driver.get_cookies()
    with open(COOKIES_FILE, "wb") as f:
        pickle.dump(cookies, f)
    print(f"\n✅ Session saved — {len(cookies)} cookies captured")
    driver.quit()


def load_session(driver, base_url):
    if not COOKIES_FILE.exists():
        print("❌ cookies.pkl not found! Run with --capture first.")
        return False
    driver.get(base_url)
    time.sleep(2)
    with open(COOKIES_FILE, "rb") as f:
        cookies = pickle.load(f)
    for cookie in cookies:
        cookie.pop("sameSite", None)
        cookie.pop("expiry", None)
        try:
            driver.add_cookie(cookie)
        except Exception:
            pass
    print(f"[SESSION] Loaded {len(cookies)} cookies")
    return True


def check_page(driver, page_cfg, base_url):
    name = page_cfg["name"]
    url  = base_url + page_cfg["url"]
    safe_name = name.lower().replace(" ", "_")
    screenshot_path = str(SCREENSHOTS_DIR / f"{safe_name}.png")

    result = {
        "name": name,
        "url": url,
        "status": "PASS",
        "checks": [],
        "error": None,
        "load_time_ms": 0,
        "screenshot": screenshot_path,
        "redirected_to_login": False
    }

    try:
        start = time.time()
        driver.get(url)
        time.sleep(2)
        result["load_time_ms"] = round((time.time() - start) * 1000)

        current_url = driver.current_url.lower()
        if any(x in current_url for x in ["login", "signin", "auth", "sso"]):
            result["redirected_to_login"] = True
            result["status"] = "FAIL"
            result["error"]  = "Redirected to login — session expired!"
            driver.save_screenshot(screenshot_path)
            print(f"  🔒 [{name}] Session expired!")
            return result

        for check in page_cfg.get("ui_checks", []):
            selector  = check["selector"]
            check_res = {"selector": selector, "status": "PASS", "detail": ""}
            try:
                selectors = [s.strip() for s in selector.split(",")]
                found = False
                for sel in selectors:
                    try:
                        el = WebDriverWait(driver, 5).until(
                            EC.visibility_of_element_located((By.CSS_SELECTOR, sel))
                        )
                        check_res["detail"] = "Visible"
                        found = True
                        if check.get("expect_text"):
                            text = el.text.strip()
                            if check["expect_text"].lower() in text.lower():
                                check_res["detail"] = f"Text OK: '{text[:40]}'"
                            else:
                                check_res["status"] = "FAIL"
                                check_res["detail"] = f"Expected '{check['expect_text']}'"
                                result["status"]    = "FAIL"
                        break
                    except Exception:
                        continue
                if not found:
                    check_res["status"] = "WARN"
                    check_res["detail"] = "Element not found"
            except Exception as e:
                check_res["status"] = "WARN"
                check_res["detail"] = str(e)[:50]
            result["checks"].append(check_res)

        driver.save_screenshot(screenshot_path)
        icon = "✅" if result["status"] == "PASS" else "❌"
        print(f"  {icon} [{name}] {result['status']} ({result['load_time_ms']}ms) 📸")

    except Exception as e:
        result["status"] = "FAIL"
        result["error"]  = str(e)[:100]
        try:
            driver.save_screenshot(screenshot_path)
        except Exception:
            result["screenshot"] = None
        print(f"  ❌ [{name}] ERROR: {e}")

    return result


def generate_html_report(results, run_date, elapsed, app_name):
    passed   = sum(1 for r in results if r["status"] == "PASS")
    failed   = sum(1 for r in results if r["status"] == "FAIL")
    overall  = "PASS" if failed == 0 else "FAIL"
    ov_color = "#22c55e" if overall == "PASS" else "#ef4444"
    rows = ""
    for r in results:
        bg       = "#f0fdf4" if r["status"] == "PASS" else "#fee2e2"
        st_color = "#16a34a" if r["status"] == "PASS" else "#dc2626"
        checks_html = "".join(
            f'<div style="font-size:11px">{"✅" if c["status"]=="PASS" else "⚠️"} '
            f'<code>{c["selector"]}</code> — {c["detail"]}</div>'
            for c in r.get("checks", [])
        )
        error_html = f'<div style="color:#dc2626;font-size:11px">{r["error"]}</div>' if r.get("error") else ""
        rows += f"""<tr style="background:{bg}">
          <td style="padding:10px 14px;font-weight:500">{r['name']}</td>
          <td style="padding:10px 14px"><span style="color:{st_color};font-weight:700">{r['status']}</span></td>
          <td style="padding:10px 14px;font-size:12px;color:#6b7280">{r['url']}</td>
          <td style="padding:10px 14px;font-size:12px">{r['load_time_ms']}ms</td>
          <td style="padding:10px 14px">{checks_html}{error_html}</td></tr>"""

    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"att_sanity_{timestamp}.html"
    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>ATT Sanity — {run_date}</title>
<style>body{{font-family:-apple-system,sans-serif;margin:0;padding:24px;background:#f8fafc;color:#1e293b}}
.hdr{{background:#1e293b;color:white;border-radius:12px;padding:28px 32px;margin-bottom:24px}}
.hdr h1{{margin:0 0 4px;font-size:22px}}.hdr p{{margin:0;opacity:.6;font-size:14px}}
.badge{{display:inline-block;padding:6px 20px;border-radius:999px;font-size:18px;font-weight:700;margin-top:12px;background:{ov_color};color:white}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}}
.card{{background:white;border-radius:10px;padding:20px 24px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.card .num{{font-size:32px;font-weight:700}}.card .lbl{{font-size:13px;color:#94a3b8}}
table{{width:100%;border-collapse:collapse;background:white;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
th{{background:#f1f5f9;padding:12px 14px;text-align:left;font-size:13px;color:#64748b;font-weight:600;border-bottom:1px solid #e2e8f0}}
td{{border-bottom:1px solid #f1f5f9;vertical-align:top}}code{{background:#f1f5f9;padding:2px 5px;border-radius:4px;font-size:11px}}</style></head><body>
<div class="hdr"><h1>🧪 {app_name} — Daily Sanity Report</h1>
<p>{run_date} | {elapsed}s</p><div class="badge">{overall}</div></div>
<div class="cards">
<div class="card"><div class="num">{len(results)}</div><div class="lbl">Pages tested</div></div>
<div class="card"><div class="num" style="color:#16a34a">{passed}</div><div class="lbl">Passed</div></div>
<div class="card"><div class="num" style="color:{'#dc2626' if failed else '#16a34a'}">{failed}</div><div class="lbl">Failed</div></div>
<div class="card"><div class="num">{elapsed}s</div><div class="lbl">Time</div></div></div>
<table><thead><tr><th>Page</th><th>Status</th><th>URL</th><th>Load</th><th>Details</th></tr></thead>
<tbody>{rows}</tbody></table></body></html>"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)
    return str(report_path)


def generate_docx_report(results, run_date, elapsed, app_name):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = REPORTS_DIR / f"sanity_results_{timestamp}.json"
    docx_path = REPORTS_DIR / f"att_sanity_{timestamp}.docx"

    payload = {
        "app_name": app_name,
        "run_date": run_date,
        "elapsed": elapsed,
        "results": results
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("\n[DOCX] Generating Word report with all screenshots...")
    try:
        result = subprocess.run(
            ["node", str(REPORT_JS), str(json_path), str(docx_path)],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            print(f"[DOCX] ✅ Saved → {docx_path}")
            json_path.unlink(missing_ok=True)
            return str(docx_path)
        else:
            print(f"[DOCX] ❌ Node error: {result.stderr[:300]}")
            return None
    except FileNotFoundError:
        print("[DOCX] ❌ Node.js not found!")
        print("        Install Node.js from: https://nodejs.org/en/download")
        print("        Then run: npm install -g docx")
        return None
    except Exception as e:
        print(f"[DOCX] ❌ Failed: {e}")
        return None


def run_sanity():
    start_time = time.time()
    run_date   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'='*60}")
    print(f"  ATT ATLAS UI — DAILY SANITY CHECK")
    print(f"  {run_date}")
    print(f"{'='*60}")

    if not COOKIES_FILE.exists():
        print("\n⚠️  No session found — capturing session first...")
        capture_session()

    with open(PAGES_FILE) as f:
        config = json.load(f)

    base_url = config["base_url"]
    pages    = config["pages"]
    results  = []

    driver = get_driver(headless=True)
    if not load_session(driver, base_url):
        driver.quit()
        return

    print(f"\n[TESTING] Checking {len(pages)} pages...\n")
    for page_cfg in pages:
        result = check_page(driver, page_cfg, base_url)
        results.append(result)

    driver.quit()

    elapsed   = round(time.time() - start_time, 1)
    html_path = generate_html_report(results, run_date, elapsed, config["app_name"])
    docx_path = generate_docx_report(results, run_date, elapsed, config["app_name"])

    passed  = sum(1 for r in results if r["status"] == "PASS")
    failed  = sum(1 for r in results if r["status"] == "FAIL")
    expired = sum(1 for r in results if r.get("redirected_to_login"))

    print(f"\n{'='*60}")
    print(f"  ✅ PASSED : {passed}")
    print(f"  ❌ FAILED : {failed}")
    print(f"  ⏱  TIME   : {elapsed}s")
    print(f"  🌐 HTML   : {html_path}")
    if docx_path:
        print(f"  📝 DOCX   : {docx_path}")
    if expired:
        print(f"  🔒 Session expired on {expired} page(s) — re-run with --capture")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if "--capture" in sys.argv:
        capture_session()
    else:
        run_sanity()
