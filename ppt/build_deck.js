// 生成面试汇报 PPT：node ppt/build_deck.js
// 数字全部来自 outputs/deck_data.json（由 scripts/12_deck_data.py 从数仓导出），不手抄
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..");
const D = JSON.parse(fs.readFileSync(path.join(ROOT, "outputs", "deck_data.json"), "utf8"));

// ------------------------------------------------------------ 设计系统
const C = {
  ink: "17232B", teal: "0E6E6E", tealLight: "E4F0EF", tealMid: "7FB3B0",
  orange: "E0662F", orangeLight: "FBE9E1", gray: "B8BFC2", grayLight: "F2F4F4",
  muted: "5E6B72", white: "FFFFFF", amber: "E8A317", red: "C8413A", green: "2E8B57",
};
const FONT = "Microsoft YaHei";
const W = 13.333, H = 7.5, MX = 0.6;
const pct = (v, d = 1) => (v * 100).toFixed(d) + "%";
const A = D.adv;   // 进阶分析结果（13_advanced_analysis.py）
const pp = (v, d = 2) => (v >= 0 ? "+" : "−") + Math.abs(v * 100).toFixed(d) + "pp";
const num = v => Math.round(v).toLocaleString("en-US");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "品控数据分析项目";
pres.title = "差评在降，品质客诉在升：电商品控数据分析项目";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

const DUTY = {
  1: "JD 职责① 指标体系建设",
  2: "JD 职责② 可视化看板",
  3: "JD 职责③ 业务专题分析",
  4: "JD 职责④ 取数与 SQL",
  0: "项目方法",
};

let pageNo = 0;
function text(slide, t, o) {
  slide.addText(t, Object.assign({ fontFace: FONT, color: C.ink, isTextBox: true, margin: 0, valign: "top" }, o));
}
function contentSlide({ duty, title, sub }) {
  const s = pres.addSlide();
  pageNo += 1;
  s.background = { color: C.white };
  // 职责徽标：圆 + 编号（贯穿全篇的母题）
  s.addShape(pres.shapes.OVAL, { x: MX, y: 0.42, w: 0.3, h: 0.3, fill: { color: duty ? C.teal : C.gray }, line: { color: duty ? C.teal : C.gray } });
  text(s, duty ? String(duty) : "·", { x: MX, y: 0.42, w: 0.3, h: 0.3, fontSize: 11, bold: true, color: C.white, align: "center", valign: "middle" });
  text(s, DUTY[duty], { x: MX + 0.42, y: 0.42, w: 6, h: 0.3, fontSize: 11, color: C.teal, bold: true, valign: "middle" });
  text(s, title, { x: MX, y: 0.82, w: W - 2 * MX, h: 0.62, fontSize: 28, bold: true, valign: "middle" });
  if (sub) text(s, sub, { x: MX, y: 1.44, w: W - 2 * MX, h: 0.4, fontSize: 14, color: C.muted, valign: "middle" });
  text(s, "数据：Olist 巴西电商公开数据（脱敏真实订单，2017.01 – 2018.08）", { x: MX, y: H - 0.42, w: 8, h: 0.25, fontSize: 9, color: C.muted, valign: "middle" });
  text(s, String(pageNo), { x: W - MX - 0.6, y: H - 0.42, w: 0.6, h: 0.25, fontSize: 9, color: C.muted, align: "right", valign: "middle" });
  return s;
}
function card(s, x, y, w, h, fill = C.grayLight) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: fill } });
}
function stat(s, x, y, w, big, label, color = C.teal, bigSize = 34) {
  text(s, big, { x, y, w, h: 0.62, fontSize: bigSize, bold: true, color, valign: "bottom" });
  text(s, label, { x, y: y + 0.66, w, h: 0.5, fontSize: 12, color: C.muted });
}
function bullets(s, items, o) {
  s.addText(items.map((t, i) => {
    const parts = Array.isArray(t) ? t : [t];
    return { text: parts.join(""), options: { bullet: { indent: 14 }, breakLine: i < items.length - 1, paraSpaceAfter: 6 } };
  }), Object.assign({ fontFace: FONT, fontSize: 14, color: C.ink, isTextBox: true, margin: 0, valign: "top" }, o));
}
const axis = {
  catAxisLabelColor: C.muted, valAxisLabelColor: C.muted, catAxisLabelFontSize: 10, valAxisLabelFontSize: 10,
  catAxisLabelFontFace: FONT, valAxisLabelFontFace: FONT, valGridLine: { color: "E3E6E6", size: 0.5 },
  catGridLine: { style: "none" }, catAxisLineColor: C.gray, valAxisLineShow: false, legendFontFace: FONT,
  titleFontFace: FONT, dataLabelFontFace: FONT,
};

// ============================================================ 1 封面
{
  const s = pres.addSlide();
  pageNo += 1;
  s.background = { color: C.ink };
  text(s, "电商品控数据分析项目", { x: MX, y: 1.2, w: 10, h: 0.5, fontSize: 18, color: C.tealMid, bold: true });
  text(s, "差评在降，品质客诉在升", { x: MX, y: 1.8, w: 12, h: 1.1, fontSize: 48, bold: true, color: C.white, valign: "middle" });
  text(s, "品控指标体系 · 经营看板 · 专题分析 · SQL 取数", { x: MX, y: 2.95, w: 12, h: 0.55, fontSize: 22, color: "D5DEE2", valign: "middle" });
  const facts = [
    [num(D.counts.orders), "真实订单"], [num(D.counts.reviews), "条用户评价（去重后）"],
    [num(D.counts.sellers), "家商家"], [String(D.counts.categories), "个品类"],
  ];
  facts.forEach(([v, l], i) => {
    const x = MX + i * 3.0;
    text(s, v, { x, y: 4.55, w: 2.8, h: 0.6, fontSize: 30, bold: true, color: C.white, valign: "bottom" });
    text(s, l, { x, y: 5.2, w: 2.8, h: 0.35, fontSize: 13, color: "AEBBC1" });
  });
  text(s, "应聘岗位：唯品会 品控数据分析实习生　｜　数据：Olist Brazilian E-Commerce Public Dataset", { x: MX, y: 6.55, w: 12, h: 0.35, fontSize: 12, color: "8FA0A8", valign: "middle" });
  s.addNotes("开场 30 秒：我用巴西电商平台 Olist 公开的约 10 万笔真实订单，按照这个岗位 JD 的四项职责，完整做了一遍品控数据分析：先建指标体系，再搭看板，然后做了一个专题分析，最后把取数需求整理成了一套 SQL 题。标题就是专题分析的核心结论：2018 年差评率在下降，但品质客诉率在上升，差评下降掩盖了品质问题。");
}

// ============================================================ 2 项目概览
{
  const s = contentSlide({ duty: 0, title: "按 JD 的四项职责，做了四件可交付的东西", sub: "所有数字都从同一张数仓宽表 dwd_qc_order 取数，跑数后自动执行 18 项数据质量校验" });
  const items = [
    [1, "品控指标体系", "北极星「品质客诉率」+ 31 个指标", "指标字典 Excel：定义 / 公式 / 口径 SQL / 基准值 / 预警线；6 条口径约定、5 个口径版本"],
    [2, "品控经营看板", "3 页交互看板 + BI 搭建指南", "总览 / 商家风险 / 指标口径；统一筛选、环比、状态标识；附 Power BI DAX 与 Tableau 计算字段"],
    [3, "专题分析", "定位 3 个品控瓶颈，测算治理空间", "差评原因结构、因素分解、订单结构、商家分层、品类风险；3 项举措可把品质客诉率从 5.00% 降到 3.82%（情景区间 3.34%–4.32%）"],
    [4, "SQL 取数题库", "19 道业务取数题，全部实跑", "业务原话 → 口径 → SQL → 自检 → 错误写法对比；4 道题与看板数字逐一对账一致"],
  ];
  items.forEach(([n, t, head, body], i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = MX + col * 6.13, y = 2.1 + row * 2.45, w = 5.93, h = 2.2;
    card(s, x, y, w, h, C.tealLight);
    s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: y + 0.3, w: 0.42, h: 0.42, fill: { color: C.teal }, line: { color: C.teal } });
    text(s, String(n), { x: x + 0.3, y: y + 0.3, w: 0.42, h: 0.42, fontSize: 16, bold: true, color: C.white, align: "center", valign: "middle" });
    text(s, t, { x: x + 0.9, y: y + 0.3, w: w - 1.2, h: 0.42, fontSize: 18, bold: true, valign: "middle" });
    text(s, head, { x: x + 0.3, y: y + 0.88, w: w - 0.6, h: 0.4, fontSize: 15, bold: true, color: C.teal });
    text(s, body, { x: x + 0.3, y: y + 1.32, w: w - 0.6, h: 0.8, fontSize: 12.5, color: C.muted });
  });
  s.addNotes("这一页是全局地图，四张卡片对应 JD 的四项职责。我特别强调一点：所有产出都来自同一张宽表，指标字典里每个指标的基准值是直接执行字典里的 SQL 得到的，看板、报告和 SQL 题的数字能互相对上，这是我理解的『口径统一、对数据准确性负责』。");
}

