"""
Word Report Generator — No lxml needed!
Generates .docx file using pure Python (zipfile + xml)
Works with Python 3.14 — zero extra packages required.
"""

import zipfile
import os
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def make_docx(results, run_date, elapsed, app_name):
    """Generate a Word .docx report without python-docx or lxml."""

    passed  = sum(1 for r in results if r["status"] == "PASS")
    failed  = sum(1 for r in results if r["status"] == "FAIL")
    overall = "PASS" if failed == 0 else "FAIL"

    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    docx_path   = REPORTS_DIR / f"ATT_Sanity_{timestamp}.docx"

    # ── Build table rows ──────────────────────────────────────
    table_rows = ""
    for r in results:
        status  = r["status"]
        color   = "FF0000" if status == "FAIL" else "00AA00"
        bg      = "FFE0E0" if status == "FAIL" else "E0FFE0"

        # Check details as bullet text
        check_lines = ""
        for c in r.get("checks", []):
            icon = "PASS" if c["status"] == "PASS" else "WARN"
            check_lines += f"""
            <w:p>
              <w:pPr><w:ind w:left="200"/></w:pPr>
              <w:r><w:rPr><w:sz w:val="16"/></w:rPr>
                <w:t xml:space="preserve">{icon}: {c['selector'][:40]} — {c['detail'][:60]}</w:t>
              </w:r>
            </w:p>"""

        error_line = ""
        if r.get("error"):
            error_line = f"""
            <w:p>
              <w:pPr><w:ind w:left="200"/></w:pPr>
              <w:r><w:rPr><w:color w:val="FF0000"/><w:sz w:val="16"/></w:rPr>
                <w:t>ERROR: {str(r['error'])[:80]}</w:t>
              </w:r>
            </w:p>"""

        table_rows += f"""
        <w:tr>
          <w:trPr><w:shd w:val="clear" w:color="auto" w:fill="{bg}"/></w:trPr>

          <w:tc>
            <w:tcPr><w:tcW w:w="1800" w:type="dxa"/>
              <w:shd w:val="clear" w:color="auto" w:fill="{bg}"/>
            </w:tcPr>
            <w:p><w:r><w:rPr><w:b/><w:sz w:val="18"/></w:rPr>
              <w:t>{r['name']}</w:t></w:r></w:p>
          </w:tc>

          <w:tc>
            <w:tcPr><w:tcW w:w="900" w:type="dxa"/>
              <w:shd w:val="clear" w:color="auto" w:fill="{bg}"/>
            </w:tcPr>
            <w:p><w:r><w:rPr><w:b/><w:color w:val="{color}"/><w:sz w:val="18"/></w:rPr>
              <w:t>{status}</w:t></w:r></w:p>
          </w:tc>

          <w:tc>
            <w:tcPr><w:tcW w:w="900" w:type="dxa"/>
              <w:shd w:val="clear" w:color="auto" w:fill="{bg}"/>
            </w:tcPr>
            <w:p><w:r><w:rPr><w:sz w:val="18"/></w:rPr>
              <w:t>{r['load_time_ms']}ms</w:t></w:r></w:p>
          </w:tc>

          <w:tc>
            <w:tcPr><w:tcW w:w="3600" w:type="dxa"/>
              <w:shd w:val="clear" w:color="auto" w:fill="{bg}"/>
            </w:tcPr>
            <w:p><w:r><w:rPr><w:sz w:val="16"/></w:rPr>
              <w:t>{r['url']}</w:t></w:r></w:p>
            {check_lines}
            {error_line}
          </w:tc>
        </w:tr>"""

    # ── Overall status badge ──────────────────────────────────
    ov_color = "FF0000" if overall == "FAIL" else "00AA00"
    ov_bg    = "FFE0E0" if overall == "FAIL" else "E0FFE0"

    # ── Full document XML ─────────────────────────────────────
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
  xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<w:body>

  <!-- Title -->
  <w:p>
    <w:pPr><w:jc w:val="center"/><w:spacing w:after="100"/></w:pPr>
    <w:r><w:rPr><w:b/><w:sz w:val="36"/><w:color w:val="1E293B"/></w:rPr>
      <w:t>ATT Atlas UI — Daily Sanity Report</w:t></w:r>
  </w:p>

  <!-- Subtitle -->
  <w:p>
    <w:pPr><w:jc w:val="center"/><w:spacing w:after="200"/></w:pPr>
    <w:r><w:rPr><w:sz w:val="22"/><w:color w:val="64748B"/></w:rPr>
      <w:t>{run_date}  |  Completed in {elapsed}s</w:t></w:r>
  </w:p>

  <!-- Overall status -->
  <w:p>
    <w:pPr><w:jc w:val="center"/><w:spacing w:after="300"/>
      <w:shd w:val="clear" w:color="auto" w:fill="{ov_bg}"/>
    </w:pPr>
    <w:r><w:rPr><w:b/><w:sz w:val="32"/><w:color w:val="{ov_color}"/></w:rPr>
      <w:t>Overall Status: {overall}</w:t></w:r>
  </w:p>

  <!-- Summary line -->
  <w:p>
    <w:pPr><w:jc w:val="center"/><w:spacing w:after="400"/></w:pPr>
    <w:r><w:rPr><w:sz w:val="22"/></w:rPr>
      <w:t>Pages Tested: {len(results)}   |   Passed: {passed}   |   Failed: {failed}</w:t></w:r>
  </w:p>

  <!-- Section heading -->
  <w:p>
    <w:pPr><w:spacing w:after="100"/></w:pPr>
    <w:r><w:rPr><w:b/><w:sz w:val="24"/><w:color w:val="1E293B"/></w:rPr>
      <w:t>Page Results</w:t></w:r>
  </w:p>

  <!-- Table -->
  <w:tbl>
    <w:tblPr>
      <w:tblStyle w:val="TableGrid"/>
      <w:tblW w:w="7200" w:type="dxa"/>
      <w:tblBorders>
        <w:top    w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>
        <w:left   w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>
        <w:bottom w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>
        <w:right  w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>
        <w:insideH w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>
        <w:insideV w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>
      </w:tblBorders>
    </w:tblPr>

    <!-- Header row -->
    <w:tr>
      <w:trPr><w:shd w:val="clear" w:color="auto" w:fill="1E293B"/></w:trPr>
      <w:tc>
        <w:tcPr><w:tcW w:w="1800" w:type="dxa"/>
          <w:shd w:val="clear" w:color="auto" w:fill="1E293B"/></w:tcPr>
        <w:p><w:r><w:rPr><w:b/><w:color w:val="FFFFFF"/><w:sz w:val="20"/></w:rPr>
          <w:t>Page</w:t></w:r></w:p>
      </w:tc>
      <w:tc>
        <w:tcPr><w:tcW w:w="900" w:type="dxa"/>
          <w:shd w:val="clear" w:color="auto" w:fill="1E293B"/></w:tcPr>
        <w:p><w:r><w:rPr><w:b/><w:color w:val="FFFFFF"/><w:sz w:val="20"/></w:rPr>
          <w:t>Status</w:t></w:r></w:p>
      </w:tc>
      <w:tc>
        <w:tcPr><w:tcW w:w="900" w:type="dxa"/>
          <w:shd w:val="clear" w:color="auto" w:fill="1E293B"/></w:tcPr>
        <w:p><w:r><w:rPr><w:b/><w:color w:val="FFFFFF"/><w:sz w:val="20"/></w:rPr>
          <w:t>Load Time</w:t></w:r></w:p>
      </w:tc>
      <w:tc>
        <w:tcPr><w:tcW w:w="3600" w:type="dxa"/>
          <w:shd w:val="clear" w:color="auto" w:fill="1E293B"/></w:tcPr>
        <w:p><w:r><w:rPr><w:b/><w:color w:val="FFFFFF"/><w:sz w:val="20"/></w:rPr>
          <w:t>URL / Details</w:t></w:r></w:p>
      </w:tc>
    </w:tr>

    {table_rows}

  </w:tbl>

  <!-- Footer -->
  <w:p><w:pPr><w:spacing w:before="400"/></w:pPr>
    <w:r><w:rPr><w:sz w:val="16"/><w:color w:val="94A3B8"/></w:rPr>
      <w:t>Generated by ATT Atlas UI Sanity Automation — {run_date}</w:t>
    </w:r>
  </w:p>

  <w:sectPr>
    <w:pgSz w:w="12240" w:h="15840"/>
    <w:pgMar w:top="720" w:right="720" w:bottom="720" w:left="720"/>
  </w:sectPr>

