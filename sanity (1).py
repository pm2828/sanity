"""
sanity.py
---------
Daily sanity check for ATT Atlas UI.
Loads saved session — no login needed.
Generates HTML + DOCX reports with screenshots.

Key behaviours
--------------
1.  Clicks the "Install" card/tab on the home page BEFORE navigating to
    any endpoint.  The locators are taken directly from the DevTools DOM
    visible in the reference screenshots:

      app-cards-job
        └─ div.card
             └─ div.row.m-0
                  └─ div.column.left.border-right.left-bg-navyblue   ← click target
                       └─ app-page-header
                            └─ h1  (text = "Install")

    Four CSS / XPath locators are tried in order, followed by three JS
    strategies, so one of them will succeed regardless of minor class-name
    variations between builds.

2.  After navigating to each endpoint, waits for the page to be fully
    loaded (document.readyState + no visible spinner) before capturing a
    screenshot.

3.  Detects session expiry and home-page redirects and marks them FAIL.

Usage:
    python sanity.py
"""

import pickle, time, json, subprocess, sys
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException
)

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL    = "https://atlasui-eastus2-prod.az.3pc.att.com"
COOKIE_FILE = "session.pkl"
SS_DIR      = Path("screenshots"); SS_DIR.mkdir(exist_ok=True)
RPT_DIR     = Path("reports");     RPT_DIR.mkdir(exist_ok=True)

PAGE_LOAD_TIMEOUT  = 30   # seconds — document.readyState
SPINNER_TIMEOUT    = 20   # seconds — Angular loading overlay
POST_LOAD_SETTLE_S = 1.5  # seconds — brief settle after spinner clears

# All endpoints that require the Install tab to be active.
# /job is listed first so it is tested immediately after the Install click.
PAGES = [
    {"name": "Home",               "url": "/"},
    {"name": "Job",                "url": "/job"},          # primary post-Install page
    {"name": "Customer",           "url": "/customer"},
    {"name": "Customer History",   "url": "/customer-history"},
    {"name": "Facilities",         "url": "/facilities"},
    {"name": "Tests Dynamic",      "url": "/tests-dynamic"},
    {"name": "CPE Test",           "url": "/cpe-test"},
    {"name": "Trouble Shoot",      "url": "/trouble-shoot"},
    {"name": "Sync No Service",    "url": "/sync-no-service"},
    {"name": "Troubleshoot VOIP",  "url": "/troubleshoot-voip"},
    {"name": "System Health",      "url": "/system-health"},
]

# ── Browser setup ─────────────────────────────────────────────────────────────
def get_driver():
    opt = Options()
    opt.add_argument("--headless=new")
    opt.add_argument("--window-size=1366,768")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--ignore-certificate-errors")
    opt.add_argument("--log-level=3")
    driver = webdriver.Chrome(options=opt)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    return driver

# ── Session loader ────────────────────────────────────────────────────────────
def load_session(driver):
    if not Path(COOKIE_FILE).exists():
        print("ERROR: session.pkl not found. Run save_session.py first.")
        sys.exit(1)

    driver.get(BASE_URL)
    _wait_for_page_ready(driver)
    for c in pickle.load(open(COOKIE_FILE, "rb")):
        c.pop("sameSite", None)
        c.pop("expiry",   None)
        try:
            driver.add_cookie(c)
        except Exception:
            pass
    driver.get(BASE_URL)          # refresh so cookies take effect
    _wait_for_page_ready(driver)
    print(f"[OK] Session loaded from {COOKIE_FILE}\n")

# ── Page-load wait helpers ────────────────────────────────────────────────────
def _wait_for_page_ready(driver, timeout=PAGE_LOAD_TIMEOUT):
    """Block until document.readyState == 'complete'."""
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )

def _wait_for_no_spinner(driver, timeout=SPINNER_TIMEOUT):
    """
    Poll until Angular / ATT Atlas loading overlays have disappeared.
    Covers mat-progress-bar, mat-spinner, and common CSS-class patterns.
    """
    SPINNER_SELECTORS = [
        "mat-progress-bar",
        "mat-spinner",
        ".loading",
        ".spinner",
        ".loader",
        ".progress-overlay",
        "[class*='loading']",
        "[class*='spinner']",
    ]
    deadline = time.time() + timeout
    while time.time() < deadline:
        visible = False
        for sel in SPINNER_SELECTORS:
            try:
                if any(e.is_displayed()
                       for e in driver.find_elements(By.CSS_SELECTOR, sel)):
                    visible = True
                    break
            except Exception:
                pass
        if not visible:
            return
        time.sleep(0.4)
    # Timed-out — proceed anyway

def _full_page_wait(driver):
    """readyState complete  +  no spinner  +  short settle pause."""
    _wait_for_page_ready(driver)
    _wait_for_no_spinner(driver)
    time.sleep(POST_LOAD_SETTLE_S)

# ── Install tab click ─────────────────────────────────────────────────────────
def click_install_tab(driver):
    """
    Locate and click the Install card on the ATT Atlas home page.

    DOM structure confirmed from DevTools screenshots
    (breadcrumb: app-cards-job > div.card > div.row.m-0 > div.column.left ...):

      L1  CSS   — div.column.left.border-right.left-bg-navyblue   (blue panel)
      L2  XPath — //app-cards-job//div[contains(@class,'left-bg-navyblue')]//h1
      L3  XPath — any div[left-bg-navyblue] whose text contains "Install"
      L4  XPath — sibling lookup via transport-title "FTTP-GPON" text

    If all four fail, three JS strategies scan the live DOM directly.
    """
    print("[INFO] Navigating to home page to activate Install tab ...")
    try:
        driver.get(BASE_URL)
        _full_page_wait(driver)
    except Exception as e:
        print(f"[WARN] Home page load issue: {e}")

    # ── Ordered Selenium locators derived from DevTools DOM ───────────────
    install_locators = [
        # L1 — exact CSS class chain from the DevTools breadcrumb
        (By.CSS_SELECTOR,
         "app-cards-job div.card div.row.m-0 "
         "div.column.left.border-right.left-bg-navyblue"),

        # L2 — h1 inside the navyblue left column of app-cards-job
        (By.XPATH,
         "//app-cards-job"
         "//div[contains(@class,'left-bg-navyblue')]"
         "//h1"),

        # L3 — any navyblue column whose full text contains "Install"
        (By.XPATH,
         "//div[contains(@class,'left-bg-navyblue') and "
         "contains(normalize-space(.),'Install')]"),

        # L4 — navigate from FTTP-GPON transport-title up to the row div,
        #       then back down to the left-bg-navyblue column
        (By.XPATH,
         "//div[contains(@class,'transport-title') and contains(.,'FTTP')]"
         "/ancestor::div[contains(@class,'row')]"
         "//div[contains(@class,'left-bg-navyblue')]"),
    ]

    tab_clicked = False
    for by, locator in install_locators:
        try:
            el = WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((by, locator))
            )
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", el
            )
            time.sleep(0.3)
            try:
                el.click()                                       # normal click
            except Exception:
                driver.execute_script("arguments[0].click();", el)  # JS fallback

            _full_page_wait(driver)
            print(f"[OK] Install tab clicked  ->  locator: {locator}\n")
            tab_clicked = True
            break

        except (TimeoutException, NoSuchElementException):
            print(f"[DEBUG] Locator not found: {locator}")
            continue
        except Exception as e:
            print(f"[WARN] Click failed ({locator}): {e}")
            continue

    # ── JavaScript deep-scan fallback ─────────────────────────────────────
    if not tab_clicked:
        print("[WARN] All Selenium locators failed — trying JS deep-scan ...")
        try:
            strategy = driver.execute_script("""
                // JS-A: div with class 'left-bg-navyblue' containing 'Install'
                var cols = document.querySelectorAll('div.left-bg-navyblue');
                for (var i = 0; i < cols.length; i++) {
                    if (cols[i].textContent.indexOf('Install') !== -1) {
                        cols[i].click();
                        return 'JS-A: div.left-bg-navyblue';
                    }
                }
                // JS-B: any element whose class contains 'navyblue' and text has Install
                var nbs = document.querySelectorAll('[class*="navyblue"]');
                for (var j = 0; j < nbs.length; j++) {
                    if (nbs[j].textContent.indexOf('Install') !== -1) {
                        nbs[j].click();
                        return 'JS-B: [class*=navyblue]';
                    }
                }
                // JS-C: h1 whose exact trimmed text is 'Install'
                var h1s = document.querySelectorAll('h1');
                for (var k = 0; k < h1s.length; k++) {
                    if (h1s[k].textContent.trim() === 'Install') {
                        h1s[k].click();
                        return 'JS-C: h1[Install]';
                    }
                }
                return null;
            """)

            if strategy:
                _full_page_wait(driver)
                print(f"[OK] Install tab clicked via {strategy}\n")
                tab_clicked = True
            else:
                print("[WARN] JS deep-scan: no matching element found.")
        except Exception as e:
            print(f"[WARN] JS deep-scan exception: {e}")

    if not tab_clicked:
        print(
            "[ERROR] Install tab could NOT be clicked.\n"
            "        Endpoints may redirect to home — inspect the DOM manually.\n"
        )