// ============================================================ 3 数据与方法
{
  const s = contentSlide({ duty: 0, title: "真实公开数据 + 四层数仓 + 评价文本打标", sub: "公开数据里没有「客诉工单」，用评价星级 + 评价原文打标来还原品控问题" });
  // 数仓流程
  const layers = [
    ["ODS", "贴源 8 张表", "行数与源文件逐一对账"],
    ["DWD", "清洗 + 宽表", "评价去重、时间倒挂打标、主品类归属"],
    ["DWS", "商家/品类×月", "只存计数，不存比率"],
    ["ADS", "看板 / 评分卡", "KPI、商家品质分、品类排行"],
  ];
  layers.forEach(([k, a, b], i) => {
    const x = MX + i * 3.08, y = 2.15, w = 2.75, h = 1.55;
    card(s, x, y, w, h, i === 1 ? C.tealLight : C.grayLight);
    text(s, k, { x: x + 0.25, y: y + 0.18, w: 1.2, h: 0.45, fontSize: 22, bold: true, color: C.teal });
    text(s, a, { x: x + 0.25, y: y + 0.66, w: w - 0.4, h: 0.32, fontSize: 13, bold: true });
    text(s, b, { x: x + 0.25, y: y + 1.0, w: w - 0.4, h: 0.5, fontSize: 11, color: C.muted });
    if (i < 3) text(s, "›", { x: x + w + 0.02, y: y + 0.45, w: 0.3, h: 0.6, fontSize: 28, bold: true, color: C.gray, align: "center", valign: "middle" });
  });
  // 左：映射表
  const rows = [
    ["唯品会品控", "本项目数据"],
    ["供应商 / 品牌方", "Olist 商家（3,095 家）"],
    ["客诉 / 售后工单", "评价星级 + 葡语评价原文打标"],
    ["供应商发货时效", "shipping_limit_date 发货 SLA"],
    ["入仓质检 / 退货原因", "公开数据没有 → 定义为待接入指标"],
  ];
  s.addTable(rows.map((r, i) => r.map(t => ({ text: t, options: { bold: i === 0, color: i === 0 ? C.white : C.ink, fill: { color: i === 0 ? C.teal : (i % 2 ? C.white : C.grayLight) } } }))),
    { x: MX, y: 4.1, w: 6.1, colW: [2.2, 3.9], fontFace: FONT, fontSize: 12, border: { type: "solid", color: "E3E6E6", pt: 0.5 }, rowH: 0.42, valign: "middle" });
  // 右：打标 & 质检
  card(s, 7.05, 4.1, 5.68, 2.1, C.tealLight);
  text(s, "评价文本 → 8 类问题标签", { x: 7.35, y: 4.28, w: 5.2, h: 0.35, fontSize: 15, bold: true });
  bullets(s, [
    "葡语关键词规则：假货 / 质量缺陷 / 货不对板 / 少件漏发 / 包装破损 / 未收货 / 延迟 / 服务",
    `随机抽 200 条盲评（大模型逐条读原文判定）：准确率 ${pct(D.gold.precision)}、召回率 ${pct(D.gold.recall)}，规则偏保守`,
    `每次跑数自动执行 ${D.dq_checks} 项校验（跨层对账、主键唯一、分子 ≤ 分母）`,
  ], { x: 7.35, y: 4.72, w: 5.2, h: 1.45, fontSize: 12 });
  s.addNotes("数据是 Olist 公开的巴西电商真实订单，行数和 Kaggle 官方版本完全一致。它是平台 + 商家模式，和唯品会的供应商模式可以对应。最大的缺口是没有客诉工单和质检数据，所以我用『评价星级 + 评价原文』来还原客诉：写了葡语关键词规则打 8 类标签，然后做了两轮抽样复核：先按标签分层抽 140 条看准确率，再随机抽 200 条盲评看召回率（判定都是借助大模型逐条阅读葡语原文完成的，每条附了中文释义，方便人工抽查）。结果是准确率 97%、召回率 75%，规则偏保守，会低估品质客诉率，但 2017 和 2018 年漏标的比例相近，所以趋势结论不受影响。数仓分四层，DWS 只存计数，比率最后再算，避免比率再平均。");
}

// ============================================================ 4 指标体系
{
  const s = contentSlide({ duty: 1, title: "北极星选「品质客诉率」，差评率只做护栏", sub: "品质客诉率 = 签收订单中，因商品本身问题给出 1-3 星并描述该问题的订单占比" });
  // 顶部北极星
  const cx = W / 2;
  card(s, cx - 2.3, 2.0, 4.6, 0.95, C.teal);
  text(s, "L0 北极星　品质客诉率", { x: cx - 2.2, y: 2.06, w: 4.4, h: 0.42, fontSize: 16, bold: true, color: C.white, align: "center", valign: "middle" });
  text(s, `基准 ${pct(D.sizing.baseline_rate, 2)}　目标 ≤ 4.0%　预警 > 5.5%`, { x: cx - 2.2, y: 2.5, w: 4.4, h: 0.36, fontSize: 12, color: "D9ECEA", align: "center", valign: "middle" });
  // L1
  const t = D.type_by_year["2018M1-8"];
  const l1 = [["少件/漏发", t.missing], ["质量缺陷", t.defect], ["货不对板", t.mismatch], ["假货", t.fake], ["包装破损", t.package]];
  text(s, "L1 结果指标 · 按问题类型拆（What）", { x: MX, y: 3.2, w: 6, h: 0.3, fontSize: 12, bold: true, color: C.teal });
  l1.forEach(([n, v], i) => {
    const x = MX + i * 1.62, y = 3.55;
    card(s, x, y, 1.5, 0.95, C.tealLight);
    text(s, n, { x: x + 0.12, y: y + 0.1, w: 1.3, h: 0.3, fontSize: 12, bold: true });
    text(s, n === "假货" ? `${(v * 1e4).toFixed(0)}/万单` : pct(v, 2), { x: x + 0.12, y: y + 0.45, w: 1.3, h: 0.4, fontSize: 17, bold: true, color: C.teal });
  });
  // 右侧护栏
  card(s, MX + 8.3, 3.55, 3.83, 0.95, C.grayLight);
  text(s, "护栏：差评率 / 平均分 / 差评品质原因占比", { x: MX + 8.45, y: 3.62, w: 3.6, h: 0.35, fontSize: 12, bold: true });
  text(s, "品控不直接负责，但必须一起看", { x: MX + 8.45, y: 3.98, w: 3.6, h: 0.35, fontSize: 11, color: C.muted });
  // L2
  text(s, "L2 过程指标 · 按品控链路拆（Where）", { x: MX, y: 4.75, w: 6, h: 0.3, fontSize: 12, bold: true, color: C.teal });
  const l2 = [
    ["商品准入", "动销商品信息完整率\n高风险品类订单占比"],
    ["商家管理", "发货超时率 · 商家品质分\n高风险商家数 / 客诉贡献度"],
    ["仓配履约", "准时签收率\n多件订单少件率"],
    ["待接入（内部数据）", "入仓质检合格率 · 问题商品拦截率\n品质退货率 · 客诉响应时长"],
  ];
  l2.forEach(([n, v], i) => {
    const x = MX + i * 3.08, y = 5.1;
    card(s, x, y, 2.9, 1.3, i === 3 ? C.white : C.grayLight);
    if (i === 3) s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 2.9, h: 1.3, rectRadius: 0.08, fill: { color: C.white }, line: { color: C.gray, dashType: "dash", width: 1 } });
    text(s, n, { x: x + 0.2, y: y + 0.14, w: 2.6, h: 0.32, fontSize: 13, bold: true, color: i === 3 ? C.muted : C.ink });
    text(s, v, { x: x + 0.2, y: y + 0.52, w: 2.6, h: 0.72, fontSize: 11, color: C.muted });
  });
  s.addNotes("为什么不用差评率做北极星？因为差评率被物流主导：2018 年 3 月物流出问题，差评率冲到 22.8%，4 月物流恢复又立刻回落，这期间品控什么都没做。让品控背一个自己控制不了的指标，没法考核也没法复盘。所以北极星选品质客诉率，只统计商品本身出问题的订单。往下按两个方向拆：按问题类型拆是 What，每类问题对应不同的责任方；按品控链路拆是 Where，结果指标出问题时顺着链路找过程指标。虚线框是公开数据里没有、但唯品会一定有的质检和退货数据，我先把口径定义好了，接入就能上线。");
}

// ============================================================ 5 口径统一
{
  const s = contentSlide({ duty: 1, title: "口径统一：6 条约定，写进字典、落到看板", sub: "同一个指标，看板、周报、专题分析、临时取数必须是同一个数" });
  const rules = [
    ["按下单月归属", "分子分母是同一批订单；\"本月投诉 ÷ 本月签收\"会错配（3 月：4.97% vs 5.25%）"],
    ["签收口径", "状态 delivered 且有签收时间（8 单状态已签收但没有签收时间）"],
    ["一单一评", "547 单有多条评价，保留用户最后一次提交的评价"],
    ["品质客诉只认 1-3 星", "4-5 星里的\"sem defeito（没有瑕疵）\"会被关键词误命中"],
    ["问题类型可多选", "各类发生率之和 > 品质客诉率，不能相加；要互斥结构时用主标签"],
    ["比率最后再算", "底表只存计数；各品类客诉率的简单平均 ≠ 平台客诉率"],
  ];
  rules.forEach(([h, b], i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = MX + col * 4.1, y = 2.05 + row * 1.62, w = 3.9, hh = 1.45;
    card(s, x, y, w, hh, C.grayLight);
    text(s, String(i + 1), { x: x + 0.2, y: y + 0.15, w: 0.4, h: 0.4, fontSize: 20, bold: true, color: C.teal });
    text(s, h, { x: x + 0.62, y: y + 0.17, w: w - 0.8, h: 0.36, fontSize: 14, bold: true, valign: "middle" });
    text(s, b, { x: x + 0.2, y: y + 0.62, w: w - 0.4, h: 0.76, fontSize: 11.5, color: C.muted });
  });
  // 口径版本时间线
  text(s, "口径迭代记录", { x: MX, y: 5.4, w: 3, h: 0.3, fontSize: 12, bold: true, color: C.teal });
  const vs = [["v0.1", "关键词命中即算"], ["v0.2", "限定 1-3 星 + 剔除否定句"], ["v0.3", "包装破损从缺陷中剥离"], ["v0.4", "抽样复核 140 条，修 8 条规则"], ["v1.0", "口径冻结，四端同源"]];
  s.addShape(pres.shapes.LINE, { x: MX + 0.1, y: 6.05, w: 11.9, h: 0, line: { color: C.gray, width: 1 } });
  vs.forEach(([v, d], i) => {
    const x = MX + i * 2.45;
    s.addShape(pres.shapes.OVAL, { x: x + 0.02, y: 5.96, w: 0.18, h: 0.18, fill: { color: i === 4 ? C.teal : C.white }, line: { color: C.teal, width: 1.5 } });
    text(s, v, { x: x + 0.3, y: 5.78, w: 0.8, h: 0.28, fontSize: 12, bold: true, color: C.teal });
    text(s, d, { x: x + 0.3, y: 6.1, w: 2.1, h: 0.4, fontSize: 10.5, color: C.muted });
  });
  s.addNotes("口径统一是 JD 第一条里特别强调的。我定了 6 条约定，每条后面都有一个真实踩过的坑。比如第一条，按下单月归属：业务同学如果用『3 月收到的投诉 ÷ 3 月签收的订单』，算出来是 5.25%，看板是 4.97%，两个数都没错，但回答的问题不一样。下面的时间线是口径本身的迭代记录，每个版本改了什么、为什么改，都记在字典的『口径变更记录』里。");
}

