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

// ── Colours ───────────────────────────────────────────────
const NAVY    = '1e3a5f';
const GREEN   = '16a34a';
const RED     = 'dc2626';
const WHITE   = 'FFFFFF';
const LGRAY   = 'F1F5F9';
const PASS_BG = 'DCFCE7';
const FAIL_BG = 'FEE2E2';

// ── Helpers ───────────────────────────────────────────────
const bdr = (c='CCCCCC') => ({ style: BorderStyle.SINGLE, size: 1, color: c });
const allB = (c='CCCCCC') => ({ top:bdr(c), bottom:bdr(c), left:bdr(c), right:bdr(c) });
const mar  = { top:100, bottom:100, left:140, right:140 };
const txt  = (t, opt={}) => new TextRun({ text:t, font:'Arial', size:20, ...opt });
const p    = (children, opts={}) => new Paragraph({ children, spacing:{before:60,after:60}, ...opts });
const cell = (children, opt={}) => new TableCell({ borders:allB(), margins:mar, children, ...opt });

// ── Cover table ───────────────────────────────────────────
function coverTable() {
  const ov   = overall === 'PASS' ? PASS_BG : FAIL_BG;
  const ovc  = overall === 'PASS' ? GREEN   : RED;
  const rows = [
    ['Run Date',    run_date,             null],
    ['Duration',    `${secs} seconds`,    null],
    ['Total Pages', `${results.length}`,  null],
    ['Passed',      `${passed}`,          PASS_BG],
    ['Failed',      `${failed}`,          failed > 0 ? FAIL_BG : PASS_BG],
    ['Status',      overall,              ov],
  ];
  return new Table({
    width: { size:9360, type:WidthType.DXA },
    columnWidths: [3000, 6360],
    rows: rows.map(([label, value, bg]) => new TableRow({ children: [
      cell([p([txt(label, {bold:true})])], { shading:{fill:LGRAY, type:ShadingType.CLEAR}, width:{size:3000,type:WidthType.DXA} }),
      cell([p([txt(value, label==='Status' ? {bold:true,color:ovc,size:24} : {})])],
        { shading: bg ? {fill:bg, type:ShadingType.CLEAR} : {}, width:{size:6360,type:WidthType.DXA} })
    ]}))
  });
}

// ── Summary table ─────────────────────────────────────────
function summaryTable() {
  const header = new TableRow({ tableHeader:true, children:
    ['Page','Status','URL','Load Time','Note'].map((h,i) => {
      const w = [1600,900,3200,900,2760][i];
      return new TableCell({ borders:allB(NAVY), margins:mar, width:{size:w,type:WidthType.DXA},
        shading:{fill:NAVY, type:ShadingType.CLEAR},
        children:[p([txt(h, {bold:true,color:WHITE,size:18})])] });
    })
  });
  const dataRows = results.map(r => {
    const bg  = r.status==='PASS' ? PASS_BG : FAIL_BG;
    const fc  = r.status==='PASS' ? GREEN   : RED;
    const w   = [1600,900,3200,900,2760];
    return new TableRow({ children:
      [r.name, r.status, r.url, `${r.time_ms}ms`, r.note||''].map((val,i) =>
        new TableCell({ borders:allB(), margins:mar, width:{size:w[i],type:WidthType.DXA},
          shading:{fill:bg, type:ShadingType.CLEAR},
          children:[p([txt(val, i===1 ? {bold:true,color:fc,size:18} : {size:i===2?16:18,color:'334155'})])] })
      )
    });
  });
  return new Table({ width:{size:9360,type:WidthType.DXA}, columnWidths:[1600,900,3200,900,2760],
    rows:[header,...dataRows] });
}

// ── Screenshot pages ──────────────────────────────────────
function screenshotPages() {
  const children = [];
  results.forEach((r, i) => {
    const fc = r.status==='PASS' ? GREEN : RED;
    children.push(new Paragraph({
      children: [
        txt(`${i+1}. ${r.name}   `, {bold:true, size:26, color:NAVY}),
        txt(`[${r.status}]`, {bold:true, size:22, color:fc})
      ],
      spacing:{before:200, after:80}
    }));
    children.push(p([txt(`URL: ${r.url}`, {size:18,color:'475569'})]));
    children.push(p([txt(`Load time: ${r.time_ms}ms  |  ${r.note}`, {size:18,color:'475569'})],
      {spacing:{before:0,after:120}}));

    if (r.screenshot && fs.existsSync(r.screenshot)) {
      try {
        children.push(new Paragraph({
          children: [new ImageRun({
            data: fs.readFileSync(r.screenshot),
            transformation: { width:620, height:350 },
            type: 'png'
          })],
          alignment: AlignmentType.CENTER,
          spacing: {before:60, after:160}
        }));
      } catch(e) {
        children.push(p([txt(`[Screenshot error: ${e.message}]`, {color:RED})]));
      }
    } else {
      children.push(p([txt('[No screenshot]', {color:'94a3b8'})]));
    }

    // Divider
    children.push(new Paragraph({
      children:[],
      border:{ bottom:{style:BorderStyle.SINGLE, size:4, color:'E2E8F0', space:1} },
      spacing:{before:40, after:200}
    }));
  });
  return children;
}

// ── Build document ────────────────────────────────────────
const doc = new Document({
  styles: {
    default: { document:{ run:{ font:'Arial', size:20 } } },
    paragraphStyles: [
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
      // Cover
      new Paragraph({ children:[txt('ATT Atlas UI — Daily Sanity Report',
        {bold:true, size:36, color:WHITE})],
        shading:{fill:NAVY, type:ShadingType.CLEAR},
        alignment:AlignmentType.CENTER,
        spacing:{before:0,after:0} }),
      p([txt('')]),
      coverTable(),
      p([txt('')]),

      // Summary
      new Paragraph({ heading:HeadingLevel.HEADING_1,
        children:[txt('Results Summary', {bold:true,size:28,color:NAVY,font:'Arial'})] }),
      summaryTable(),
      new Paragraph({ children:[new PageBreak()] }),

      // Screenshots
      new Paragraph({ heading:HeadingLevel.HEADING_1,
        children:[txt('Page Screenshots', {bold:true,size:28,color:NAVY,font:'Arial'})] }),
      ...screenshotPages()
    ]
  }]
});

fs.mkdirSync(path.dirname(outPath), { recursive:true });
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outPath, buf);
  console.log(`DOCX saved: ${outPath}`);
});
