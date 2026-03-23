# ATT Atlas UI — Daily Sanity (Selenium)

No greenlet needed! Works with Python 3.14 directly.

---

## Step 1 — Download on internet machine

Run this on internet machine:
```cmd
pip download selenium -d C:\selenium-packages
```

Also download ChromeDriver matching your Chrome version:
```
https://googlechromelabs.github.io/chrome-for-testing/
```
Extract chromedriver.exe to: C:\chromedriver\chromedriver.exe

---

## Step 2 — Install on corporate machine

```cmd
"C:\Users\pm3562\AppData\Local\Python\bin\python.exe" -m pip install --no-index --find-links=C:\selenium-packages selenium
```

---

## Step 3 — Update chromedriver path

Open att_sanity.py and capture_session.py
Change this line to match where you put chromedriver:
```python
CHROME_DRIVER_PATH = r"C:\chromedriver\chromedriver.exe"
```

---

## Step 4 — Capture session (run once)

```cmd
"C:\Users\pm3562\AppData\Local\Python\bin\python.exe" capture_session.py
```
- Browser opens → log in manually → press Enter → done!

---

## Step 5 — Run daily sanity

```cmd
"C:\Users\pm3562\AppData\Local\Python\bin\python.exe" att_sanity.py
```

---

## Find your Chrome version

Open Chrome → type in address bar:
```
chrome://version
```
Note the version number e.g. 133.0.xxxx
Download matching chromedriver from:
```
https://googlechromelabs.github.io/chrome-for-testing/
```
# sanity