// ============================================================ 6 看板
{
  const s = contentSlide({ duty: 2, title: "经营看板：先回答「好不好」，再回答「在哪里」", sub: "总 → 分 → 明细；筛选器一行作用于全页；状态用圆点 + 文字，不只靠颜色" });
  const img = path.join(ROOT, "docs", "images", "dashboard_overview_top.png");
  s.addImage({ path: img, x: MX, y: 2.0, w: 7.7, h: 7.7 * 1640 / 2720 });
  s.addShape(pres.shapes.RECTANGLE, { x: MX, y: 2.0, w: 7.7, h: 7.7 * 1640 / 2720, fill: { type: "none" }, line: { color: "D5DADB", width: 0.75 } });
  const x = 8.65, w = W - MX - x;
  const pts = [
    ["谁看什么", "品控负责人看北极星 + 环比；类目运营看类目排行和品类表；商家管理看风险榜"],
    ["不做双轴图", "差评率与品质客诉率量纲不同，双轴会制造假相关，改成各自独立"],
    ["比率筛选后再算", "底表只存计数，任意筛选组合下总计行都正确"],
    ["口径可查", "第三页直接展示指标字典，业务方不用再来问\"这个数怎么算的\""],
  ];
  pts.forEach(([h, b], i) => {
    const y = 2.0 + i * 1.18;
    text(s, h, { x, y, w, h: 0.34, fontSize: 14, bold: true, color: C.teal });
    text(s, b, { x, y: y + 0.36, w, h: 0.75, fontSize: 12, color: C.ink });
  });
  s.addNotes("看板我用 HTML 做了一个能直接打开的交互版，同时写了 Power BI 和 Tableau 的搭建指南，包括数据模型和 DAX 度量值。设计上我最在意两件事：一是第一屏 5 秒内回答『这个月品质好不好』，所以北极星单独放大、带状态和环比；二是数字在任何筛选组合下都对，所以底表只存计数，筛选之后再相除。还有一个取舍是不做双轴图，因为双轴的对齐是任意的，很容易让人看出不存在的相关性。另外我做了一个 Excel 商家品质月报模板，用 SUMIFS、INDEX/MATCH 和数据透视表实现，改参数就能自动出名单，和数仓评分卡的结果完全一致。");
}

// ============================================================ 7 分析框架
{
  const s = contentSlide({ duty: 3, title: "专题分析：差评在降，为什么品控反而要警惕？", sub: "假设驱动：先看大盘和结构，再拆四个方向找瓶颈，最后证伪并测算治理空间" });
  const steps = [
    ["大盘", "差评率与品质客诉率\n走势是否一致？"],
    ["结构", "差评里品质问题\n占比怎么变？"],
    ["归因", "上升来自结构变化\n还是同类恶化？"],
    ["瓶颈", "订单结构 · 商家\n品类 · 商品信息"],
    ["证伪", "新商家？晚到损坏？\n影响复购？"],
    ["测算", "三项举措能降到多少？"],
  ];
  steps.forEach(([h, b], i) => {
    const x = MX + i * 2.05, y = 2.35, w = 1.85;
    card(s, x, y, w, 2.1, i === 3 ? C.tealLight : C.grayLight);
    text(s, String(i + 1), { x: x + 0.2, y: y + 0.18, w: 0.5, h: 0.45, fontSize: 22, bold: true, color: C.teal });
    text(s, h, { x: x + 0.2, y: y + 0.7, w: w - 0.3, h: 0.4, fontSize: 17, bold: true });
    text(s, b, { x: x + 0.2, y: y + 1.15, w: w - 0.3, h: 0.85, fontSize: 11.5, color: C.muted });
  });
  card(s, MX, 4.85, W - 2 * MX, 1.6, C.white);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: MX, y: 4.85, w: W - 2 * MX, h: 1.6, rectRadius: 0.08, fill: { color: C.orangeLight }, line: { color: C.orangeLight } });
  text(s, "一句话结论", { x: MX + 0.3, y: 5.0, w: 3, h: 0.35, fontSize: 13, bold: true, color: C.orange });
  text(s, `2018 年物流改善让差评率从 ${pct(D.bad_rate[14])} 降到 ${pct(D.bad_rate[19])}，但品质客诉率从 2017 年的 ${pct(D.decomp_category.rate_A, 2)} 升到 ${pct(D.decomp_category.rate_B, 2)}，差评里品质原因的占比从约 22% 升到 35%。上升全部来自同类订单内部变差；三个瓶颈是多件订单少件漏发、少数高风险商家、3C / 钟表的假货与货不对板。`,
    { x: MX + 0.3, y: 5.38, w: W - 2 * MX - 0.6, h: 1.0, fontSize: 14, color: C.ink });
  s.addNotes("专题分析的出发点是一个反直觉的现象：2018 年差评率在降，业务可能觉得体验在变好。但我按品质问题拆开看，发现品质客诉率反而在升。分析按六步走，第四步是重点，找到了三个瓶颈；第五步我专门验证了三个直觉上成立、但数据不支持的假设。");
}

// ============================================================ 8 发现1 趋势（p 控制图）
{
  const s = contentSlide({ duty: 3, title: "发现①　差评率跟着物流走，品质客诉率越出了控制限", sub: "左：p 控制图（2017 年为基线，控制限 ±3σ 随签收量变化）；右：差评率与准时率。量纲不同，分开画" });
  const labels = D.months;
  const p0 = A.spc.p0;
  s.addChart(pres.charts.LINE, [
    { name: "品质客诉率", labels, values: D.p_chart.p },
    { name: "上控制限 UCL", labels, values: D.p_chart.ucl },
    { name: "下控制限 LCL", labels, values: D.p_chart.lcl },
    { name: `中心线 ${pct(p0, 2)}`, labels, values: labels.map(() => p0) },
  ], Object.assign({}, axis, {
    x: MX, y: 1.95, w: 7.4, h: 4.45, chartColors: [C.teal, "C9CFD1", "C9CFD1", "5E6B72"], lineSize: 2, lineDataSymbol: "none",
    valAxisLabelFormatCode: "0.0%", valAxisMinVal: 0.02, valAxisMaxVal: 0.065, valAxisMajorUnit: 0.005, showLegend: true, legendPos: "b",
    legendFontSize: 9, catAxisLabelFontSize: 9, catAxisLabelFrequency: 2,
  }));
  text(s, `2018 年 ${A.spc.beyond_ucl_months.map(m => +m.slice(5) + " 月").join("、")}越出上控制限；自 2017 年 10 月起连续 ${A.spc.max_run_above} 个月高于中心线（判异准则：≥ 9 点同侧）→ 过程均值发生了持续偏移，不是随机波动`,
    { x: MX, y: 6.42, w: 7.4, h: 0.55, fontSize: 11.5, color: C.orange, bold: true });
  const small = (vals, title, y, fmtMin, fmtMax) => s.addChart(pres.charts.LINE, [{ name: title, labels, values: vals }], Object.assign({}, axis, {
    x: 8.2, y, w: 4.55, h: 2.2, chartColors: ["8A959A"], lineSize: 2, lineDataSymbol: "none", valAxisLabelFormatCode: "0%",
    valAxisMinVal: fmtMin, valAxisMaxVal: fmtMax, showLegend: false, showTitle: true, title, titleFontSize: 12, titleColor: C.ink,
    catAxisLabelFontSize: 8, valAxisLabelFontSize: 9, catAxisLabelFrequency: 4,
  }));
  small(D.bad_rate, "差评率（1-2 星 ÷ 已评价）", 1.95, 0.05, 0.25);
  small(D.on_time_rate, "准时签收率", 4.25, 0.75, 1.0);
  s.addNotes(`左边是品质客诉率的 p 控制图，这是质量管理里判断"异常还是波动"的标准工具。我用 2017 年做基线，12 个月全部在控制限内，说明基线是稳定的；2018 年有 3 个月越出上控制限，而且从 2017 年 10 月开始连续 11 个月高于中心线，触发"连续 9 点在同侧"的判异准则，说明过程均值已经偏移了。两年对比的 z 检验 z = 5.05，p 小于万分之一。右边两张是差评率和准时率，形状几乎是镜像：物流出问题时准时率跌到 81%，差评率冲到 22.8%，所以差评率下降主要是物流改善带来的。最后一个月回落到 4.4%，因为评价还在回收，我不会解读成好转。`);
}