</w:body>
</w:document>"""

    # ── Required docx supporting files ───────────────────────
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml"  ContentType="application/xml"/>
  <Override PartName="/word/document.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
    Target="word/document.xml"/>
</Relationships>"""

    word_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
</Relationships>"""

    # ── Write .docx (it's just a zip file) ───────────────────
    with zipfile.ZipFile(str(docx_path), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels",         rels)
        zf.writestr("word/document.xml",   document_xml)
        zf.writestr("word/_rels/document.xml.rels", word_rels)

    print(f"[WORD REPORT] Saved → {docx_path}")
    return docx_path


# ── Quick test ────────────────────────────────────────────────
if __name__ == "__main__":
    # Sample test data
    sample = [
        {"name": "Home",      "url": "/",        "status": "PASS", "load_time_ms": 820,  "checks": [{"selector": "body",   "status": "PASS", "detail": "Visible"}], "error": None, "redirected_to_login": False},
        {"name": "Job",       "url": "/job",      "status": "PASS", "load_time_ms": 1100, "checks": [{"selector": "h1",     "status": "PASS", "detail": "Visible"}], "error": None, "redirected_to_login": False},
        {"name": "Customer",  "url": "/customer", "status": "FAIL", "load_time_ms": 500,  "checks": [{"selector": ".title", "status": "FAIL", "detail": "Not found"}], "error": "Element not found", "redirected_to_login": False},
    ]
    make_docx(sample, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 12.3, "ATT Atlas UI")
    print("Test report generated in reports/ folder!")
