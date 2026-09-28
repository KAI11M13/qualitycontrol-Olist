// 两份 PPT（完整版 build_deck.js / 精简版 build_deck_short.js）共用的设计系统与绘图函数
// 每一页内容页的结构相同：模块标签 → 标题（结论） → 关键术语（名称：定义） → 依据（图表与数字） → 动作
const pptxgen = require("pptxgenjs");

// 配色：白底 + 玫红 #E1006C（主色）+ 95 度黑 #161418；与看板、图表（scripts/viz_style.py）一致
const C = {
  ink: "161418", pink: "E1006C", pinkMid: "F08CB8", pinkTint: "FCE6F0", pinkDark: "8C0044",
  gray: "CDC7CF", grayLight: "F6F4F6", line: "E9E6EA", muted: "6E6872", white: "FFFFFF",
  amber: "E8A317", green: "2E8B57", onInk: "CFC8CD", onInkMuted: "948D93",
};
const FONT = "Microsoft YaHei";
const W = 13.333, H = 7.5, MX = 0.6;
const BODY_TOP = 2.05, BODY_BOTTOM = 6.35;     // 依据区域的上下边界（下方留给"动作"条）
// 数字格式（docs/00_术语与口径.md 第 5 节）：同一类数字在讲稿、PPT、报告里写法完全一致
const F = {
  qc: v => (v * 100).toFixed(2) + "%",                                  // 品质客诉率与结果指标（假货客诉率除外）
  fake: v => (v * 1e4).toFixed(1) + " 单/万单",                          // 假货客诉率
  share: v => (v * 100).toFixed(1) + "%",                               // 其他比率与占比
  pp: v => (v >= 0 ? "+" : "−") + Math.abs(v * 100).toFixed(2) + "pp",  // 百分点
  times: v => v.toFixed(1) + " 倍",                                     // 倍数
  z: v => v.toFixed(2),
  p: v => (v < 0.0001 ? "p < 0.0001" : v < 0.01 ? "p < 0.01" : "p = " + v.toFixed(2)),
  int: v => Math.round(v).toLocaleString("en-US"),                      // 订单数、商家数
};
// 图表的月份标签：每年第一个月写 "2017-01"，其余只写月份 "02"
const monthLabels = ms => ms.map((m, i) => (i === 0 || m.endsWith("-01") ? m : m.slice(5)));
const DATA_NOTE = "数据：Olist 巴西电商公开数据（脱敏真实订单），下单月 2017-01 至 2018-08";

const axis = {
  catAxisLabelColor: C.muted, valAxisLabelColor: C.muted, catAxisLabelFontSize: 10, valAxisLabelFontSize: 10,
  catAxisLabelFontFace: FONT, valAxisLabelFontFace: FONT, valGridLine: { color: C.line, size: 0.5 },
  catGridLine: { style: "none" }, catAxisLineColor: C.gray, valAxisLineShow: false, legendFontFace: FONT,
  titleFontFace: FONT, dataLabelFontFace: FONT,
};

function createDeck(title) {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.author = "品控数据分析项目";
  pres.title = title;
  pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

  let pageNo = 0;
  const nextPage = () => ++pageNo;
  function text(slide, t, o) {
    slide.addText(t, Object.assign({ fontFace: FONT, color: C.ink, isTextBox: true, margin: 0, valign: "top" }, o));
  }
  // mark：圆形徽标里的字（模块编号或部分序号）；label：徽标右侧的模块名
  // term：[术语, 定义]，显示在标题下方；action：页面底部的"动作"
  function contentSlide({ mark, label, title, term, action }) {
    const s = pres.addSlide();
    nextPage();
    s.background = { color: C.white };
    s.addShape(pres.shapes.OVAL, { x: MX, y: 0.42, w: 0.3, h: 0.3, fill: { color: mark ? C.pink : C.gray }, line: { color: mark ? C.pink : C.gray } });
    text(s, mark ? String(mark) : "·", { x: MX, y: 0.42, w: 0.3, h: 0.3, fontSize: 11, bold: true, color: C.white, align: "center", valign: "middle" });
    text(s, label, { x: MX + 0.42, y: 0.42, w: 8, h: 0.3, fontSize: 11, color: C.pink, bold: true, valign: "middle" });
    text(s, title, { x: MX, y: 0.8, w: W - 2 * MX, h: 0.62, fontSize: 26, bold: true, valign: "middle", fit: "shrink" });
    if (term) {
      s.addText([
        { text: "关键术语　", options: { bold: true, color: C.pink } },
        { text: term[0], options: { bold: true, color: C.ink } },
        { text: "：" + term[1], options: { color: C.muted } },
      ], { x: MX, y: 1.47, w: W - 2 * MX, h: 0.42, fontFace: FONT, fontSize: 12.5, isTextBox: true, margin: 0, valign: "middle", fit: "shrink" });
    }
    if (action) {
      s.addShape(pres.shapes.RECTANGLE, { x: MX, y: 6.48, w: W - 2 * MX, h: 0.42, fill: { color: C.pinkTint }, line: { color: C.pinkTint } });
      s.addShape(pres.shapes.RECTANGLE, { x: MX, y: 6.48, w: 0.06, h: 0.42, fill: { color: C.pink }, line: { color: C.pink } });
      s.addText([
        { text: "动作　", options: { bold: true, color: C.pink } },
        { text: action, options: { color: C.ink } },
      ], { x: MX + 0.2, y: 6.48, w: W - 2 * MX - 0.3, h: 0.42, fontFace: FONT, fontSize: 12, isTextBox: true, margin: 0, valign: "middle", fit: "shrink" });
    }
    text(s, DATA_NOTE, { x: MX, y: H - 0.42, w: 9, h: 0.25, fontSize: 9, color: C.muted, valign: "middle" });
    text(s, String(pageNo), { x: W - MX - 0.6, y: H - 0.42, w: 0.6, h: 0.25, fontSize: 9, color: C.muted, align: "right", valign: "middle" });
    return s;
  }
  function card(s, x, y, w, h, fill = C.grayLight) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: fill } });
  }
  // 大数字 + 说明（说明写清楚数字的定义与范围）
  function stat(s, x, y, w, big, label, color = C.pink, bigSize = 30, labelH = 0.6) {
    text(s, big, { x, y, w, h: 0.58, fontSize: bigSize, bold: true, color, valign: "bottom", fit: "shrink" });
    text(s, label, { x, y: y + 0.62, w, h: labelH, fontSize: 11, color: C.muted });
  }
  function bullets(s, items, o) {
    s.addText(items.map((t, i) => ({ text: t, options: { bullet: { indent: 14 }, breakLine: i < items.length - 1, paraSpaceAfter: 6 } })),
      Object.assign({ fontFace: FONT, fontSize: 13, color: C.ink, isTextBox: true, margin: 0, valign: "top" }, o));
  }
  // 表格：第一行为表头
  function table(s, rows, o, highlightRow) {
    s.addTable(rows.map((r, i) => r.map(t => ({ text: t, options: {
      bold: i === 0 || i === highlightRow, color: i === 0 ? C.white : C.ink,
      fill: { color: i === 0 ? C.ink : i === highlightRow ? C.pinkTint : (i % 2 ? C.white : C.grayLight) } } }))),
    Object.assign({ fontFace: FONT, fontSize: 11.5, border: { type: "solid", color: C.line, pt: 0.5 }, valign: "middle" }, o));
  }
  return { pres, nextPage, text, contentSlide, card, stat, bullets, table };
}

module.exports = { C, FONT, W, H, MX, BODY_TOP, BODY_BOTTOM, F, DATA_NOTE, axis, monthLabels, createDeck };