// ============================================================ 9 发现2 差评结构
{
  const s = contentSlide({ duty: 3, title: "发现②　差评里，品质问题的占比从 22% 升到 35%", sub: "1-2 星差评按主标签归类（互斥口径）" });
  const names = [["quality", "品质类"], ["fulfill", "履约类（未收货/延迟）"], ["service", "服务类"], ["other", "有文本·原因不明"], ["notext", "无文本"]];
  const qlabels = D.quarters.map(q => q === "2018Q3" ? "2018Q3(7-8月)" : q);
  s.addChart(pres.charts.BAR, names.map(([k, n]) => ({ name: n, labels: qlabels, values: D.mix[k] })), Object.assign({}, axis, {
    x: MX, y: 1.95, w: 8.3, h: 4.6, barDir: "col", barGrouping: "percentStacked", barGapWidthPct: 70,
    chartColors: [C.teal, C.orange, "7FB3B0", "E8C07A", "D0D5D7"], valAxisLabelFormatCode: "0%",
    showLegend: true, legendPos: "b", legendFontSize: 10, showValue: false,
  }));
  const q = D.mix.quality;
  stat(s, 9.3, 2.1, 3.4, `${pct(q[0], 0)} → ${pct(q[6], 0)}`, "差评中品质类占比（2017Q1 → 2018Q3）", C.teal, 32);
  stat(s, 9.3, 3.55, 3.4, `${pct(D.mix.fulfill[4], 0)} → ${pct(D.mix.fulfill[6], 0)}`, "履约类占比（物流危机的 2018Q1 → 2018Q3）", C.orange, 32);
  text(s, "物流问题解决之后，品质问题成为差评里品控能管、也最该管的部分。", { x: 9.3, y: 5.05, w: 3.4, h: 1.2, fontSize: 13, color: C.ink });
  s.addNotes("这张图把每个季度的 1-2 星差评按原因拆开。蓝绿色是品质类，2017 年一直在 20% 出头，2018 年二季度开始跳到 34%-35%；橙色的履约类在 2018 年一季度物流危机时最高。换句话说，物流问题解决以后，剩下的差评里，品质问题越来越突出，这正是品控团队的工作范围。");
}

// ============================================================ 10 发现3 因素分解
{
  const s = contentSlide({ duty: 3, title: "发现③　上升不是「卖了更多高风险品类」，而是同类订单在变差", sub: `品质客诉率 2017 年 ${pct(D.decomp_category.rate_A, 2)} → 2018 年 1-8 月 ${pct(D.decomp_category.rate_B, 2)}（+${(100 * (D.decomp_category.rate_B - D.decomp_category.rate_A)).toFixed(2)}pp）` });
  // 左：因素分解
  card(s, MX, 1.95, 4.4, 4.5, C.grayLight);
  text(s, "按一级类目做因素分解", { x: MX + 0.3, y: 2.1, w: 3.9, h: 0.35, fontSize: 14, bold: true });
  const dc = D.decomp_category;
  const rows = [["结构效应", dc.mix_effect, "品类占比变化"], ["组内效应", dc.within_effect, "品类自身客诉率变化"], ["交互项", dc.interaction, ""]];
  rows.forEach(([n, v, d], i) => {
    const y = 2.65 + i * 1.05;
    text(s, n, { x: MX + 0.3, y, w: 1.6, h: 0.4, fontSize: 14, bold: true, valign: "middle" });
    text(s, pp(v), { x: MX + 1.9, y, w: 2.2, h: 0.4, fontSize: 24, bold: true, color: i === 1 ? C.orange : C.muted, valign: "middle", align: "right" });
    if (d) text(s, d, { x: MX + 0.3, y: y + 0.45, w: 3.8, h: 0.3, fontSize: 11, color: C.muted });
  });
  text(s, "组内贡献最大：3C 数码、钟表礼品、家居家纺、母婴玩具", { x: MX + 0.3, y: 5.75, w: 3.9, h: 0.6, fontSize: 11.5, color: C.ink });
  // 右：类型对比
  const names = [["missing", "少件/漏发"], ["defect", "质量缺陷"], ["mismatch", "货不对板"], ["fake", "假货"], ["package", "包装破损"]];
  const a = D.type_by_year["2017"], b = D.type_by_year["2018M1-8"];
  s.addChart(pres.charts.BAR, [
    { name: "2017 全年", labels: names.map(n => n[1]), values: names.map(n => a[n[0]]) },
    { name: "2018 年 1-8 月", labels: names.map(n => n[1]), values: names.map(n => b[n[0]]) },
  ], Object.assign({}, axis, {
    x: 5.3, y: 1.95, w: 7.45, h: 3.7, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60,
    chartColors: [C.gray, C.teal], valAxisLabelFormatCode: "0.0%", showValue: true, dataLabelFormatCode: "0.00%",
    dataLabelFontSize: 9, dataLabelColor: C.ink, dataLabelPosition: "outEnd", showLegend: true, legendPos: "t", legendFontSize: 10,
    showTitle: true, title: "各类问题发生率（占签收单）", titleFontSize: 12, titleColor: C.ink,
  }));
  const chg = k => (b[k] / a[k] - 1);
  text(s, `增幅最大：货不对板 ${chg("mismatch") >= 0 ? "+" : ""}${(chg("mismatch") * 100).toFixed(0)}%，假货 +${(chg("fake") * 100).toFixed(0)}%；质量缺陷基本持平（+${(chg("defect") * 100).toFixed(0)}%）`,
    { x: 5.4, y: 5.85, w: 7.3, h: 0.5, fontSize: 13, bold: true, color: C.orange });
  s.addNotes("品质客诉率上升 0.69 个百分点，第一反应要问：是不是 2018 年卖了更多高客诉的品类？我用因素分解把变化拆成结构效应和组内效应，结构效应几乎为 0，上升全部来自品类内部变差。再看问题类型：货不对板涨了三分之一，假货将近翻倍，质量缺陷基本不变。这说明问题更多出在『描述与实物不符、正品管控』，而不是生产质量本身。");
}

// ============================================================ 11 发现4 订单结构
{
  const s = contentSlide({ duty: 3, title: "瓶颈①　多件订单：10% 的订单贡献了 34% 的品质客诉", sub: "几乎全部来自少件/漏发；99.8% 的少件投诉提交时订单已显示签收" });
  const ot = D.order_type;
  const keys = Object.keys(ot).sort();
  const labels = keys.map(k => `${k.slice(2)}：${pct(ot[k].qc, 1)}（少件 ${pct(ot[k].missing, 1)}）`);
  s.addChart(pres.charts.BAR, [
    { name: "少件/漏发", labels, values: keys.map(k => ot[k].missing) },
    { name: "其他品质问题", labels, values: keys.map(k => Math.max(0, ot[k].qc - ot[k].missing)) },
  ], Object.assign({}, axis, {
    x: MX, y: 1.95, w: 7.6, h: 4.5, barDir: "bar", barGrouping: "stacked", barGapWidthPct: 55,
    chartColors: [C.orange, C.teal], valAxisLabelFormatCode: "0%", showValue: false, catAxisLabelFontSize: 11,
    showLegend: true, legendPos: "t", legendFontSize: 10, valAxisMinVal: 0,
    catAxisOrientation: "maxMin", showTitle: true, title: "品质客诉率 × 订单结构", titleFontSize: 12, titleColor: C.ink,
  }));
  const m = D.multi_item;
  stat(s, 8.75, 2.0, 4.0, pct(m.order_share, 0), "多件订单占签收单");
  stat(s, 8.75, 3.25, 4.0, pct(m.qc_share, 0), "贡献的品质客诉", C.orange);
  stat(s, 8.75, 4.5, 4.0, pct(m.missing_share, 0), "贡献的少件/漏发客诉", C.orange);
  text(s, `多件订单品质客诉率 ${pct(m.multi_qc)}，是单件订单（${pct(m.single_qc)}）的 ${(m.multi_qc / m.single_qc).toFixed(1)} 倍`, { x: 8.75, y: 5.8, w: 4.0, h: 0.6, fontSize: 12, bold: true });
  s.addNotes("第一个瓶颈在订单结构。单件订单品质客诉率只有 3.5%，多件订单是 14% 到 27%，多商家订单最高，而且几乎都是少件漏发。我还验证了一件事：这些少件投诉，99.8% 提交时订单已经显示签收，所以不是『还没收齐就着急评价』，而是用户在签收状态下确实缺件——要么漏发，要么分包裹没有同步送达、也没告诉用户。两种情况都指向出库环节。");
}

// ============================================================ 12 发现5 商家
{
  const s = contentSlide({ duty: 3, title: "瓶颈②　3% 的高风险商家，贡献了 12% 的品质客诉", sub: `近 6 个月签收 ≥ 30 单的 ${D.seller_eligible} 家商家（覆盖 ${pct(D.seller_cover, 0)} 订单）；平滑客诉率 ≥ 平台 2 倍且客诉 ≥ 3 单 = 高风险` });
  const sh = D.seller_tier_share;
  const cats = ["商家数", "签收订单", "GMV", "品质客诉单"];
  const kk = ["sellers", "delivered", "gmv", "qc"];
  s.addChart(pres.charts.BAR, ["正常", "需关注", "高风险"].map(t => ({ name: t, labels: cats, values: kk.map(k => sh[t][k]) })), Object.assign({}, axis, {
    x: MX, y: 1.95, w: 7.6, h: 4.2, barDir: "bar", barGrouping: "percentStacked", barGapWidthPct: 55,
    chartColors: ["D0D5D7", C.amber, C.red], valAxisLabelFormatCode: "0%", showValue: true, dataLabelFormatCode: "0%",
    dataLabelPosition: "ctr", dataLabelColor: C.ink, dataLabelFontSize: 9, showLegend: true, legendPos: "t", legendFontSize: 10,
    catAxisOrientation: "maxMin",
  }));
  const tier = D.seller_tier;
  const x = 8.75, w = 4.0;
  card(s, x, 1.95, w, 2.05, C.grayLight);
  text(s, "评分模型", { x: x + 0.25, y: 2.08, w: w - 0.5, h: 0.32, fontSize: 13, bold: true, color: C.teal });
  text(s, "品质分 = 客诉率 50% + 差评率 20% + 发货超时率 15% + 延迟签收率 15%（分位数打分）\n平滑客诉率 =（客诉 + 50 × 平台）÷（签收 + 50）", { x: x + 0.25, y: 2.45, w: w - 0.5, h: 1.45, fontSize: 11, color: C.ink });
  stat(s, x, 4.2, w, `${pct(tier["高风险"].qc_rate, 1)}`, `高风险商家平均品质客诉率（正常商家为 ${pct(D.seller_tier["正常"].qc_rate, 1)}）`, C.red, 30);
  text(s, `不平滑会圈出 302 家；平滑后的 ${A.seller_ci.high_risk_n} 家全部通过 Wilson 区间检验（显著高于平台）。回测：前 6 个月判为高风险的商家，下 6 个月客诉率仍是平台的 ${A.backtest.pooled["高风险"]["平均倍数"].toFixed(1)} 倍`,
    { x, y: 5.35, w, h: 0.95, fontSize: 11, color: C.muted });
  s.addNotes("第二个瓶颈是商家。我做了一个商家品质分，四个分项按分位数打分再加权。风险分层时最关键的是小样本问题：一个商家 10 单里 1 单客诉就是 10%，看起来是平台的两倍，但很可能只是运气。所以我用了贝叶斯平滑，给每个商家先加 50 单平台平均水平的虚拟订单。不平滑会圈出 302 家，平滑加门槛后只剩 10 家，这 10 家只占 3.6% 的订单，却贡献了 12.5% 的品质客诉，客诉率是正常商家的 4 倍多。模型靠不靠谱我做了两个检验：一是 Wilson 置信区间，10 家的区间下限全部高于平台；二是回测，用前 6 个月分层、看后 6 个月，三个窗口里高风险商家下一期客诉率平均仍是平台的 2.2 倍，需关注 1.5 倍，正常 0.9 倍，排序每次都成立。同时能看到均值回归，高风险商家会从 13%-15% 回落到 10%-14%，所以评估整改效果一定要有对照组。");
}

