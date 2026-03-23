/**
 * Generate ATT Sanity Report as DOCX with screenshots
 * Usage: node generate_report.js <results_json_path>
 */

const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  ImageRun, HeadingLevel, AlignmentType, BorderStyle, WidthType,
  ShadingType, PageBreak, VerticalAlign
} = require('docx');
const fs   = require('fs');
const path = require('path');

const resultsPath = process.argv[2] || 'sanity_results.json';
const outputPath  = process.argv[3] || 'reports/att_sanity_report.docx';

if (!fs.existsSync(resultsPath)) {
  console.error(`Results file not found: ${resultsPath}`);
  process.exit(1);
}

fs.mkdirSync(path.dirname(outputPath), { recursive: true });

const data    = JSON.parse(fs.readFileSync(resultsPath, 'utf8'));
const results = data.results;
const runDate = data.run_date;
const elapsed = data.elapsed;
const appName = data.app_name;

const passed  = results.filter(r => r.status === 'PASS').length;
const failed  = results.filter(r => r.status === 'FAIL').length;
const overall = failed === 0 ? 'PASS' : 'FAIL';

// ── Colours ──────────────────────────────────────────────
const GREEN  = '16a34a';
const RED    = 'dc2626';
const BLUE   = '1e3a5f';
const LGRAY  = 'F1F5F9';
const MGRAY  = 'E2E8F0';
const WHITE  = 'FFFFFF';
const PASS_BG = 'DCFCE7';
const FAIL_BG = 'FEE2E2';

// ── Helpers ───────────────────────────────────────────────
const border = (color = 'CCCCCC') => ({
  style: BorderStyle.SINGLE, size: 1, color
});
const allBorders = (color = 'CCCCCC') => ({
  top: border(color), bottom: border(color),
  left: border(color), right: border(color)
});
const cellMargins = { top: 100, bottom: 100, left: 140, right: 140 };

function boldText(text, color = '000000', size = 22) {
  return new TextRun({ text, bold: true, color, size, font: 'Arial' });
}
function normalText(text, color = '333333', size = 20) {
  return new TextRun({ text, color, size, font: 'Arial' });
}
function para(children, spacing = { before: 60, after: 60 }, alignment = AlignmentType.LEFT) {
  return new Paragraph({ children, spacing, alignment });
}

// ── Cover / Header section ────────────────────────────────
function makeCoverSection() {
  const children = [];

  // Title bar (dark blue)
  children.push(new Paragraph({
    children: [
      new TextRun({ text: `${appName} — Daily Sanity Report`, bold: true, color: WHITE, size: 36, font: 'Arial' })
    ],
    shading: { fill: BLUE, type: ShadingType.CLEAR },
    spacing: { before: 0, after: 0 },
    alignment: AlignmentType.CENTER,
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: '2E75B6', space: 1 } }
  }));

  children.push(para([normalText('')]));

  // Run info table
  children.push(new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [4680, 4680],
    rows: [
      new TableRow({ children: [
        new TableCell({ borders: allBorders(), margins: cellMargins, shading: { fill: LGRAY, type: ShadingType.CLEAR },
          children: [para([boldText('Run Date')])] }),
        new TableCell({ borders: allBorders(), margins: cellMargins,
          children: [para([normalText(runDate)])] })
      ]}),
      new TableRow({ children: [
        new TableCell({ borders: allBorders(), margins: cellMargins, shading: { fill: LGRAY, type: ShadingType.CLEAR },
          children: [para([boldText('Duration')])] }),
        new TableCell({ borders: allBorders(), margins: cellMargins,
          children: [para([normalText(`${elapsed} seconds`)])] })
      ]}),
      new TableRow({ children: [
        new TableCell({ borders: allBorders(), margins: cellMargins, shading: { fill: LGRAY, type: ShadingType.CLEAR },
          children: [para([boldText('Total Pages')])] }),
        new TableCell({ borders: allBorders(), margins: cellMargins,
          children: [para([normalText(`${results.length}`)])] })
      ]}),
      new TableRow({ children: [
        new TableCell({ borders: allBorders(), margins: cellMargins, shading: { fill: LGRAY, type: ShadingType.CLEAR },
          children: [para([boldText('Overall Status')])] }),
        new TableCell({ borders: allBorders(), margins: cellMargins,
          shading: { fill: overall === 'PASS' ? PASS_BG : FAIL_BG, type: ShadingType.CLEAR },
          children: [para([boldText(overall, overall === 'PASS' ? GREEN : RED, 24)])] })
      ]}),
      new TableRow({ children: [
        new TableCell({ borders: allBorders(), margins: cellMargins, shading: { fill: LGRAY, type: ShadingType.CLEAR },
          children: [para([boldText('Passed')])] }),
        new TableCell({ borders: allBorders(), margins: cellMargins, shading: { fill: PASS_BG, type: ShadingType.CLEAR },
          children: [para([boldText(`${passed}`, GREEN)])] })
      ]}),
      new TableRow({ children: [
        new TableCell({ borders: allBorders(), margins: cellMargins, shading: { fill: LGRAY, type: ShadingType.CLEAR },
          children: [para([boldText('Failed')])] }),
        new TableCell({ borders: allBorders(), margins: cellMargins, shading: { fill: failed > 0 ? FAIL_BG : PASS_BG, type: ShadingType.CLEAR },
          children: [para([boldText(`${failed}`, failed > 0 ? RED : GREEN)])] })
      ]})
    ]
  }));

  return children;
}

