"""
sanity.py
---------
Daily sanity check for ATT Atlas UI.
Loads saved session — no login needed.
Generates HTML + DOCX reports with screenshots.

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

# ── Config ────────────────────────────────────────────────
BASE_URL    = "https://atlasui-eastus2-prod.az.3pc.att.com"
COOKIE_FILE = "session.pkl"
SS_DIR      = Path("screenshots"); SS_DIR.mkdir(exist_ok=True)
RPT_DIR     = Path("reports");     RPT_DIR.mkdir(exist_ok=True)

PAGES = [
    {"name": "Home",               "url": "/"},
    {"name": "Job",                "url": "/job"},
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

# ── Browser setup ─────────────────────────────────────────
def get_driver():
    opt = Options()
    opt.add_argument("--headless=new")
    opt.add_argument("--window-size=1366,768")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--ignore-certificate-errors")
    opt.add_argument("--log-level=3")
    return webdriver.Chrome(options=opt)

# ── Load saved session ────────────────────────────────────
def load_session(driver):
    if not Path(COOKIE_FILE).exists():
        print("ERROR: session.pkl not found. Run save_session.py first.")
        sys.exit(1)

    driver.get(BASE_URL)
    time.sleep(1)
    for c in pickle.load(open(COOKIE_FILE, "rb")):
        c.pop("sameSite", None)
        c.pop("expiry", None)
        try: driver.add_cookie(c)
        except: pass
    print(f"[OK] Session loaded from {COOKIE_FILE}\n")

# ── Test one page ─────────────────────────────────────────
def test_page(driver, page):
    name = page["name"]
    url  = BASE_URL + page["url"]
    ss   = str(SS_DIR / f"{name.lower().replace(' ','_')}.png")
    r    = {"name": name, "url": url, "status": "PASS",
            "note": "", "time_ms": 0, "screenshot": ss}
    try:
        t0 = time.time()
        driver.get(url)
        time.sleep(2)
        r["time_ms"] = round((time.time() - t0) * 1000)

        # Session expired check
        if any(x in driver.current_url.lower() for x in ["login","signin","auth","sso"]):
            r["status"] = "FAIL"
            r["note"]   = "Session expired — re-run save_session.py"
        else:
            # Basic page load check
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            r["note"] = "Page loaded OK"

        driver.save_screenshot(ss)
        icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"  {icon} {name} — {r['status']} ({r['time_ms']}ms)")

    except Exception as e:
        r["status"] = "FAIL"
        r["note"]   = str(e)[:80]
        try: driver.save_screenshot(ss)
        except: r["screenshot"] = None
        print(f"  ❌ {name} — ERROR: {r['note']}")

    return r

# ── HTML Report ───────────────────────────────────────────
def html_report(results, run_date, secs):
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = len(results) - passed
    status = "PASS" if failed == 0 else "FAIL"
    sc     = "#22c55e" if status == "PASS" else "#ef4444"

    rows = ""
    for r in results:
        bg = "#f0fdf4" if r["status"] == "PASS" else "#fee2e2"
        fc = "#16a34a" if r["status"] == "PASS" else "#dc2626"
        rows += f"""<tr style="background:{bg}">
          <td>{r['name']}</td>
          <td style="color:{fc};font-weight:700">{r['status']}</td>
          <td style="font-size:12px;color:#6b7280">{r['url']}</td>
          <td>{r['time_ms']}ms</td>
          <td style="font-size:12px">{r['note']}</td></tr>"""

    path = RPT_DIR / f"sanity_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    path.write_text(f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>body{{font-family:Arial,sans-serif;padding:24px;background:#f8fafc;color:#1e293b}}
h1{{background:#1e293b;color:white;padding:20px 24px;border-radius:10px;font-size:20px}}
.badge{{display:inline-block;padding:6px 18px;border-radius:999px;background:{sc};color:white;font-weight:700;font-size:16px;margin:8px 0}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0}}
.card{{background:white;border-radius:8px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.1)}}
.num{{font-size:28px;font-weight:700}}.lbl{{font-size:12px;color:#94a3b8}}
table{{width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)}}
th{{background:#f1f5f9;padding:10px 12px;text-align:left;font-size:13px;color:#64748b;border-bottom:1px solid #e2e8f0}}
td{{padding:10px 12px;border-bottom:1px solid #f1f5f9}}</style></head><body>
<h1>🧪 ATT Atlas UI — Daily Sanity Report</h1>
<p style="color:#64748b">{run_date} &nbsp;|&nbsp; {secs}s</p>
<div class="badge">{status}</div>
<div class="cards">
<div class="card"><div class="num">{len(results)}</div><div class="lbl">Pages</div></div>
<div class="card"><div class="num" style="color:#16a34a">{passed}</div><div class="lbl">Passed</div></div>
<div class="card"><div class="num" style="color:{'#dc2626' if failed else '#16a34a'}">{failed}</div><div class="lbl">Failed</div></div>
<div class="card"><div class="num">{secs}s</div><div class="lbl">Duration</div></div></div>
<table><thead><tr><th>Page</th><th>Status</th><th>URL</th><th>Time</th><th>Note</th></tr></thead>
<tbody>{rows}</tbody></table></body></html>""", encoding="utf-8")
    return str(path)

# ── DOCX Report via Node.js ───────────────────────────────
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
        r = subprocess.run(["node", str(js), str(jpath), str(docxpath)],
                           capture_output=True, text=True, timeout=60)
        jpath.unlink(missing_ok=True)
        if r.returncode == 0:
            return str(docxpath)
        print(f"[DOCX] Node error: {r.stderr[:200]}")
        return None
    except FileNotFoundError:
        print("[DOCX] Node.js not installed — skipping DOCX.")
        jpath.unlink(missing_ok=True)
        return None

# ── Main ──────────────────────────────────────────────────
def main():
    run_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*52}")
    print(f"  ATT ATLAS UI — SANITY CHECK  |  {run_date}")
    print(f"{'='*52}\n")

    driver = get_driver()
    load_session(driver)

    results = [test_page(driver, p) for p in PAGES]
    driver.quit()

    secs     = round(time.time() - time.mktime(
                   datetime.strptime(run_date, "%Y-%m-%d %H:%M:%S").timetuple()), 1)
    html     = html_report(results, run_date, secs)
    docx     = docx_report(results, run_date, secs)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = len(results) - passed

    print(f"\n{'='*52}")
    print(f"  ✅ Passed : {passed}  ❌ Failed : {failed}  ⏱ {secs}s")
    print(f"  🌐 HTML  : {html}")
    if docx: print(f"  📝 DOCX  : {docx}")
    print(f"{'='*52}\n")

if __name__ == "__main__":
    main()