// ============================================================ 13 发现6 品类
{
  const s = contentSlide({ duty: 3, title: "瓶颈③　大件家具少配件，3C/钟表假货高，信息缺失商品风险大", sub: `签收 ≥ 300 单的品类中，品质客诉率最高的 10 个（平台 ${pct(D.overview.qc_rate, 1)}）` });
  const top = D.category_top.slice(0, 10).reverse();
  s.addChart(pres.charts.BAR, [{ name: "品质客诉率", labels: top.map(c => c.category_cn), values: top.map(c => c.qc_rate) }], Object.assign({}, axis, {
    x: MX, y: 1.95, w: 6.6, h: 4.6, barDir: "bar", barGapWidthPct: 45, chartColors: [C.teal], valAxisLabelFormatCode: "0%",
    showValue: true, dataLabelFormatCode: "0.0%", dataLabelPosition: "outEnd", dataLabelFontSize: 10, dataLabelColor: C.ink,
    showLegend: false, valAxisMinVal: 0, valAxisMaxVal: 0.12, valAxisMajorUnit: 0.02,
  }));
  const f10 = v => (v * 1e4).toFixed(0);
  const info = D.info, heavy = D.heavy;
  const cards = [
    ["办公家具 10.8%", `平台 ${pct(D.overview.qc_rate, 1)} 的 2.3 倍：少件/漏发 ${pct(D.category_top[0].missing_rate, 1)}（缺螺丝、配件），质量缺陷 ${pct(D.category_top[0].defect_rate, 1)}；单件订单中 ≥15kg 大件的品质客诉率 ${pct(heavy["4 ≥15kg"].qc, 1)}`],
    ["假货集中在 3C / 钟表", `电脑配件 ${f10(D.fake_top[1].fake_rate)}、钟表礼品 ${f10(D.fake_top[3].fake_rate)} 单/万单，平台 ${f10(D.fake_platform)} 单/万单`],
    ["信息缺失 = 高风险", `缺品类/图片/描述的商品，假货投诉率 ${pct(info["0 信息缺失"].fake, 2)}，是信息完整商品的约 9 倍`],
  ];
  cards.forEach(([h, b], i) => {
    const y = 1.95 + i * 1.55, x = 7.55, w = W - MX - x;
    card(s, x, y, w, 1.4, i === 0 ? C.orangeLight : C.grayLight);
    text(s, h, { x: x + 0.25, y: y + 0.14, w: w - 0.5, h: 0.36, fontSize: 14, bold: true, color: i === 0 ? C.orange : C.ink });
    text(s, b, { x: x + 0.25, y: y + 0.55, w: w - 0.5, h: 0.8, fontSize: 11.5, color: C.ink });
  });
  s.addNotes("第三个瓶颈在品类和商品。办公家具品质客诉率 10.8%，是平台的两倍多，主要是少配件和质量缺陷，大件商品普遍如此。假货投诉集中在电脑配件和钟表，这和唯品会『正品保障』的定位直接相关。还有一个很实用的发现：商品信息缺失——没有品类、没有图片描述——的商品，假货投诉率是信息完整商品的 9 倍，这可以直接变成上架准入的卡口。");
}

// ============================================================ 13b 唯品会视角
{
  const V = A.vip_view;
  const s = contentSlide({ duty: 3, title: "放到唯品会的品类结构下：穿戴类问题涨得更快，假货更集中", sub: `唯品会 2024 年穿戴类 GMV 占比 75%，Olist 仅 ${pct(V.olist_wear_share, 0)}；按唯品会结构重新加权后，假货风险会被放大` });
  const lab = ["穿戴类", "非穿戴"];
  const bar = (title, vals17, vals18, x, fmt, max) => s.addChart(pres.charts.BAR, [
    { name: "2017", labels: lab, values: vals17 }, { name: "2018 年 1-8 月", labels: lab, values: vals18 },
  ], Object.assign({}, axis, {
    x, y: 1.95, w: 3.6, h: 3.6, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60, chartColors: [C.gray, C.teal],
    valAxisLabelFormatCode: fmt, dataLabelFormatCode: fmt, showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 9,
    dataLabelColor: C.ink, showLegend: true, legendPos: "b", legendFontSize: 9, showTitle: true, title, titleFontSize: 12,
    titleColor: C.ink, valAxisMinVal: 0, valAxisMaxVal: max,
  }));
  bar("品质客诉率", [V.wear["2017"].qc, V.nonwear["2017"].qc], [V.wear["2018"].qc, V.nonwear["2018"].qc], MX, "0.0%", 0.07);
  bar("假货投诉（每万单）", [V.wear["2017"].fake10k, V.nonwear["2017"].fake10k], [V.wear["2018"].fake10k, V.nonwear["2018"].fake10k], MX + 3.75, "0", 70);
  const x = 8.2, w = W - MX - x;
  stat(s, x, 1.95, w, `${pct(V.wear["2017"].qc)} → ${pct(V.wear["2018"].qc)}`, `穿戴类品质客诉率（z = ${V.wear_z.toFixed(2)}，p = ${V.wear_p.toFixed(3)}，显著）`, C.teal, 28);
  stat(s, x, 3.2, w, `${D.fake_platform ? (V.reweight_2018.olist_mix.fake10k).toFixed(0) : ""} → ${(V.reweight_2018.vip_mix.fake10k).toFixed(0)}`, "每万单假货投诉：Olist 结构 → 按唯品会 75% 穿戴类重新加权", C.orange, 28);
  card(s, x, 4.5, w, 1.95, C.grayLight);
  text(s, "外部参考：国家监督抽查", { x: x + 0.2, y: 4.62, w: w - 0.4, h: 0.3, fontSize: 12, bold: true, color: C.teal });
  const down = D.samr.find(r => r.product === "羽绒服装");
  text(s, `2023 年在 15 家电商平台抽查羽绒服 ${down.batches} 批次，${down.unqualified_batches} 批次不合格（${pct(down.unqualified_rate)}），其中 19 批次是纤维含量与标称不符——本质就是"货不对板"。服饰类入仓质检应把成分 / 标签一致性列为必检项。`,
    { x: x + 0.2, y: 4.97, w: w - 0.4, h: 1.4, fontSize: 10.5, color: C.ink });
  text(s, "外部数据来源：市场监管总局抽查通报（经新闻转载）；唯品会品类结构来自 2024 年财报报道；见 data/external/", { x: MX, y: 6.55, w: 7.4, h: 0.3, fontSize: 9, color: C.muted });
  s.addNotes(`Olist 以家居为主，穿戴类只占 9%，但唯品会穿戴类占 GMV 的 75%，所以我专门把穿戴类拿出来看。穿戴类品质客诉率从 3.7% 升到 5.1%，涨幅比平台大，检验是显著的；假货投诉从每万单 10 单涨到 54 单。如果按唯品会的品类结构重新加权，平台的假货投诉会从每万单 22 单翻倍到 45 单左右，所以在唯品会的语境下，"正品"和"货不对板"应该是品控的第一优先级。外部数据也能印证：国抽里电商平台羽绒服的不合格批次，大部分是纤维含量和标称不符，这就是货不对板。需要说明的是 Olist 的服装样本很小，这一页的结论是方向性的。`);
}