# ── Test one page ─────────────────────────────────────────────────────────────
def test_page(driver, page):
    name = page["name"]
    url  = BASE_URL + page["url"]
    ss   = str(SS_DIR / f"{name.lower().replace(' ', '_')}.png")
    r    = {
        "name": name, "url": url,
        "status": "PASS", "note": "", "time_ms": 0, "screenshot": ss
    }

    try:
        t0 = time.time()
        driver.get(url)

        # Wait for the page to be fully ready BEFORE doing anything else
        _full_page_wait(driver)

        r["time_ms"] = round((time.time() - t0) * 1000)
        current      = driver.current_url.lower()

        # Session-expired check
        if any(x in current for x in ["login", "signin", "auth", "sso"]):
            r["status"] = "FAIL"
            r["note"]   = "Session expired — re-run save_session.py"

        # Redirect-back-to-home check
        elif page["url"] != "/" and current.rstrip("/") in (
            BASE_URL.lower(), BASE_URL.lower() + "/"
        ):
            r["status"] = "FAIL"
            r["note"]   = "Redirected to home — Install tab may not be active"

        else:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            r["note"] = "Page loaded OK"

        # Screenshot captured only after page is fully settled
        driver.save_screenshot(ss)

        icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"  {icon}  {name:<22} {r['status']}  ({r['time_ms']} ms)  {r['note']}")

    except TimeoutException:
        r["status"] = "FAIL"
        r["note"]   = "Page load timed out"
        try:   driver.save_screenshot(ss)
        except Exception: r["screenshot"] = None
        print(f"  ❌  {name:<22} TIMEOUT")

    except WebDriverException as e:
        r["status"] = "FAIL"
        r["note"]   = str(e)[:80]
        try:   driver.save_screenshot(ss)
        except Exception: r["screenshot"] = None
        print(f"  ❌  {name:<22} ERROR: {r['note']}")

    return r

