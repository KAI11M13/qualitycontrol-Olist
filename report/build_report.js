// 生成专题分析报告：node report/build_report.js
//   report/品控专题分析报告.docx   Word 版（A4）
//   docs/03_专题分析报告.md        Markdown 版（GitHub 直接阅读）
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, ImageRun, Footer, PageNumber, LevelFormat,
} = require("docx");
const { meta, blocks } = require("./report_content");

const ROOT = path.resolve(__dirname, "..");
const TEAL = "0E6E6E", INK = "17232B", MUTED = "5E6B72", TINT = "E4F0EF", LINE = "D5DADB";
const FONT = { ascii: "Arial", hAnsi: "Arial", eastAsia: "Microsoft YaHei", cs: "Arial" };
const CONTENT_W = 9026; // A4 宽 11906 − 左右边距 1440×2

const run = (text, o = {}) => new TextRun({ text, font: FONT, ...o });
const para = (text, o = {}) => new Paragraph({ children: [run(text, o.run || {})], spacing: { after: 120, line: 360 }, ...o.p });

function imageSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20), buf: b };   // PNG IHDR
}

function table(b) {
  const border = { style: BorderStyle.SINGLE, size: 4, color: LINE };
  const borders = { top: border, bottom: border, left: border, right: border };
  const total = b.widths.reduce((a, x) => a + x, 0);
  const widths = b.widths.map(w => Math.round(w * CONTENT_W / total));
  widths[widths.length - 1] += CONTENT_W - widths.reduce((a, x) => a + x, 0);
  const cell = (t, i, head, last) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA }, borders,
    shading: { type: ShadingType.CLEAR, color: "auto", fill: head ? TEAL : (last ? TINT : "FFFFFF") },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: [run(t, { bold: head || last, color: head ? "FFFFFF" : INK, size: 19 })] })],
  });
  const lastIsTotal = b.rows.length && b.rows[b.rows.length - 1][0] === "合计";
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: widths,
    rows: [
      new TableRow({ tableHeader: true, children: b.head.map((t, i) => cell(t, i, true, false)) }),
      ...b.rows.map((r, ri) => new TableRow({ children: r.map((t, i) => cell(t, i, false, lastIsTotal && ri === b.rows.length - 1)) })),
    ],
  });
}

function callout(items) {
  const border = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: [CONTENT_W],
    rows: [new TableRow({ children: [new TableCell({
      width: { size: CONTENT_W, type: WidthType.DXA },
      borders: { top: border, bottom: border, left: border, right: border },
      shading: { type: ShadingType.CLEAR, color: "auto", fill: TINT },
      margins: { top: 200, bottom: 200, left: 260, right: 260 },
      children: items.map((t, i) => new Paragraph({
        numbering: { reference: "nums", level: 0 },
        spacing: { after: i === items.length - 1 ? 0 : 140, line: 340 },
        children: [run(t, { size: 21 })],
      })),
    })] })],
  });
}

const children = [];
children.push(new Paragraph({ spacing: { before: 600, after: 120 }, children: [run(meta.title, { bold: true, size: 48, color: INK })] }));
children.push(new Paragraph({ spacing: { after: 300 }, children: [run(meta.subtitle, { size: 26, color: TEAL })] }));
meta.info.forEach(([k, v]) => children.push(new Paragraph({
  spacing: { after: 60 }, children: [run(k + "：", { bold: true, size: 19, color: MUTED }), run(v, { size: 19, color: MUTED })],
})));
children.push(new Paragraph({ spacing: { after: 240 }, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: LINE, space: 8 } }, children: [] }));

for (const b of blocks) {
  if (b.t === "h1") children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [run(b.text)] }));
  else if (b.t === "h2") children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: [run(b.text)] }));
  else if (b.t === "p") children.push(para(b.text));
  else if (b.t === "bullets") b.items.forEach(t => children.push(new Paragraph({
    numbering: { reference: "bullets", level: 0 }, spacing: { after: 80, line: 340 }, children: [run(t)],
  })));
  else if (b.t === "callout") { children.push(callout(b.items)); children.push(para("")); }
  else if (b.t === "table") { children.push(table(b)); children.push(new Paragraph({ spacing: { after: 160 }, children: [] })); }
  else if (b.t === "img") {
    const { w, h, buf } = imageSize(b.path);
    const width = Math.round(b.w / 2.54 * 96);        // cm → px（96 dpi）
    children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 },
      children: [new ImageRun({ type: "png", data: buf, transformation: { width, height: Math.round(width * h / w) },
        altText: { title: b.caption, description: b.caption, name: path.basename(b.path) } })] }));
    children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [run(b.caption, { size: 18, color: MUTED })] }));
  }
}

const doc = new Document({
  creator: "品控数据分析项目", title: meta.title,
  styles: {
    default: { document: { run: { font: FONT, size: 21, color: INK } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, color: TEAL, font: FONT }, paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: INK, font: FONT }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 440, hanging: 260 } } } }] },
    { reference: "nums", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 400, hanging: 300 } }, run: { bold: true, color: TEAL } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1300, bottom: 1300, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [
      run("电商品控专题分析报告　", { size: 16, color: MUTED }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: MUTED, font: FONT }),
    ] })] }) },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  const out = path.join(__dirname, "品控专题分析报告.docx");
  fs.writeFileSync(out, buf);
  console.log("写入", out);
});

// ---------------------------------------------------------------- Markdown 版
const md = [`# 03 专题分析报告：${meta.title}`, "", `> ${meta.subtitle}`, ">",
  ...meta.info.map(([k, v]) => `> **${k}**：${v}  `), "", "> Word 版：[`report/品控专题分析报告.docx`](../report/品控专题分析报告.docx)", ""];
for (const b of blocks) {
  if (b.t === "h1") md.push(`## ${b.text}`, "");
  else if (b.t === "h2") md.push(`### ${b.text}`, "");
  else if (b.t === "p") md.push(b.text, "");
  else if (b.t === "bullets") md.push(...b.items.map(t => `- ${t}`), "");
  else if (b.t === "callout") md.push(...b.items.map((t, i) => `${i + 1}. **${t.split("：")[0]}**：${t.split("：").slice(1).join("：")}`), "");
  else if (b.t === "table") md.push(`| ${b.head.join(" | ")} |`, `|${"---|".repeat(b.head.length)}`, ...b.rows.map(r => `| ${r.join(" | ")} |`), "");
  else if (b.t === "img") md.push(`![${b.caption}](${path.relative(path.join(ROOT, "docs"), b.path)})`, "", `*${b.caption}*`, "");
}
fs.writeFileSync(path.join(ROOT, "docs", "03_专题分析报告.md"), md.join("\n"));
console.log("写入 docs/03_专题分析报告.md");