// ============================================================ 14 证伪
{
  const s = contentSlide({ duty: 3, title: "三个直觉上成立、但数据不支持的假设", sub: "证伪同样是结论：避免把资源投到错误的方向" });
  const fz = D.falsify;
  const t = fz.tenure, l = fz.late, r = fz.repurchase;
  const items = [
    ["新入驻商家品质更差？", "不成立", `入驻 < 3 个月 ${pct(t["1 入驻<3个月"], 1)}，12 个月以上 ${pct(t["4 12个月以上"], 1)}，新商家并不更差`, "准入审核不是主要短板，重点应放在存量商家的持续监控"],
    ["送晚了导致更多损坏？", "不成立", `延迟签收订单品质客诉率 ${pct(l["1"].qc, 1)}，准时订单 ${pct(l["0"].qc, 1)}；包装破损率几乎一样`, "延迟订单的差评主要在抱怨\"慢\"，物流时效和品质问题要分开治理"],
    ["首单遇到品质问题会流失？", "证据不足", `首单品质客诉用户复购率 ${pct(r["1 首单品质客诉"].repurchase_rate, 1)}，首单 5 星 ${pct(r["4 首单5星"].repurchase_rate, 1)}，整体复购只有 4% 左右`, "Olist 平台整体复购很低，这个问题需要唯品会的会员数据才能回答"],
  ];
  items.forEach(([q, v, e, so], i) => {
    const x = MX + i * 4.1, y = 2.0, w = 3.9, h = 3.9;
    card(s, x, y, w, h, C.grayLight);
    text(s, q, { x: x + 0.25, y: y + 0.25, w: w - 0.5, h: 0.75, fontSize: 16, bold: true });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.25, y: y + 1.1, w: 1.3, h: 0.4, rectRadius: 0.2, fill: { color: i === 2 ? C.amber : C.muted }, line: { color: i === 2 ? C.amber : C.muted } });
    text(s, v, { x: x + 0.25, y: y + 1.1, w: 1.3, h: 0.4, fontSize: 12, bold: true, color: C.white, align: "center", valign: "middle" });
    text(s, e, { x: x + 0.25, y: y + 1.7, w: w - 0.5, h: 1.3, fontSize: 12.5, color: C.ink });
    text(s, so, { x: x + 0.25, y: y + 2.85, w: w - 0.5, h: 0.95, fontSize: 12, color: C.teal, bold: true });
  });
  s.addNotes("分析里我也验证了三个直觉上很合理的假设，数据都不支持。新商家并不比老商家差；送晚了的订单品质客诉率反而更低，因为用户主要在骂慢；首单体验对复购的影响在这份数据里看不出来，因为 Olist 整体复购只有 4%。第三个我标的是『证据不足』而不是『不成立』，这个区别很重要，唯品会有会员体系和复购数据，可以真正回答这个问题。");
}

// ============================================================ 15 建议与测算
{
  const s = contentSlide({ duty: 3, title: "三项举措，可把品质客诉率从 5.00% 降到 3.82%", sub: "以 2018 年 1-8 月签收订单为基线；多项举措叠加时按 1 − Π(1 − p) 计算，避免重复" });
  const sz = D.sizing;
  // 瀑布图（形状绘制，数值与标注精确对齐）
  const x0 = MX, y0 = 2.1, ch = 3.9, cw = 6.6, maxV = 0.06;
  const yOf = v => y0 + ch * (1 - v / maxV);
  s.addShape(pres.shapes.LINE, { x: x0, y: y0 + ch, w: cw, h: 0, line: { color: C.gray, width: 1 } });
  const bars = [["现状", 0, sz.baseline_rate, C.teal, pct(sz.baseline_rate, 2)]];
  let level = sz.baseline_rate;
  sz.steps.forEach(st => { bars.push([st.code, level - st.delta_pp, level, C.orange, "−" + (st.delta_pp * 100).toFixed(2) + "pp"]); level -= st.delta_pp; });
  bars.push(["治理后", 0, level, C.teal, pct(level, 2)]);
  const bw = 0.8, gap = (cw - bars.length * bw) / (bars.length + 1);
  bars.forEach(([lab, lo, hi, col, vlab], i) => {
    const x = x0 + gap + i * (bw + gap);
    s.addShape(pres.shapes.RECTANGLE, { x, y: yOf(hi), w: bw, h: yOf(lo) - yOf(hi), fill: { color: col }, line: { color: col } });
    text(s, vlab, { x: x - 0.3, y: yOf(hi) - 0.38, w: bw + 0.6, h: 0.32, fontSize: 12, bold: true, align: "center", valign: "bottom" });
    text(s, lab, { x: x - 0.3, y: y0 + ch + 0.08, w: bw + 0.6, h: 0.3, fontSize: 12, align: "center", color: C.muted });
  });
  const sc = A.scenarios.scenarios;
  text(s, `三档情景：悲观 ${pct(sc["悲观"].rate, 2)} / 中性 ${pct(sc["中性"].rate, 2)} / 乐观 ${pct(sc["乐观"].rate, 2)}；最敏感的是 A（区间宽 ${(A.scenarios.tornado[0]["影响幅度"] * 100).toFixed(2)}pp）`,
    { x: MX, y: 6.5, w: 6.7, h: 0.45, fontSize: 11, color: C.teal, bold: true });
  // 举措卡片
  const acts = [
    ["A", "多件订单出库复核 + 分包裹提醒", "仓配 / 商家", "多件订单少件客诉 −50%", "多件订单少件率 14.4% → ≤ 7%"],
    ["B", "高风险 / 需关注商家整改", "商家管理", "该类商家品质客诉 −30%", "高风险商家数、整改闭环率"],
    ["C", "3C 数码 / 钟表礼品 正品与描述专项", "品控 + 类目", "两类目假货、货不对板客诉 −30%", "假货投诉率（每万单）、货不对板率"],
  ];
  acts.forEach(([c, n, owner, as, kpi], i) => {
    const x = 7.6, y = 1.95 + i * 1.55, w = W - MX - x;
    card(s, x, y, w, 1.45, C.grayLight);
    s.addShape(pres.shapes.OVAL, { x: x + 0.2, y: y + 0.2, w: 0.42, h: 0.42, fill: { color: C.orange }, line: { color: C.orange } });
    text(s, c, { x: x + 0.2, y: y + 0.2, w: 0.42, h: 0.42, fontSize: 14, bold: true, color: C.white, align: "center", valign: "middle" });
    text(s, n, { x: x + 0.78, y: y + 0.18, w: w - 1.0, h: 0.34, fontSize: 13.5, bold: true });
    text(s, `负责：${owner}`, { x: x + 0.78, y: y + 0.54, w: w - 1.0, h: 0.26, fontSize: 10.5, color: C.muted });
    text(s, `测算假设：${as}`, { x: x + 0.78, y: y + 0.8, w: w - 1.0, h: 0.26, fontSize: 10.5, color: C.muted });
    text(s, `跟踪指标：${kpi}`, { x: x + 0.78, y: y + 1.07, w: w - 1.0, h: 0.26, fontSize: 10.5, color: C.teal, bold: true });
  });
  s.addNotes(`最后是建议和测算。A 针对多件订单：出库时称重或扫码复核，分包裹时主动告知用户，假设少件客诉减半，能降 ${(sz.steps[0].delta_pp * 100).toFixed(2)} 个百分点，是收益最大的一项。B 针对高风险和需关注商家整改，假设降 30%。C 针对 3C 和钟表的假货与货不对板做正品专项。三项叠加时我按『一个客诉单被任一举措避免的概率』计算，避免重复计算，合计能从 5.00% 降到 3.82%，达到 4% 的目标线。这些假设比例是可以和业务一起校准的参数。`);
}

// ============================================================ 15b 差异化抽检
{
  const G = D.gain, SA = A.sampling;
  const s = contentSlide({ duty: 3, title: "质检资源按风险分配：少件靠订单结构锁定，缺陷和假货靠风险打分", sub: `样本外检验：用 ${SA.train} 的数据打分，在 ${SA.test} 的 ${num(SA.test_orders)} 个签收订单上检验` });
  const labels = G["抽检比例"].map((v, i) => (i % 2 ? "" : pct(v, 0)));
  const keys = ["出库复核：多件订单优先（少件问题）", "商家 × 品类风险分", "商家风险分", "随机抽检"];
  s.addChart(pres.charts.LINE, keys.map(k => ({ name: k, labels, values: G[k] })), Object.assign({}, axis, {
    x: MX, y: 1.95, w: 7.4, h: 4.55, chartColors: [C.orange, C.teal, C.tealMid, "B8BFC2"], lineSize: 2, lineDataSymbol: "none",
    valAxisLabelFormatCode: "0%", valAxisMinVal: 0, valAxisMaxVal: 1, showLegend: true, legendPos: "b", legendFontSize: 9,
    catAxisLabelFrequency: 2, showTitle: true, title: "增益曲线：抽检 / 复核 X% 的订单，能覆盖多少问题订单", titleFontSize: 12, titleColor: C.ink,
    catAxisTitle: "抽检比例（按风险分从高到低）", showCatAxisTitle: true, catAxisTitleFontSize: 10, catAxisTitleColor: C.muted,
  }));
  const x = 8.2, w = W - MX - x;
  const c10 = SA.capture_at_10;
  stat(s, x, 1.95, w, pct(c10["出库复核：多件订单优先（少件问题）"], 0), `出库复核只盯多件订单（占 ${pct(SA.multi_share, 0)}），就能覆盖的少件 / 漏发问题`, C.orange, 30);
  stat(s, x, 3.2, w, `${(c10["商家 × 品类风险分"] / c10["随机抽检"]).toFixed(2)} 倍`, `入仓抽检 10% 时，按"商家 × 品类"风险分覆盖 ${pct(c10["商家 × 品类风险分"], 1)} 的缺陷 / 货不对板 / 假货，随机抽检为 ${pct(c10["随机抽检"], 1)}`, C.teal, 30);
  card(s, x, 4.5, w, 1.95, C.grayLight);
  const scale = D.samr.find(r => r.product === "按企业规模");
  text(s, "外部先验支持分层抽检", { x: x + 0.2, y: 4.62, w: w - 0.4, h: 0.3, fontSize: 12, bold: true, color: C.teal });
  text(s, `2023 年国抽：${scale.note}；流通领域 19.6% vs 生产领域 6.7%。新 / 小供应商与流通环节应提高抽检比例；真实场景可加入供应商历史质检结果，风险分会更准。`,
    { x: x + 0.2, y: 4.97, w: w - 0.4, h: 1.4, fontSize: 10.5, color: C.ink });
  s.addNotes(`这一页把商家风险分层落到质检动作上，而且是样本外检验：用前 6 个月打分，在后 6 个月的订单上看效果，避免"用答案检验答案"。两类问题差别很大：少件漏发靠订单结构就能精准锁定，只复核占 10% 的多件订单，就能覆盖 75% 的少件问题；缺陷、货不对板、假货更分散，用商家乘以品类的风险分，同样 10% 的抽检量能覆盖约 16%，是随机抽检的 1.6 倍左右。这个提升不算大，因为公开数据里只有商家和品类两个特征；唯品会有供应商历史质检不合格率、品牌、价格带这些特征，风险分会准得多。检出率这个参数在两种方案里会约掉，所以倍数这个结论不依赖检出率的假设。`);
}

