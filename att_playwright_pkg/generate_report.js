const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  ImageRun, HeadingLevel, AlignmentType, BorderStyle, WidthType,
  ShadingType, PageBreak, VerticalAlign
} = require('docx');
const fs   = require('fs');
const path = require('path');

const data    = JSON.parse(fs.readFileSync(process.argv[2]));
const outPath = process.argv[3];
const { results, run_date, secs } = data;

const passed  = results.filter(r => r.status === 'PASS').length;
const failed  = results.length - passed;
const overall = failed === 0 ? 'PASS' : 'FAIL';

// Colours
const NAVY = '1e3a5f', GREEN = '16a34a', RED = 'dc2626';
const WHITE = 'FFFFFF', LGRAY = 'F1F5F9';
const PASS_BG = 'DCFCE7', FAIL_BG = 'FEE2E2';

// Helpers
const bdr  = (c='CCCCCC') => ({ style: BorderStyle.SINGLE, size:1, color:c });
const allB = (c='CCCCCC') => ({ top:bdr(c), bottom:bdr(c), left:bdr(c), right:bdr(c) });
const mar  = { top:100, bottom:100, left:140, right:140 };
const t    = (text, opt={}) => new TextRun({ text, font:'Arial', size:20, ...opt });
const p    = (children, opts={}) => new Paragraph({ children, spacing:{before:60,after:60}, ...opts });
const cell = (children, opt={}) => new TableCell({ borders:allB(), margins:mar, children, ...opt });

// Cover summary table
function coverTable() {
  const ov  = overall === 'PASS' ? PASS_BG : FAIL_BG;
  const ovc = overall === 'PASS' ? GREEN   : RED;
  const rows = [
    ['Run Date',    run_date,            null],
    ['Duration',    `${secs} seconds`,   null],
    ['Total Pages', `${results.length}`, null],
    ['Passed',      `${passed}`,         PASS_BG],
    ['Failed',      `${failed}`,         failed > 0 ? FAIL_BG : PASS_BG],
    ['Status',      overall,             ov],
  ];
  return new Table({
    width: { size:9360, type:WidthType.DXA },
    columnWidths: [2800, 6560],
    rows: rows.map(([label, value, bg]) => new TableRow({ children: [
      cell([p([t(label, {bold:true})])], {
        shading:{fill:LGRAY, type:ShadingType.CLEAR},
        width:{size:2800, type:WidthType.DXA} }),
      cell([p([t(value, label==='Status' ? {bold:true, color:ovc, size:24} : {})])], {
        shading: bg ? {fill:bg, type:ShadingType.CLEAR} : {},
        width:{size:6560, type:WidthType.DXA} })
    ]}))
  });
}

// Results summary table
function summaryTable() {
  const cols  = ['Page','Status','URL','Load Time','Note'];
  const widths= [1600, 900, 3100, 900, 2860];
  const header = new TableRow({ tableHeader:true, children:
    cols.map((h,i) => new TableCell({
      borders:allB(NAVY), margins:mar, width:{size:widths[i], type:WidthType.DXA},
      shading:{fill:NAVY, type:ShadingType.CLEAR},
      children:[p([t(h, {bold:true, color:WHITE, size:18})])]
    }))
  });
  const dataRows = results.map(r => {
    const bg = r.status==='PASS' ? PASS_BG : FAIL_BG;
    const fc = r.status==='PASS' ? GREEN   : RED;
    return new TableRow({ children:
      [r.name, r.status, r.url, `${r.time_ms}ms`, r.note||''].map((val,i) =>
        new TableCell({
          borders:allB(), margins:mar, width:{size:widths[i], type:WidthType.DXA},
          shading:{fill:bg, type:ShadingType.CLEAR},
          children:[p([t(val, i===1 ? {bold:true, color:fc, size:18} : {size:i===2?16:18, color:'334155'})])]
        })
      )
    });
  });
  return new Table({ width:{size:9360, type:WidthType.DXA}, columnWidths:widths,
    rows:[header, ...dataRows] });
}

// Screenshot section
function screenshotPages() {
  const children = [];
  results.forEach((r, i) => {
    const fc = r.status==='PASS' ? GREEN : RED;

    children.push(new Paragraph({
      children:[
        t(`${i+1}. ${r.name}   `, {bold:true, size:24, color:NAVY}),
        t(`[${r.status}]`,        {bold:true, size:20, color:fc})
      ],
      spacing:{before:180, after:60}
    }));
    children.push(p([t(`URL: ${r.url}  |  Load: ${r.time_ms}ms`, {size:17, color:'475569'})],
      {spacing:{before:0, after:100}}));

    if (r.screenshot && fs.existsSync(r.screenshot)) {
      try {
        children.push(new Paragraph({
          children:[new ImageRun({
            data: fs.readFileSync(r.screenshot),
            transformation:{width:620, height:350},
            type:'png'
          })],
          alignment: AlignmentType.CENTER,
          spacing:{before:40, after:140}
        }));
      } catch(e) {
        children.push(p([t(`[Screenshot error: ${e.message}]`, {color:RED})]));
      }
    } else {
      children.push(p([t('[No screenshot available]', {color:'94a3b8'})]));
    }

    // Divider
    children.push(new Paragraph({
      children:[],
      border:{ bottom:{style:BorderStyle.SINGLE, size:4, color:'E2E8F0', space:1} },
      spacing:{before:40, after:180}
    }));
  });
  return children;
}

// Build document
const doc = new Document({
  styles:{
    default:{ document:{ run:{ font:'Arial', size:20 } } },
    paragraphStyles:[
      { id:'Heading1', name:'Heading 1', basedOn:'Normal', next:'Normal', quickFormat:true,
        run:{size:28, bold:true, font:'Arial', color:NAVY},
        paragraph:{spacing:{before:240, after:120}, outlineLevel:0} }
    ]
  },
  sections:[{
    properties:{ page:{
      size:{width:12240, height:15840},
      margin:{top:1080, right:1080, bottom:1080, left:1080}
    }},
    children:[
      // Title bar
      new Paragraph({
        children:[t('ATT Atlas UI — Daily Sanity Report', {bold:true, size:34, color:WHITE})],
        shading:{fill:NAVY, type:ShadingType.CLEAR},
        alignment:AlignmentType.CENTER,
        spacing:{before:0, after:0}
      }),
      p([t('')]),
      coverTable(),
      p([t('')]),
      // Summary
      new Paragraph({ heading:HeadingLevel.HEADING_1,
        children:[t('Results Summary', {bold:true, size:28, color:NAVY, font:'Arial'})] }),
      summaryTable(),
      new Paragraph({ children:[new PageBreak()] }),
      // Screenshots
      new Paragraph({ heading:HeadingLevel.HEADING_1,
        children:[t('Page Screenshots', {bold:true, size:28, color:NAVY, font:'Arial'})] }),
      ...screenshotPages()
    ]
  }]
});

fs.mkdirSync(path.dirname(outPath), { recursive:true });
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outPath, buf);
  console.log(`DOCX saved: ${outPath}`);
});