// ── Summary table ─────────────────────────────────────────
function makeSummaryTable() {
  const children = [];

  children.push(new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text: 'Test Results Summary', bold: true, font: 'Arial', size: 28, color: BLUE })]
  }));

  // Header row
  const headerRow = new TableRow({
    tableHeader: true,
    children: ['Page', 'Status', 'URL', 'Load Time', 'Details'].map((h, i) => {
      const widths = [1500, 900, 3000, 900, 3060];
      return new TableCell({
        borders: allBorders('2E75B6'),
        margins: cellMargins,
        width: { size: widths[i], type: WidthType.DXA },
        shading: { fill: BLUE, type: ShadingType.CLEAR },
        verticalAlign: VerticalAlign.CENTER,
        children: [para([boldText(h, WHITE, 18)])]
      });
    })
  });

  const dataRows = results.map(r => {
    const isPass  = r.status === 'PASS';
    const bg      = isPass ? PASS_BG : FAIL_BG;
    const stColor = isPass ? GREEN : RED;

    const detailLines = [];
    (r.checks || []).forEach(c => {
      const icon = c.status === 'PASS' ? '✓' : '⚠';
      detailLines.push(`${icon} ${c.selector} — ${c.detail}`);
    });
    if (r.error)              detailLines.push(`Error: ${r.error}`);
    if (r.redirected_to_login) detailLines.push('Session expired!');
    const detailText = detailLines.join('\n') || '—';

    return new TableRow({ children: [
      new TableCell({ borders: allBorders(), margins: cellMargins, shading: { fill: bg, type: ShadingType.CLEAR },
        children: [para([boldText(r.name, '1e293b', 18)])] }),
      new TableCell({ borders: allBorders(), margins: cellMargins, shading: { fill: bg, type: ShadingType.CLEAR },
        children: [para([boldText(r.status, stColor, 18)], {}, AlignmentType.CENTER)] }),
      new TableCell({ borders: allBorders(), margins: cellMargins, shading: { fill: bg, type: ShadingType.CLEAR },
        children: [para([new TextRun({ text: r.url, size: 16, color: '334155', font: 'Arial' })])] }),
      new TableCell({ borders: allBorders(), margins: cellMargins, shading: { fill: bg, type: ShadingType.CLEAR },
        children: [para([normalText(`${r.load_time_ms}ms`, '334155', 18)], {}, AlignmentType.CENTER)] }),
      new TableCell({ borders: allBorders(), margins: cellMargins, shading: { fill: bg, type: ShadingType.CLEAR },
        children: [para([new TextRun({ text: detailText, size: 16, color: '475569', font: 'Arial' })])] })
    ]});
  });

  children.push(new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [1500, 900, 3000, 900, 3060],
    rows: [headerRow, ...dataRows]
  }));

  return children;
}

// ── Screenshot pages ───────────────────────────────────────
function makeScreenshotPages() {
  const children = [];

  children.push(new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text: 'Page Screenshots', bold: true, font: 'Arial', size: 28, color: BLUE })]
  }));

  results.forEach((r, idx) => {
    const ssPath = r.screenshot;

    // Page heading
    const isPass  = r.status === 'PASS';
    const stColor = isPass ? GREEN : RED;

    children.push(new Paragraph({
      heading: HeadingLevel.HEADING_2,
      children: [
        new TextRun({ text: `${idx + 1}. ${r.name}  `, bold: true, font: 'Arial', size: 24, color: BLUE }),
        new TextRun({ text: `[${r.status}]`, bold: true, font: 'Arial', size: 22, color: stColor })
      ],
      spacing: { before: 240, after: 80 }
    }));

    children.push(para([
      new TextRun({ text: 'URL: ', bold: true, font: 'Arial', size: 18, color: '475569' }),
      new TextRun({ text: r.url, font: 'Arial', size: 18, color: '2563eb' })
    ], { before: 0, after: 60 }));

    children.push(para([
      new TextRun({ text: 'Load time: ', bold: true, font: 'Arial', size: 18, color: '475569' }),
      new TextRun({ text: `${r.load_time_ms}ms`, font: 'Arial', size: 18, color: '334155' })
    ], { before: 0, after: 120 }));

    // Screenshot
    if (ssPath && fs.existsSync(ssPath)) {
      try {
        const imgBuffer = fs.readFileSync(ssPath);
        const ext = path.extname(ssPath).toLowerCase().replace('.', '');
        const typeMap = { png: 'png', jpg: 'jpg', jpeg: 'jpg' };
        const imgType = typeMap[ext] || 'png';

        children.push(new Paragraph({
          children: [
            new ImageRun({
              data: imgBuffer,
              transformation: { width: 620, height: 380 },
              type: imgType
            })
          ],
          spacing: { before: 60, after: 120 },
          alignment: AlignmentType.CENTER
        }));
      } catch (e) {
        children.push(para([normalText(`[Screenshot error: ${e.message}]`, RED)]));
      }
    } else {
      children.push(para([normalText('[No screenshot available]', '94a3b8')]));
    }

    // Divider line
    children.push(new Paragraph({
      children: [],
      border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: MGRAY, space: 1 } },
      spacing: { before: 60, after: 240 }
    }));
  });

  return children;
}

// ── Build document ────────────────────────────────────────
const allChildren = [
  ...makeCoverSection(),
  para([normalText('')]),
  ...makeSummaryTable(),
  new Paragraph({ children: [new PageBreak()] }),
  ...makeScreenshotPages()
];

const doc = new Document({
  styles: {
    default: { document: { run: { font: 'Arial', size: 20 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 28, bold: true, font: 'Arial', color: BLUE },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 24, bold: true, font: 'Arial', color: BLUE },
        paragraph: { spacing: { before: 180, after: 80 }, outlineLevel: 1 } }
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 }
      }
    },
    children: allChildren
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outputPath, buffer);
  console.log(`DOCX report saved: ${outputPath}`);
}).catch(err => {
  console.error('Error generating DOCX:', err);
  process.exit(1);
});