// ============================================================ 16 SQL 题库
{
  const s = contentSlide({ duty: 4, title: `SQL 取数：${D.sql_total} 道业务题，从「业务语言」到能跑的 SQL`, sub: "每题：业务原话 → 口径拆解 → 默认假设 → 分层 SQL → 自检 → 错误写法对比 → 追问；全部在 MySQL 8.0 实跑" });
  const rows = [
    ["难度", "题数", "代表题目", "考点"],
    ["基础", String(D.sql_levels["基础"]), "月度概览、评价去重、差评率 TOP10、明细导出", "条件聚合、ROW_NUMBER 去重、一对多先去重、半开区间"],
    ["进阶", String(D.sql_levels["进阶"]), "品质客诉率、类目内 TOP3、连续 3 月上升、中位数", "DENSE_RANK、LAG + 月份连续、分位数、递归 CTE 补 0"],
    ["高阶", String(D.sql_levels["高阶"]), "首单复购、帕累托、高风险商家、对账、连续 3 天", "customer_unique_id、累计窗口、贝叶斯平滑、Gaps & Islands"],
    ["开放", String(D.sql_levels["开放"]), "看板 4.97% vs 业务自己算的数", "cohort 口径 vs 事件时间口径"],
  ];
  s.addTable(rows.map((r, i) => r.map(t => ({ text: t, options: { bold: i === 0, color: i === 0 ? C.white : C.ink, fill: { color: i === 0 ? C.teal : (i % 2 ? C.white : C.grayLight) } } }))),
    { x: MX, y: 2.1, w: 7.3, colW: [0.8, 0.7, 2.9, 2.9], fontFace: FONT, fontSize: 11.5, border: { type: "solid", color: "E3E6E6", pt: 0.5 }, rowH: 0.62, valign: "middle" });
  const x = 8.2, w = W - MX - x;
  text(s, "错误写法 vs 正确写法（实跑结果）", { x, y: 2.1, w, h: 0.35, fontSize: 14, bold: true, color: C.teal });
  const cmp = [
    ["两张一对多表直接 JOIN 对账", "12,494 单", "249 单"],
    ["用 customer_id 算复购率", "0%", "2.8%"],
    ["多件订单 JOIN 商品行后计数", "12,790 单", "5,249 单"],
    ["口径：投诉月 ÷ 签收月", "5.25%", "4.97%"],
  ];
  cmp.forEach(([n, a, b], i) => {
    const y = 2.6 + i * 0.95;
    card(s, x, y, w, 0.82, C.grayLight);
    text(s, n, { x: x + 0.2, y: y + 0.1, w: w - 0.4, h: 0.3, fontSize: 12, bold: true });
    text(s, `错：${a}`, { x: x + 0.2, y: y + 0.44, w: 1.9, h: 0.3, fontSize: 12, color: C.red, bold: true });
    text(s, `对：${b}`, { x: x + 2.1, y: y + 0.44, w: w - 2.3, h: 0.3, fontSize: 12, color: C.green, bold: true });
  });
  text(s, "4 道题的结果与数仓、看板数字逐一对账一致（月度品质客诉率、准时率、高风险商家名单、3 月口径）", { x: MX, y: 5.45, w: 7.3, h: 0.7, fontSize: 12, color: C.muted });
  s.addNotes("SQL 部分我把品控业务可能提的临时需求整理成 19 道题。我认为取数最难的不是语法，而是把业务的一句话翻译成口径，所以每道题都从业务方原话出发，先写口径和假设。右边是四个最典型的错误：比如对账时把商品表和支付表这两张一对多的表直接 JOIN，对不上的订单会从 249 单虚高到 1.2 万单；用 customer_id 算复购率会得到 0，因为它是一单一个的。所有答案都实际跑过，其中 4 道和看板上的数字逐一对过账。");
}

// ============================================================ 17 数据质量与局限
{
  const s = contentSlide({ duty: 0, title: "对数字负责：校验做在前面，局限说在前面", sub: "" });
  card(s, MX, 1.7, 5.9, 3.75, C.tealLight);
  text(s, `数据质量：${D.dq_checks} 项自动校验全部通过`, { x: MX + 0.3, y: 1.9, w: 5.4, h: 0.4, fontSize: 16, bold: true, color: C.teal });
  bullets(s, [
    "完整性：ODS → DWD 不丢单、不重复；打标覆盖全部评价",
    "唯一性：宽表一单一行、评价一单一条",
    "一致性：宽表 = DWS = ADS = 看板，三层数字相等",
    "合理性：比率在 [0,1]、分子 ≤ 分母、品质客诉只来自 1-3 星",
    "已知问题公开披露：189 单时间倒挂、547 单重复评价、249 单金额对不上……各自写明处理方式",
  ], { x: MX + 0.3, y: 2.45, w: 5.3, h: 2.9, fontSize: 13 });
  const x = 6.85, w = W - MX - x;
  text(s, "局限与下一步", { x, y: 1.9, w, h: 0.4, fontSize: 16, bold: true });
  const lim = [
    ["打标偏保守", `随机盲评 200 条：准确率 ${pct(D.gold.precision, 0)}、召回率 ${pct(D.gold.recall, 0)}，品质客诉率被低估约 1/4；两年漏标比例相近，趋势不受影响`],
    ["没有质检数据", "入仓质检、抽检、拦截率已定义口径，待接入内部数据"],
    ["巴西市场 ≠ 唯品会", "方法可迁移，阈值（目标 4%、平滑 m=50）需用唯品会数据重估"],
    ["最近月份右删失", "评价与签收仍在回收，最后 1-2 个月的指标偏乐观，汇报时标注"],
  ];
  lim.forEach(([h, b], i) => {
    const y = 2.45 + i * 1.0;
    text(s, h, { x, y, w, h: 0.32, fontSize: 13.5, bold: true, color: C.orange });
    text(s, b, { x, y: y + 0.35, w, h: 0.58, fontSize: 11.5, color: C.ink });
  });
  s.addNotes("JD 里提到严谨细致、对数据准确性负责。我的做法是把校验做成脚本，每次跑数自动执行 18 项检查，任何一项失败就不出数；已知的脏数据不悄悄删掉，而是公开披露并写明处理方式。右边是这个项目的局限，我觉得主动讲清楚比被问到更好：评价不等于客诉，随机盲评显示规则准确率 97%、召回率 75%，会漏掉约四分之一的品质问题，所以绝对值偏低，但两年漏标比例相近，趋势结论成立；没有质检数据；阈值要用唯品会自己的数据重估。");
}

// ============================================================ 18 结尾
{
  const s = pres.addSlide();
  pageNo += 1;
  s.background = { color: C.ink };
  text(s, "如果入职，我会先做的三件事", { x: MX, y: 1.0, w: 12, h: 0.7, fontSize: 34, bold: true, color: C.white, valign: "middle" });
  const todo = [
    ["对齐口径", "把品质客诉率、品质退货率与现有指标字典对齐，确认时间归属和去重规则"],
    ["接入质检与退货", "补齐入仓质检合格率、问题商品拦截率，让结果指标和过程指标连起来"],
    ["先做一个专题", "从多件订单少件率或高风险供应商切入，做完一轮\"发现 → 举措 → 复盘\""],
  ];
  todo.forEach(([h, b], i) => {
    const x = MX + i * 4.1, y = 2.3, w = 3.8;
    s.addShape(pres.shapes.OVAL, { x, y, w: 0.55, h: 0.55, fill: { color: C.teal }, line: { color: C.teal } });
    text(s, String(i + 1), { x, y, w: 0.55, h: 0.55, fontSize: 18, bold: true, color: C.white, align: "center", valign: "middle" });
    text(s, h, { x, y: y + 0.8, w, h: 0.45, fontSize: 20, bold: true, color: C.white });
    text(s, b, { x, y: y + 1.35, w, h: 1.2, fontSize: 13, color: "C9D4D9" });
  });
  text(s, "项目材料：指标字典与商家品质月报模板（Excel）· 交互看板（HTML）· 专题分析报告（Word）· SQL 题库（19 题）· 全部代码与数据可一键复现",
    { x: MX, y: 5.5, w: 12, h: 0.5, fontSize: 13, color: "8FA0A8" });
  text(s, "谢谢！", { x: MX, y: 6.2, w: 6, h: 0.6, fontSize: 24, bold: true, color: C.tealMid });
  s.addNotes("最后说一下如果有机会入职，我会先做的三件事：先对齐口径，再接入质检和退货数据，然后挑一个专题跑完整个闭环。所有材料都可以一键复现，谢谢。");
}