# ── HTML report ───────────────────────────────────────────────────────────────
def html_report(results, run_date, secs):
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = len(results) - passed
    status = "PASS" if failed == 0 else "FAIL"
    sc     = "#22c55e" if status == "PASS" else "#ef4444"

    rows = ""
    for r in results:
        bg = "#f0fdf4" if r["status"] == "PASS" else "#fee2e2"
        fc = "#16a34a" if r["status"] == "PASS" else "#dc2626"
        rows += (
            f'<tr style="background:{bg}">'
            f"<td>{r['name']}</td>"
            f'<td style="color:{fc};font-weight:700">{r["status"]}</td>'
            f'<td style="font-size:12px;color:#6b7280">{r["url"]}</td>'
            f"<td>{r['time_ms']} ms</td>"
            f'<td style="font-size:12px">{r["note"]}</td></tr>\n'
        )

    path = RPT_DIR / f"sanity_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    path.write_text(f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  body  {{font-family:Arial,sans-serif;padding:24px;background:#f8fafc;color:#1e293b}}
  h1    {{background:#1e293b;color:white;padding:20px 24px;border-radius:10px;
          font-size:20px;margin:0 0 12px}}
  .badge{{display:inline-block;padding:6px 18px;border-radius:999px;
          background:{sc};color:white;font-weight:700;font-size:16px;margin:8px 0 16px}}
  .cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:0 0 20px}}
  .card {{background:white;border-radius:8px;padding:16px;
          box-shadow:0 1px 3px rgba(0,0,0,.1)}}
  .num  {{font-size:28px;font-weight:700}}
  .lbl  {{font-size:12px;color:#94a3b8;margin-top:4px}}
  table {{width:100%;border-collapse:collapse;background:white;border-radius:8px;
          overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)}}
  th    {{background:#f1f5f9;padding:10px 12px;text-align:left;
          font-size:13px;color:#64748b;border-bottom:1px solid #e2e8f0}}
  td    {{padding:10px 12px;border-bottom:1px solid #f1f5f9;font-size:14px}}
</style></head><body>
<h1>&#129514; ATT Atlas UI &#8212; Daily Sanity Report</h1>
<p style="color:#64748b;margin:0 0 8px">{run_date} &nbsp;|&nbsp; {secs} s</p>
<div class="badge">{status}</div>
<div class="cards">
  <div class="card"><div class="num">{len(results)}</div><div class="lbl">Pages</div></div>
  <div class="card"><div class="num" style="color:#16a34a">{passed}</div><div class="lbl">Passed</div></div>
  <div class="card"><div class="num" style="color:{'#dc2626' if failed else '#16a34a'}">{failed}</div><div class="lbl">Failed</div></div>
  <div class="card"><div class="num">{secs} s</div><div class="lbl">Duration</div></div>
</div>
<table>
  <thead><tr><th>Page</th><th>Status</th><th>URL</th><th>Time</th><th>Note</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
</body></html>""", encoding="utf-8")
    return str(path)

# ── DOCX report via Node.js ───────────────────────────────────────────────────
def docx_report(results, run_date, secs):
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    jpath    = RPT_DIR / f"_tmp_{ts}.json"
    docxpath = RPT_DIR / f"sanity_{ts}.docx"

    json.dump({"run_date": run_date, "secs": secs, "results": results},
              open(jpath, "w"), indent=2)

    js = Path("generate_report.js")
    if not js.exists():
        jpath.unlink(missing_ok=True)
        return None

    try:
        proc = subprocess.run(
            ["node", str(js), str(jpath), str(docxpath)],
            capture_output=True, text=True, timeout=60
        )
        jpath.unlink(missing_ok=True)
        if proc.returncode == 0:
            return str(docxpath)
        print(f"[DOCX] Node error: {proc.stderr[:200]}")
        return None
    except FileNotFoundError:
        print("[DOCX] Node.js not installed — skipping DOCX report.")
        jpath.unlink(missing_ok=True)
        return None

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    run_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*54}")
    print(f"  ATT ATLAS UI — SANITY CHECK  |  {run_date}")
    print(f"{'='*54}\n")

    driver = get_driver()
    load_session(driver)

    # STEP 1 — Click Install tab (mandatory before any endpoint navigation)
    click_install_tab(driver)

    # STEP 2 — Iterate pages; Job is first after Home, validating the click
    print("Testing pages ...\n")
    results = [test_page(driver, p) for p in PAGES]
    driver.quit()

    secs = round(
        time.time() - time.mktime(
            datetime.strptime(run_date, "%Y-%m-%d %H:%M:%S").timetuple()
        ), 1
    )

    # STEP 3 — Generate HTML + DOCX reports
    html = html_report(results, run_date, secs)
    docx = docx_report(results, run_date, secs)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = len(results) - passed

    print(f"\n{'='*54}")
    print(f"  Passed : {passed}   Failed : {failed}   Duration : {secs} s")
    print(f"  HTML   : {html}")
    if docx:
        print(f"  DOCX   : {docx}")
    print(f"{'='*54}\n")


if __name__ == "__main__":
    main()