// ============================================================ 附录
function appendix(title, sub) {
  const s = contentSlide({ duty: 0, title, sub });
  return s;
}
{
  const S = A.significance, SC = A.seller_ci;
  const s = appendix("附录①　统计检验：品质客诉率的上升不是随机波动", "面试追问\"这个差异显著吗\"时使用");
  const rows = [
    ["检验", "结果", "结论"],
    ["2017 vs 2018 品质客诉率（两比例 z 检验）", `z = ${S.qc.z.toFixed(2)}，p < 0.0001`, "显著上升"],
    ["95% 置信区间（Wilson）", `2017：${pct(S.qc.ci2017[0], 2)} – ${pct(S.qc.ci2017[1], 2)}；2018：${pct(S.qc.ci2018[0], 2)} – ${pct(S.qc.ci2018[1], 2)}`, "区间不重叠"],
    ["货不对板率 / 假货投诉率", `z = ${S.mismatch.z.toFixed(2)} / z = ${S.fake.z.toFixed(2)}（p = ${S.fake.p.toFixed(4)}）`, "均显著上升"],
    ["p 控制图（阶段Ⅰ 2017 基线）", `阶段Ⅰ 12 个月全部受控；2018 年 ${A.spc.beyond_ucl_months.length} 个月越出 UCL；连续 ${A.spc.max_run_above} 点高于中心线`, "过程均值偏移"],
    ["穿戴类 2017 vs 2018", `z = ${A.vip_view.wear_z.toFixed(2)}，p = ${A.vip_view.wear_p.toFixed(3)}`, "显著上升"],
    ["高风险商家（Wilson 下限 > 平台）", `${SC.high_risk_sig} / ${SC.high_risk_n} 家显著；不平滑时 ≥ 2 倍的 ${SC.raw2x_n} 家参评商家中 ${SC.raw2x_not_sig} 家不显著`, "平滑后名单可信"],
  ];
  s.addTable(rows.map((r, i) => r.map(t => ({ text: t, options: { bold: i === 0, color: i === 0 ? C.white : C.ink, fill: { color: i === 0 ? C.teal : (i % 2 ? C.white : C.grayLight) } } }))),
    { x: MX, y: 2.0, w: W - 2 * MX, colW: [4.0, 5.6, 2.53], fontFace: FONT, fontSize: 11.5, border: { type: "solid", color: "E3E6E6", pt: 0.5 }, rowH: 0.56, valign: "middle" });
  s.addNotes("两比例 z 检验：用合并比例算标准误，z 大于 1.96 就是 5% 水平显著。p 控制图用 2017 年做阶段Ⅰ基线，控制限是 p0 ± 3 倍根号 p0(1-p0)/n，n 是每月签收单，所以量大的月份控制限更窄。Wilson 区间在小样本时比正态近似更准，适合商家这种样本量差别很大的场景。");
}
{
  const s = appendix("附录②　评价打标的准确率与召回率", "随机 200 条（已签收 · 1-3 星 · 有文字）盲评；由大模型逐条读葡语原文判定，附中文释义供人工抽查");
  const g = D.gold_by_type;
  const rows = [["问题类型", "金标准条数", "准确率", "召回率"]].concat(
    Object.entries(g).map(([k, v]) => [k, String(v.support), v.precision == null ? "—" : pct(v.precision, 0), v.recall == null ? "—" : pct(v.recall, 0)]));
  rows.push(["合计（任一品质问题）", String(D.gold.support), pct(D.gold.precision, 1), pct(D.gold.recall, 1)]);
  s.addTable(rows.map((r, i) => r.map(t => ({ text: t, options: { bold: i === 0 || i === rows.length - 1, color: i === 0 ? C.white : C.ink, fill: { color: i === 0 ? C.teal : (i === rows.length - 1 ? C.tealLight : (i % 2 ? C.white : C.grayLight)) } } }))),
    { x: MX, y: 2.05, w: 6.4, colW: [2.2, 1.4, 1.4, 1.4], fontFace: FONT, fontSize: 12, border: { type: "solid", color: "E3E6E6", pt: 0.5 }, rowH: 0.5, valign: "middle" });
  const x = 7.5, w = W - MX - x, by = D.gold_by_year;
  stat(s, x, 2.0, w, `${pct(by["2017"].recall, 0)} vs ${pct(by["2018"].recall, 0)}`, "2017 / 2018 年召回率相近 → 两年对比不受漏标影响", C.teal, 28);
  stat(s, x, 3.3, w, `× ${D.gold_cf.toFixed(2)}`, `校正系数 = 准确率 ÷ 召回率；2018 年品质客诉率真实值约 ${pct(A.scenarios.baseline * D.gold_cf, 1)}`, C.orange, 28);
  text(s, "漏标主要是货不对板的多样说法（「寄来的和买的不像」「颜色型号被换」）和部分到货；下一步用这 200 条作为开发集迭代 v1.1，再抽一批新样本做测试集，避免在评估集上过拟合。逐条明细见 outputs/qa/tag_gold_set.csv。",
    { x, y: 4.7, w, h: 1.6, fontSize: 11.5, color: C.ink });
  s.addNotes("之前的 140 条复核是按规则打出的标签分层抽样，只能说明打上的准不准；这次随机抽样盲评，才能同时算召回率。规则准确率 97%，但召回率 75%，是偏保守的，品质客诉率的绝对值被低估了约四分之一。关键是两年的召回率接近，所以趋势和结构性的结论都不受影响。判定是借助大模型逐条读葡语原文完成的，每条都写了中文释义，方便人工抽查。");
}
{
  const s = appendix("附录③　商家风险分层回测：用前 6 个月的分层，预测后 6 个月", "排序在三个窗口里都成立：高风险 > 需关注 > 正常；同时能看到均值回归");
  const bt = A.backtest.rows;
  const wins = [...new Set(bt.map(r => r["检验窗口"]))];
  const get = (w_, g) => { const r = bt.find(x => x["检验窗口"] === w_ && x["分组"] === g); return r ? r["检验期倍数"] : 0; };
  s.addChart(pres.charts.BAR, ["高风险", "需关注", "正常"].map(g => ({ name: g, labels: wins.map(w_ => "检验期 " + w_), values: wins.map(w_ => get(w_, g)) })),
    Object.assign({}, axis, { x: MX, y: 1.95, w: 7.6, h: 4.5, barDir: "col", barGrouping: "clustered", barGapWidthPct: 50,
      chartColors: [C.red, C.amber, "C9CFD1"], valAxisLabelFormatCode: "0.0\"×\"", showValue: true, dataLabelFormatCode: "0.0\"×\"",
      dataLabelPosition: "outEnd", dataLabelFontSize: 9, dataLabelColor: C.ink, showLegend: true, legendPos: "b", legendFontSize: 10,
      valAxisMinVal: 0, valAxisMaxVal: 3, showTitle: true, title: "检验期品质客诉率 ÷ 平台", titleFontSize: 12, titleColor: C.ink }));
  const pl = A.backtest.pooled, x = 8.55, w = W - MX - x;
  stat(s, x, 2.0, w, `${pl["高风险"]["平均倍数"].toFixed(1)}×`, `高风险（3 个窗口合计 ${pl["高风险"]["窗口商家数"]} 家次）下一期仍为平台倍数`, C.red, 30);
  stat(s, x, 3.25, w, `${pl["不平滑：原始客诉率 ≥ 2 倍"]["平均倍数"].toFixed(2)}×`, `不平滑的规则圈出 ${pl["不平滑：原始客诉率 ≥ 2 倍"]["窗口商家数"]} 家次，下一期倍数更低：平滑用更少的名单换来更高的命中`, C.muted, 30);
  const hr = bt.filter(r => r["分组"] === "高风险" && r["检验期客诉率"] < r["训练期客诉率"]);
  text(s, `均值回归：${wins.length} 个窗口中有 ${hr.length} 个，高风险商家下一期客诉率明显回落（${hr.map(r => pct(r["训练期客诉率"], 1) + " → " + pct(r["检验期客诉率"], 1)).join("，")}）。所以评估整改效果必须设对照组，否则会把自然回落误判为整改成果。`,
    { x, y: 4.55, w, h: 1.8, fontSize: 11.5, color: C.ink });
  s.addNotes("回测的做法：用一个 6 个月窗口给商家分层，再看这些商家在下一个 6 个月的品质客诉率。三个窗口里高风险商家分别是平台的 2.1、2.6、1.9 倍，需关注 1.2 到 1.6 倍，正常 0.9 倍左右，排序每次都成立，说明模型有预测力。高风险每期只有 3 到 4 家，样本小，所以我看的是三个窗口合计。");
}
{
  const s = appendix("附录④　治理测算的情景与敏感性", "各举措降幅是假设参数；给出三档情景，并逐个变动参数看影响（其余参数取中性值）");
  const sc = A.scenarios.scenarios;
  const rows = [["情景", "A 多件订单少件客诉降幅", "B 风险商家客诉降幅", "C 3C/钟表假货与货不对板降幅", "治理后品质客诉率"]].concat(
    ["悲观", "中性", "乐观"].map(k => [k, pct(sc[k].params[0], 0), pct(sc[k].params[1], 0), pct(sc[k].params[2], 0), pct(sc[k].rate, 2)]));
  s.addTable(rows.map((r, i) => r.map(t => ({ text: t, options: { bold: i === 0, color: i === 0 ? C.white : C.ink, fill: { color: i === 0 ? C.teal : (i === 2 ? C.tealLight : (i % 2 ? C.white : C.grayLight)) } } }))),
    { x: MX, y: 2.0, w: W - 2 * MX, colW: [1.4, 2.8, 2.6, 3.0, 2.33], fontFace: FONT, fontSize: 12, border: { type: "solid", color: "E3E6E6", pt: 0.5 }, rowH: 0.5, valign: "middle" });
  const t = A.scenarios.tornado;
  const rows2 = [["单因素敏感性（其余取中性）", "悲观取值时", "乐观取值时", "影响幅度"]].concat(
    t.map(r => [r["参数"], pct(r["悲观时品质客诉率"], 2), pct(r["乐观时品质客诉率"], 2), (r["影响幅度"] * 100).toFixed(2) + "pp"]));
  s.addTable(rows2.map((r, i) => r.map(t_ => ({ text: t_, options: { bold: i === 0, color: i === 0 ? C.white : C.ink, fill: { color: i === 0 ? C.teal : (i % 2 ? C.white : C.grayLight) } } }))),
    { x: MX, y: 4.35, w: W - 2 * MX, colW: [5.2, 2.3, 2.3, 2.33], fontFace: FONT, fontSize: 12, border: { type: "solid", color: "E3E6E6", pt: 0.5 }, rowH: 0.5, valign: "middle" });
  s.addNotes("三档情景里，即使悲观情况也能降到 4.32%，乐观能到 3.34%；中性情景 3.82% 达到 4% 的目标。敏感性上 A 影响最大，所以上线后最该先验证的就是多件订单复核的真实效果，建议先在部分仓库试点，用双重差分评估。");
}

pres.writeFile({ fileName: path.join(ROOT, "ppt", "品控数据分析项目_面试汇报.pptx") }).then(f => console.log("写入", f));
