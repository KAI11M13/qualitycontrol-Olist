// 生成完整版 PPT：node ppt/build_deck.js
// 数字全部来自 outputs/deck_data.json（由 scripts/12_deck_data.py 从数仓导出），不手抄；
// 术语与数字格式以 docs/00_术语与口径.md 为准。每一页内容页的结构相同：模块标签 → 标题（结论）→ 关键术语 → 依据 → 动作。
const path = require("path");
const fs = require("fs");

const ROOT = path.resolve(__dirname, "..");
const D = JSON.parse(fs.readFileSync(path.join(ROOT, "outputs", "deck_data.json"), "utf8"));

const { C, FONT, W, MX, F, axis, monthLabels, createDeck } = require("./deck_kit");
const A = D.adv;   // 进阶分析结果（13_advanced_analysis.py）
const { pres, nextPage, text, contentSlide, card, stat, bullets, table } = createDeck("差评率在下降，品质客诉率在上升：电商品控数据分析项目");

const Q = "下单月 2017-01 至 2018-08";
const Q18 = "下单月 2018-01 至 2018-08";
const DC = D.decomp_category, MI = D.multi_item, T18 = D.type_by_year["2018M1-8"], T17 = D.type_by_year["2017"];
const SC = A.scenarios.scenarios, SA = A.sampling, V = A.wear_view, SPC = A.spc;
const fakeAll = D.fake_counts.fake / D.fake_counts.n;
const fakeCat = name => { const r = D.fake_top.find(x => x.main_category_cn === name); return r.fake / r.n; };
const BT = A.backtest.pooled;
const OT = { "1 单件": "单件订单", "2 同SKU多件": "同 SKU 多件", "3 单商家多SKU": "单商家多 SKU", "4 多商家": "多商家" };

// ============================================================ 1 封面
{
  const s = pres.addSlide();
  nextPage();
  s.background = { color: C.ink };
  text(s, "电商品控数据分析项目", { x: MX, y: 1.2, w: 10, h: 0.5, fontSize: 18, color: C.pink, bold: true });
  text(s, "差评率在下降，品质客诉率在上升", { x: MX, y: 1.8, w: 12.2, h: 1.1, fontSize: 44, bold: true, color: C.white, valign: "middle" });
  text(s, "指标体系 · 经营看板 · 专题分析 · SQL 取数", { x: MX, y: 2.95, w: 12, h: 0.55, fontSize: 22, color: C.onInk, valign: "middle" });
  const facts = [
    [F.int(D.counts.orders), "个订单（数据集全部订单）"], [F.int(D.counts.scope_delivered), `个签收订单（${Q}）`],
    [F.int(D.counts.sellers), "家商家"], [String(D.counts.categories), "个品类"],
  ];
  facts.forEach(([v, l], i) => {
    const x = MX + i * 3.0;
    text(s, v, { x, y: 4.55, w: 2.8, h: 0.6, fontSize: 30, bold: true, color: C.white, valign: "bottom" });
    text(s, l, { x, y: 5.2, w: 2.8, h: 0.55, fontSize: 12, color: C.onInkMuted });
  });
  text(s, "数据：Olist Brazilian E-Commerce Public Dataset（巴西电商平台公开的脱敏真实订单）", { x: MX, y: 6.55, w: 12, h: 0.35, fontSize: 12, color: C.onInkMuted, valign: "middle" });
  s.addNotes("这个项目用 Olist 巴西电商平台公开的真实订单数据，搭建了以品质客诉率为核心指标的品控分析，包括指标体系、经营看板、专题分析、SQL 取数四个模块。标题就是专题分析的结论：差评率在下降，品质客诉率在上升。");
}

// ============================================================ 2 核心概念
{
  const s = contentSlide({ mark: "·", label: "项目方法 · 核心概念", title: "全部内容围绕一个指标：品质客诉率",
    term: ["品质客诉率", "签收订单中，用户因商品本身的问题给出 1-3 星、并在评价文字里描述了该问题的订单所占的比例"],
    action: "后面每一页先给出这一页的关键术语；全部术语的定义见 docs/00_术语与口径.md" });
  card(s, MX, 2.05, W - 2 * MX, 0.7, C.ink);
  text(s, "品质客诉率　=　品质客诉订单数　÷　签收订单数　　（分子、分母按同一下单月归属）", { x: MX + 0.3, y: 2.05, w: W - 2 * MX - 0.6, h: 0.7, fontSize: 18, bold: true, color: C.white, valign: "middle" });
  const cols = [
    ["① 签收订单", "订单状态为\"已签收\"（delivered）且签收时间不为空的订单"],
    ["② 最后一次评价为 1-3 星", "评价：用户对一个订单的一次打分（1-5 星），可附文字\n最后一次评价：同一订单有多条评价时，提交时间最晚的一条"],
    ["③ 评价文字命中品质问题标签", "品质问题标签：用葡语关键词规则从评价文字中识别出的 5 类问题；一条评价可同时命中多类"],
  ];
  text(s, "品质客诉订单 = 同时满足以下三个条件的订单", { x: MX, y: 2.95, w: 8, h: 0.35, fontSize: 13, bold: true, color: C.pink });
  const cw = (W - 2 * MX - 0.4) / 3;
  cols.forEach(([h, b], i) => {
    const x = MX + i * (cw + 0.2);
    card(s, x, 3.35, cw, 1.35);
    text(s, h, { x: x + 0.2, y: 3.45, w: cw - 0.4, h: 0.35, fontSize: 13.5, bold: true });
    text(s, b, { x: x + 0.2, y: 3.83, w: cw - 0.4, h: 0.85, fontSize: 11, color: C.muted });
  });
  const tags = [["假货", "非正品、仿冒或非原装"], ["质量缺陷", "损坏、功能故障、做工差、临期过期"], ["货不对板", "错发，或颜色、尺码、型号、材质与描述不符"],
    ["少件漏发", "少发、漏发、缺配件、只收到部分商品"], ["包装破损", "外包装破损、被拆开或没有防护"]];
  text(s, "5 个品质问题标签（每个标签对应一个结果指标：命中该标签的品质客诉订单数 ÷ 签收订单数）", { x: MX, y: 4.85, w: 11, h: 0.35, fontSize: 13, bold: true, color: C.pink });
  const tw = (W - 2 * MX - 4 * 0.15) / 5;
  tags.forEach(([h, b], i) => {
    const x = MX + i * (tw + 0.15);
    card(s, x, 5.25, tw, 1.05, C.pinkTint);
    text(s, h, { x: x + 0.15, y: 5.32, w: tw - 0.3, h: 0.32, fontSize: 13, bold: true });
    text(s, b, { x: x + 0.15, y: 5.66, w: tw - 0.3, h: 0.6, fontSize: 10.5, color: C.muted });
  });
  s.addNotes("全部内容围绕一个指标：品质客诉率，等于品质客诉订单数除以签收订单数，分子分母按同一下单月归属。品质客诉订单要同时满足三个条件：是签收订单；最后一次评价为 1 到 3 星；评价文字命中至少一个品质问题标签。品质问题标签有 5 类：假货、质量缺陷、货不对板、少件漏发、包装破损，每一类对应一个结果指标。");
}

// ============================================================ 3 四个模块
{
  const s = contentSlide({ mark: "·", label: "项目方法 · 项目结构", title: "四个模块，都从同一张订单宽表计算",
    term: ["订单宽表", "每个订单一行、汇总订单、商品、评价和标签信息的明细表（dwd_qc_order）；看板、报告、SQL 取数的指标都从这张表计算"],
    action: `每次运行先执行 ${D.dq_checks} 项数据校验，全部通过才输出结果` });
  const items = [
    [1, "指标体系", `${D.metric_count} 个指标，${D.metric_live} 个已用公开数据实现`, "指标字典：定义、公式、口径 SQL、基准值、预警规则；六条口径规则；口径变更记录"],
    [2, "经营看板", "3 页交互看板 + BI 工具搭建指南", "经营总览（含预警清单）、商家分层、指标口径；附 Power BI 与 Tableau 的搭建步骤、Excel 商家品质月报模板"],
    [3, "专题分析", "定位 3 个问题，测算 3 项举措", `因素分解、订单结构、商家分层、品类；中性情景下品质客诉率从 ${F.qc(A.scenarios.baseline)} 降到 ${F.qc(SC["中性"].rate)}`],
    [4, "SQL 取数", `${D.sql_total} 道业务取数题，全部实际运行`, "业务原话 → 口径 → SQL → 自检 → 错误写法对比；4 道与看板数字逐一核对一致；5 道另有 Hive / Spark SQL 版本"],
  ];
  items.forEach(([n, t, head, body], i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = MX + col * 6.13, y = 2.1 + row * 2.15, w = 5.93, h = 1.98;
    card(s, x, y, w, h, i % 3 === 0 ? C.pinkTint : C.grayLight);
    s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: y + 0.25, w: 0.42, h: 0.42, fill: { color: C.pink }, line: { color: C.pink } });
    text(s, String(n), { x: x + 0.3, y: y + 0.25, w: 0.42, h: 0.42, fontSize: 16, bold: true, color: C.white, align: "center", valign: "middle" });
    text(s, `模块${"①②③④"[n - 1]} ${t}`, { x: x + 0.9, y: y + 0.25, w: w - 1.2, h: 0.42, fontSize: 17, bold: true, valign: "middle" });
    text(s, head, { x: x + 0.3, y: y + 0.8, w: w - 0.6, h: 0.38, fontSize: 14, bold: true, color: C.pink });
    text(s, body, { x: x + 0.3, y: y + 1.2, w: w - 0.6, h: 0.72, fontSize: 11.5, color: C.muted });
  });
  s.addNotes("项目分四个模块：指标体系、经营看板、专题分析、SQL 取数。四个模块的数字都从同一张订单宽表计算：指标字典里每个指标的基准值，是直接运行字典里的口径 SQL 得到的，所以看板、报告和 SQL 题的数字能互相对上。每次运行先执行数据校验，任一项不通过就不输出结果。");
}

// ============================================================ 4 数据与标签
{
  const G = D.gold;
  const s = contentSlide({ mark: "·", label: "项目方法 · 数据与标签", title: "公开数据没有客诉记录，用评价星级和评价文字识别品质问题",
    term: ["标注样本", `从 ${F.int(D.gold_population)} 条"签收订单、最后一次评价 1-3 星、有文字"的评价中随机抽取的 200 条；由大模型逐条阅读葡语原文给出真实标签（判定时不看规则结果）`],
    action: "迭代识别规则后，另抽一批新样本评估，避免只在同一批样本上调规则" });
  const layers = [["ODS", "原始数据 8 张表", "行数与源文件逐一核对"], ["DWD", "清洗 + 订单宽表", "只取最后一次评价、主品类归属"],
    ["DWS", "商家 / 品类 × 月", "只存订单数，不存比率"], ["ADS", "看板与商家分层", "月度核心指标、商家品质分"]];
  layers.forEach(([k, a, b], i) => {
    const x = MX + i * 3.08, y = 2.05, w = 2.75, h = 1.35;
    card(s, x, y, w, h, i === 1 ? C.pinkTint : C.grayLight);
    text(s, k, { x: x + 0.25, y: y + 0.12, w: 1.2, h: 0.42, fontSize: 20, bold: true, color: C.pink });
    text(s, a, { x: x + 0.25, y: y + 0.56, w: w - 0.4, h: 0.3, fontSize: 12.5, bold: true });
    text(s, b, { x: x + 0.25, y: y + 0.88, w: w - 0.4, h: 0.4, fontSize: 10.5, color: C.muted });
    if (i < 3) text(s, "›", { x: x + w + 0.02, y: y + 0.35, w: 0.3, h: 0.6, fontSize: 28, bold: true, color: C.gray, align: "center", valign: "middle" });
  });
  table(s, [
    ["品控环节", "本项目数据"],
    ["供应商 / 品牌方", `Olist 商家（${F.int(D.counts.sellers)} 家）`],
    ["客诉记录", "最后一次评价的星级 + 葡语评价文字"],
    ["发货时效", "平台规定发货时限（shipping_limit_date）"],
    ["入仓质检 / 退货原因", "公开数据没有 → 定义为待接入指标"],
  ], { x: MX, y: 3.6, w: 6.1, colW: [2.2, 3.9], rowH: 0.52 });
  const x = 7.05, w = W - MX - x;
  card(s, x, 3.6, w, 2.6, C.pinkTint);
  text(s, "评价文字 → 8 个标签", { x: x + 0.25, y: 3.72, w: w - 0.5, h: 0.35, fontSize: 14, bold: true });
  bullets(s, [
    "品质问题标签 5 个：假货、质量缺陷、货不对板、少件漏发、包装破损",
    "履约服务标签 3 个：未收到货、物流延迟、服务售后（不计入品质客诉订单）",
    `标签精确率 ${F.share(G.precision)}：规则判为品质问题的 ${G.predicted} 条中，标注样本也判为品质问题的 ${G.tp} 条`,
    `标签召回率 ${F.share(G.recall)}：标注样本判为品质问题的 ${G.support} 条中，规则也判为品质问题的 ${G.tp} 条`,
  ], { x: x + 0.25, y: 4.12, w: w - 0.5, h: 2.0, fontSize: 11.5 });
  s.addNotes(`公开数据里没有客诉记录，所以用最后一次评价的星级和评价文字来识别品质问题：葡语关键词规则识别出 8 个标签，其中 5 个是品质问题标签。规则的准不准用标注样本评估：随机抽 200 条，由大模型逐条读原文判定，每条附中文释义方便人工抽查。标签精确率 ${F.share(G.precision)}，标签召回率 ${F.share(G.recall)}，规则偏保守，品质客诉率的绝对值偏低。数仓分四层，汇总层只存订单数，比率在最后一步计算。`);
}

// ============================================================ 5 指标层级
{
  const s = contentSlide({ mark: 1, label: "模块① 指标体系", title: "指标分四层：核心指标、结果指标、体验指标、过程指标",
    term: ["核心指标", "衡量品控结果、用于考核的唯一指标，本项目为品质客诉率"],
    action: "考核只用核心指标；结果指标变差时，顺着品控环节找对应的过程指标" });
  const cx = W / 2;
  card(s, cx - 3.6, 2.05, 7.2, 0.95, C.pink);
  text(s, "核心指标　品质客诉率", { x: cx - 3.5, y: 2.1, w: 7.0, h: 0.42, fontSize: 16, bold: true, color: C.white, align: "center", valign: "middle" });
  text(s, `${Q18}：${F.qc(A.scenarios.baseline)}　｜　中心线（2017 年）：${F.qc(SPC.p0)}`, { x: cx - 3.5, y: 2.52, w: 7.0, h: 0.4, fontSize: 12, color: C.white, align: "center", valign: "middle" });
  const l1 = [["少件漏发客诉率", F.qc(T18.missing)], ["质量缺陷客诉率", F.qc(T18.defect)], ["货不对板客诉率", F.qc(T18.mismatch)],
    ["假货客诉率", F.fake(T18.fake)], ["包装破损客诉率", F.qc(T18.package)]];
  text(s, `结果指标：按品质问题标签拆开（${Q18}）`, { x: MX, y: 3.2, w: 7.5, h: 0.3, fontSize: 12, bold: true, color: C.pink });
  l1.forEach(([n, v], i) => {
    const x = MX + i * 1.62, y = 3.55;
    card(s, x, y, 1.5, 0.95, C.pinkTint);
    text(s, n, { x: x + 0.1, y: y + 0.1, w: 1.35, h: 0.3, fontSize: 10.5, bold: true });
    text(s, v, { x: x + 0.1, y: y + 0.45, w: 1.35, h: 0.4, fontSize: n === "假货客诉率" ? 12 : 14.5, bold: true, color: C.pink, valign: "middle" });
  });
  card(s, MX + 8.3, 3.55, 3.83, 0.95, C.grayLight);
  text(s, "体验指标：差评率、平均评分、差评品质原因占比", { x: MX + 8.45, y: 3.62, w: 3.6, h: 0.35, fontSize: 11.5, bold: true });
  text(s, "受物流和服务影响，只观察，不用于考核品控", { x: MX + 8.45, y: 3.98, w: 3.6, h: 0.35, fontSize: 10.5, color: C.muted });
  text(s, "过程指标：按品控环节拆开（在用户签收之前就能观测）", { x: MX, y: 4.72, w: 8, h: 0.3, fontSize: 12, bold: true, color: C.pink });
  const l2 = [
    ["商品准入", "动销商品信息完整率\n高风险品类订单占比"],
    ["商家管理", "发货超时率 · 商家品质分\n高风险商家数"],
    ["仓配履约", "准时签收率\n多件订单少件漏发客诉率"],
    ["待接入（内部数据）", "入仓质检合格率 · 问题商品拦截率\n品质退货率"],
  ];
  l2.forEach(([n, v], i) => {
    const x = MX + i * 3.08, y = 5.07;
    card(s, x, y, 2.9, 1.2, i === 3 ? C.white : C.grayLight);
    if (i === 3) s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 2.9, h: 1.2, rectRadius: 0.08, fill: { color: C.white }, line: { color: C.gray, dashType: "dash", width: 1 } });
    text(s, n, { x: x + 0.2, y: y + 0.12, w: 2.6, h: 0.32, fontSize: 12.5, bold: true, color: i === 3 ? C.muted : C.ink });
    text(s, v, { x: x + 0.2, y: y + 0.5, w: 2.6, h: 0.65, fontSize: 10.5, color: C.muted });
  });
  s.addNotes(`指标体系分四层。核心指标是品质客诉率，${Q18} 为 ${F.qc(A.scenarios.baseline)}。结果指标是它按 5 个品质问题标签拆开的 5 个指标；一个订单可以同时命中多个标签，所以 5 个结果指标相加大于品质客诉率。体验指标是差评率这类受物流和服务影响的指标，只观察不考核。过程指标按品控环节拆开：商品准入、商家管理、仓配履约，以及需要内部数据的待接入指标；结果指标变差时，顺着环节往前找过程指标。`);
}

// ============================================================ 6 口径规则
{
  const cal = D.caliber_2018_03;
  const s = contentSlide({ mark: 1, label: "模块① 指标体系 · 口径规则", title: "六条口径规则，保证看板、报告、SQL 取数算出同一个数",
    term: ["按下单月归属", "一个订单的分子、分母都记在它的下单月，保证分子和分母是同一批订单"],
    action: "口径变更记入指标字典的\"口径变更记录\"工作表，并通知使用方" });
  const nts = D.known_issues;
  const rules = [
    ["按下单月归属", `下单月 2018-03：按下单月归属为 ${F.qc(cal.a)}；分子按评价月、分母按签收月则为 ${F.qc(cal.b)}，分子分母不是同一批订单`],
    ["签收订单", `订单状态为已签收且签收时间不为空；源数据有 ${F.int(nts["订单状态为已签收（delivered）但签收时间为空"])} 个订单状态为已签收、但没有签收时间`],
    ["只取最后一次评价", `源数据有 ${F.int(nts["同一订单多条评价"])} 个订单有多条评价，只使用提交时间最晚的一条`],
    ["品质客诉订单只认 1-3 星", "4-5 星评价里的\"sem defeito（没有瑕疵）\"会被关键词误识别"],
    ["一个订单可命中多个标签", "5 个结果指标之和大于品质客诉率，不能相加；需要互斥的结构占比时用主标签"],
    ["比率在最后一步计算", "汇总表只存订单数；各品类品质客诉率的简单平均 ≠ 全部签收订单的品质客诉率"],
  ];
  rules.forEach(([h, b], i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = MX + col * 4.1, y = 2.05 + row * 1.58, w = 3.9, hh = 1.45;
    card(s, x, y, w, hh, C.grayLight);
    text(s, String(i + 1), { x: x + 0.2, y: y + 0.13, w: 0.4, h: 0.4, fontSize: 20, bold: true, color: C.pink });
    text(s, h, { x: x + 0.62, y: y + 0.15, w: w - 0.8, h: 0.36, fontSize: 13.5, bold: true, valign: "middle" });
    text(s, b, { x: x + 0.2, y: y + 0.6, w: w - 0.4, h: 0.8, fontSize: 10.5, color: C.muted });
  });
  text(s, "口径变更记录", { x: MX, y: 5.3, w: 3, h: 0.3, fontSize: 12, bold: true, color: C.pink });
  const vs = [["v0.1", "关键词命中即计入"], ["v0.2", "限定 1-3 星 + 剔除否定句"], ["v0.3", "包装破损从质量缺陷中剥离"], ["v0.4", "复核 140 条，修正 8 条规则"], ["v1.0", "口径冻结，四个模块同源"]];
  s.addShape(pres.shapes.LINE, { x: MX + 0.1, y: 5.9, w: 11.9, h: 0, line: { color: C.gray, width: 1 } });
  vs.forEach(([v, d], i) => {
    const x = MX + i * 2.45;
    s.addShape(pres.shapes.OVAL, { x: x + 0.02, y: 5.81, w: 0.18, h: 0.18, fill: { color: i === 4 ? C.pink : C.white }, line: { color: C.pink, width: 1.5 } });
    text(s, v, { x: x + 0.3, y: 5.63, w: 0.8, h: 0.28, fontSize: 12, bold: true, color: C.pink });
    text(s, d, { x: x + 0.3, y: 5.95, w: 2.1, h: 0.35, fontSize: 10.5, color: C.muted });
  });
  s.addNotes(`六条口径规则，每一条都对应一个真实的数据问题。比如第一条按下单月归属：下单月 2018-03 按下单月归属是 ${F.qc(cal.a)}；如果分子按评价月、分母按签收月，算出来是 ${F.qc(cal.b)}。两个数都没算错，但后者的分子分母不是同一批订单。下方是口径变更记录，每个版本改了什么、为什么改，都记在指标字典里。`);
}

// ============================================================ 7 看板
{
  const s = contentSlide({ mark: 2, label: "模块② 经营看板", title: "看板第一屏回答\"好不好\"，第二屏回答\"在哪里\"",
    term: ["预警清单", "看板第一屏的三类预警：控制图越限的月份、品质客诉率连续 3 个月上升的主品类、按评价日期连续 3 天及以上每天都有品质客诉订单的商家"],
    action: "预警触发后点一下即可筛选到对应的一级类目，或跳到商家分层页" });
  const img = path.join(ROOT, "docs", "images", "dashboard_overview_top.png");
  s.addImage({ path: img, x: MX, y: 2.15, w: 6.8, h: 6.8 * 1640 / 2720 });
  s.addShape(pres.shapes.RECTANGLE, { x: MX, y: 2.15, w: 6.8, h: 6.8 * 1640 / 2720, fill: { type: "none" }, line: { color: C.line, width: 0.75 } });
  const x = 7.75, w = W - MX - x;
  const pts = [
    ["第一屏：好不好", "核心指标、体验指标与上期对比；品质客诉率控制图；预警清单"],
    ["第二屏：在哪里", "结果指标本期与上期对比；一级类目、订单结构、主品类明细"],
    ["比率在最后一步计算", "汇总表只存订单数，任意筛选组合下都先求和再相除"],
    ["口径可查", "第三页直接展示指标字典和六条口径规则"],
  ];
  pts.forEach(([h, b], i) => {
    const y = 2.05 + i * 1.07;
    text(s, h, { x, y, w, h: 0.34, fontSize: 13.5, bold: true, color: C.pink });
    text(s, b, { x, y: y + 0.36, w, h: 0.65, fontSize: 11.5, color: C.ink });
  });
  s.addNotes("看板有三页：经营总览、商家分层、指标口径。第一屏回答好不好：核心指标单独放大，带上期对比和控制图状态；预警清单把三类预警放在一起，规则与 SQL 题库的预警题相同。第二屏回答在哪里：结果指标、一级类目、订单结构和主品类明细。汇总表只存订单数，任何筛选组合下都是先求和再相除。另外有 Power BI、Tableau 搭建指南和 Excel 商家品质月报模板。");
}

// ============================================================ 8 专题分析框架
{
  const s = contentSlide({ mark: 3, label: "模块③ 专题分析 · 分析框架", title: "差评率在下降，品质客诉率在上升：先判断是不是真变了，再找原因",
    term: ["差评率", "最后一次评价为 1-2 星（差评）的订单数 ÷ 有评价的订单数；受物流和服务影响，属于体验指标"],
    action: "按\"结论 → 问题 → 举措\"的顺序展开，下面每一页回答一个问题" });
  const steps = [
    ["判断", "品质客诉率是持续偏移\n还是随机波动？"], ["结构", "差评里品质问题\n的占比怎么变？"], ["因素分解", "来自结构效应\n还是组内效应？"],
    ["定位问题", "订单结构 · 商家\n品类 · 商品信息"], ["证伪", "新商家？晚到损坏？\n影响复购？"], ["治理测算", "三项举措能降到多少？"],
  ];
  steps.forEach(([h, b], i) => {
    const x = MX + i * 2.05, y = 2.1, w = 1.85;
    card(s, x, y, w, 2.05, i === 3 ? C.pinkTint : C.grayLight);
    text(s, String(i + 1), { x: x + 0.2, y: y + 0.15, w: 0.5, h: 0.45, fontSize: 22, bold: true, color: C.pink });
    text(s, h, { x: x + 0.2, y: y + 0.65, w: w - 0.3, h: 0.4, fontSize: 16, bold: true });
    text(s, b, { x: x + 0.2, y: y + 1.1, w: w - 0.3, h: 0.85, fontSize: 11, color: C.muted });
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: MX, y: 4.4, w: W - 2 * MX, h: 1.85, rectRadius: 0.08, fill: { color: C.grayLight }, line: { color: C.grayLight } });
  text(s, "结论", { x: MX + 0.3, y: 4.52, w: 3, h: 0.35, fontSize: 13, bold: true, color: C.pink });
  text(s, `品质客诉率从 2017 年的 ${F.qc(DC.rate_A)} 升到 ${Q18} 的 ${F.qc(DC.rate_B)}（z = ${F.z(A.significance.qc.z)}，${F.p(A.significance.qc.p)}），控制图上连续 ${SPC.max_run_above} 个月高于中心线；同期差评率随准时签收率回落。上升来自组内效应（${F.pp(DC.within_effect)}），集中在多件订单、高风险商家和假货三处。`,
    { x: MX + 0.3, y: 4.92, w: W - 2 * MX - 0.6, h: 1.25, fontSize: 13.5, color: C.ink });
  s.addNotes("专题分析的出发点是一个反直觉的现象：差评率在下降，品质客诉率却在上升。分析按六步展开：先用控制图判断是不是真的变了；再看差评结构；然后用因素分解区分结构效应和组内效应；接着定位问题；再证伪三个直觉上成立的假设；最后测算举措的效果。");
}

// ============================================================ 9 结论① 控制图
{
  const s = contentSlide({ mark: 3, label: "模块③ 专题分析 · 结论①", title: "品质客诉率持续偏移；差评率跟着准时签收率变化",
    term: ["持续偏移", "控制图上连续 9 个及以上月份落在中心线同一侧，说明变化不是随机波动"],
    action: "考核品控用品质客诉率，差评率只作为体验指标观察" });
  const labels = monthLabels(D.months), p0 = SPC.p0;
  s.addChart(pres.charts.LINE, [
    { name: "品质客诉率", labels, values: D.p_chart.p },
    { name: "上控制限", labels, values: D.p_chart.ucl },
    { name: "下控制限", labels, values: D.p_chart.lcl },
    { name: `中心线 ${F.qc(p0)}（2017 年品质客诉率）`, labels, values: labels.map(() => p0) },
  ], Object.assign({}, axis, {
    x: MX, y: 2.0, w: 7.4, h: 3.75, chartColors: [C.pink, C.gray, C.gray, C.ink], lineSize: 2, lineDataSymbol: "none",
    valAxisLabelFormatCode: "0.0%", valAxisMinVal: 0.02, valAxisMaxVal: 0.065, valAxisMajorUnit: 0.005, showLegend: true, legendPos: "b",
    legendFontSize: 9, catAxisLabelFontSize: 9, catAxisLabelRotate: 0,
  }));
  text(s, `越限：${SPC.beyond_ucl_months.join("、")}，当月品质客诉率高于上控制限；持续偏移：2017-10 至 2018-08 连续 ${SPC.max_run_above} 个月高于中心线`,
    { x: MX, y: 5.8, w: 7.4, h: 0.5, fontSize: 11, color: C.ink, bold: true });
  const small = (vals, title, y, lo, hi) => s.addChart(pres.charts.LINE, [{ name: title, labels, values: vals }], Object.assign({}, axis, {
    x: 8.2, y, w: 4.55, h: 2.05, chartColors: [C.muted], lineSize: 2, lineDataSymbol: "none", valAxisLabelFormatCode: "0%",
    valAxisMinVal: lo, valAxisMaxVal: hi, showLegend: false, showTitle: true, title, titleFontSize: 11, titleColor: C.ink,
    catAxisLabelFontSize: 7.5, valAxisLabelFontSize: 9, catAxisLabelRotate: 0,
  }));
  small(D.bad_rate, `差评率（2018-03 为 ${F.share(D.bad_rate[14])}）`, 2.0, 0.05, 0.25);
  small(D.on_time_rate, `准时签收率（2018-03 为 ${F.share(D.on_time_rate[14])}）`, 4.2, 0.75, 1.0);
  const lm = SPC.last_month_check;
  s.addNotes(`左边是品质客诉率的控制图：中心线是 2017 年的品质客诉率 ${F.qc(p0)}，控制限是中心线加减 3 倍标准差、随当月签收订单数变化。2017 年 12 个月都在控制限内；2018 年有 ${SPC.beyond_ucl_months.length} 个月越限，而且从 2017 年 10 月起连续 ${SPC.max_run_above} 个月高于中心线，是持续偏移。两期对比的 z 检验 z = ${F.z(A.significance.qc.z)}，${F.p(A.significance.qc.p)}。右边两张是差评率和准时签收率，形状几乎是镜像：2018 年 3 月准时签收率降到 ${F.share(D.on_time_rate[14])}，差评率升到 ${F.share(D.bad_rate[14])}。最后一个月品质客诉率回落到 ${F.qc(lm.aug_rate)}：8 月的评价回收率与 7 月相当，但与 7 月的差异不显著（${F.p(lm.p)}），仍在控制限内，只作为回落信号继续观察。`);
}

// ============================================================ 10 结论② 差评结构
{
  const s = contentSlide({ mark: 3, label: "模块③ 专题分析 · 结论②", title: `差评品质原因占比从 ${F.share(D.mix.quality[0])} 升到 ${F.share(D.mix.quality[6])}`,
    term: ["差评品质原因占比", "最后一次评价为差评的订单中，主标签属于品质问题标签的订单所占的比例（分母含无文字的差评）"],
    action: "物流问题缓解之后，差评里剩下的品质问题交给品控治理" });
  const names = [["quality", "主标签为品质问题标签"], ["fulfill", "主标签为履约服务标签"], ["other", "有文字、未命中标签"], ["notext", "无文字"]];
  const qlabels = D.quarters.map(q => q === "2018Q3" ? "2018Q3（7、8 月）" : q);
  s.addChart(pres.charts.BAR, names.map(([k, n]) => ({ name: n, labels: qlabels, values: D.mix[k] })), Object.assign({}, axis, {
    x: MX, y: 2.0, w: 8.3, h: 4.3, barDir: "col", barGrouping: "percentStacked", barGapWidthPct: 70,
    chartColors: [C.pink, C.ink, C.amber, C.gray], valAxisLabelFormatCode: "0%",
    showLegend: true, legendPos: "b", legendFontSize: 10, showValue: false,
  }));
  const q = D.mix.quality, f = D.mix.fulfill;
  stat(s, 9.3, 2.05, 3.4, `${F.share(q[0])} → ${F.share(q[6])}`, "差评品质原因占比：下单季度 2017Q1 → 2018Q3", C.pink, 28);
  stat(s, 9.3, 3.45, 3.4, `${F.share(f[4])} → ${F.share(f[6])}`, "主标签为履约服务标签的差评占比：2018Q1 → 2018Q3", C.ink, 28);
  text(s, "差评按主标签分类，每个差评只属于一类；2018Q3 只有 7、8 两个月。", { x: 9.3, y: 4.9, w: 3.4, h: 1.2, fontSize: 12, color: C.muted });
  s.addNotes(`这张图把每个季度的差评按主标签分成四类。玫红色是主标签为品质问题标签的差评，2017 年一季度占 ${F.share(q[0])}，2018 年三季度升到 ${F.share(q[6])}；黑色的履约服务类在 2018 年一季度物流出问题时最高，之后回落。物流问题缓解以后，差评里的品质问题越来越突出。`);
}

// ============================================================ 11 结论③ 因素分解
{
  const s = contentSlide({ mark: 3, label: "模块③ 专题分析 · 结论③", title: "上升来自组内效应：同一类目自身在变差",
    term: ["组内效应", "Σ（2017 年各一级类目签收订单占比 × 该类目品质客诉率的变化）；与之相对，结构效应是各类目占比变化带来的变化"],
    action: "治理对象是具体类目里的订单、商家和商品，而不是调整品类结构" });
  card(s, MX, 2.0, 4.4, 4.3, C.grayLight);
  text(s, `因素分解（按一级类目）：品质客诉率 ${F.pp(DC.rate_B - DC.rate_A)}`, { x: MX + 0.3, y: 2.12, w: 3.9, h: 0.5, fontSize: 12.5, bold: true });
  const rows = [["组内效应", DC.within_effect, "同一类目自身品质客诉率的变化"], ["结构效应", DC.mix_effect, "各类目签收订单占比的变化"], ["交互项", DC.interaction, "占比变化 × 品质客诉率变化"]];
  rows.forEach(([n, v, d], i) => {
    const y = 2.72 + i * 1.02;
    text(s, n, { x: MX + 0.3, y, w: 1.6, h: 0.4, fontSize: 14, bold: true, valign: "middle" });
    text(s, F.pp(v), { x: MX + 1.9, y, w: 2.2, h: 0.4, fontSize: 24, bold: true, color: i === 0 ? C.pink : C.muted, valign: "middle", align: "right" });
    text(s, d, { x: MX + 0.3, y: y + 0.45, w: 3.8, h: 0.3, fontSize: 10.5, color: C.muted });
  });
  const top = Object.keys(D.decomp_category_top);
  text(s, `组内效应最大的一级类目：${top.join("、")}`, { x: MX + 0.3, y: 5.75, w: 3.9, h: 0.5, fontSize: 11, color: C.ink });
  const names = [["missing", "少件漏发客诉率"], ["defect", "质量缺陷客诉率"], ["mismatch", "货不对板客诉率"], ["package", "包装破损客诉率"]];
  s.addChart(pres.charts.BAR, [
    { name: "2017 年", labels: names.map(n => n[1]), values: names.map(n => T17[n[0]]) },
    { name: "2018 年 1-8 月", labels: names.map(n => n[1]), values: names.map(n => T18[n[0]]) },
  ], Object.assign({}, axis, {
    x: 5.3, y: 2.0, w: 7.45, h: 3.55, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60,
    chartColors: [C.gray, C.pink], valAxisLabelFormatCode: "0.0%", showValue: true, dataLabelFormatCode: "0.00%",
    dataLabelFontSize: 9, dataLabelColor: C.ink, dataLabelPosition: "outEnd", showLegend: true, legendPos: "t", legendFontSize: 10,
    catAxisLabelFontSize: 9.5, showTitle: true, title: "结果指标（命中该标签的品质客诉订单数 ÷ 签收订单数）", titleFontSize: 11, titleColor: C.ink,
  }));
  text(s, `假货客诉率：2017 年 ${F.fake(T17.fake)} → 2018 年 1-8 月 ${F.fake(T18.fake)}（以"单/万单"表示，未画入左图）`,
    { x: 5.4, y: 5.65, w: 7.3, h: 0.6, fontSize: 12, bold: true, color: C.ink });
  s.addNotes(`品质客诉率上升 ${F.pp(DC.rate_B - DC.rate_A)}，先要回答：是不是卖了更多高品质客诉率的类目？因素分解按一级类目把变化拆成三部分：组内效应 ${F.pp(DC.within_effect)}，结构效应 ${F.pp(DC.mix_effect)}，交互项 ${F.pp(DC.interaction)}。上升几乎全部来自组内效应，也就是同一类目自身在变差。再看结果指标：货不对板客诉率从 ${F.qc(T17.mismatch)} 升到 ${F.qc(T18.mismatch)}，假货客诉率从 ${F.fake(T17.fake)} 升到 ${F.fake(T18.fake)}，质量缺陷客诉率变化较小。`);
}

// ============================================================ 12 问题① 多件订单
{
  const s = contentSlide({ mark: 3, label: "模块③ 专题分析 · 问题①", title: `多件订单占签收订单 ${F.share(MI.order_share)}，贡献 ${F.share(MI.qc_share)} 的品质客诉订单`,
    term: ["多件订单", "件数不少于 2 的签收订单（件数 = 订单包含的商品行数），分为同 SKU 多件、单商家多 SKU、多商家三类"],
    action: "举措 A：多件订单出库复核 + 分包裹提醒" });
  const ot = D.order_type, keys = Object.keys(ot).sort();
  const labels = keys.map(k => `${OT[k]}：${F.qc(ot[k].qc)}`);
  s.addChart(pres.charts.BAR, [
    { name: "命中少件漏发标签", labels, values: keys.map(k => ot[k].missing) },
    { name: "未命中少件漏发标签", labels, values: keys.map(k => Math.max(0, ot[k].qc - ot[k].missing)) },
  ], Object.assign({}, axis, {
    x: MX, y: 2.0, w: 7.6, h: 4.3, barDir: "bar", barGrouping: "stacked", barGapWidthPct: 55,
    chartColors: [C.ink, C.pink], valAxisLabelFormatCode: "0%", showValue: false, catAxisLabelFontSize: 11,
    showLegend: true, legendPos: "t", legendFontSize: 10, valAxisMinVal: 0,
    catAxisOrientation: "maxMin", showTitle: true, title: `品质客诉率 × 订单结构（${Q}）`, titleFontSize: 11, titleColor: C.ink,
  }));
  const x = 8.75, w = 4.0;
  stat(s, x, 2.0, w, F.share(MI.order_share), "多件订单数 ÷ 签收订单数");
  stat(s, x, 3.2, w, F.share(MI.qc_share), "多件订单中的品质客诉订单数 ÷ 全部品质客诉订单数");
  stat(s, x, 4.4, w, F.times(MI.multi_qc / MI.single_qc), `多件订单品质客诉率 ${F.qc(MI.multi_qc)} ÷ 单件订单 ${F.qc(MI.single_qc)}`);
  text(s, `多件订单中命中少件漏发标签的品质客诉订单，${F.share(MI.review_after_delivered)} 的评价日期不早于签收日期`, { x, y: 5.65, w, h: 0.6, fontSize: 11, color: C.ink, bold: true });
  s.addNotes(`第一处是多件订单。多件订单占签收订单 ${F.share(MI.order_share)}，却贡献了 ${F.share(MI.qc_share)} 的品质客诉订单；多件订单的品质客诉率 ${F.qc(MI.multi_qc)}，是单件订单 ${F.qc(MI.single_qc)} 的 ${F.times(MI.multi_qc / MI.single_qc)}，增加的部分主要是少件漏发。这些少件漏发客诉订单里，${F.share(MI.review_after_delivered)} 的评价日期不早于签收日期，说明不是"还没收齐就评价"，问题指向出库环节。`);
}

// ============================================================ 13 问题② 高风险商家
{
  const sh = D.seller_tier_share, tier = D.seller_tier, CI = A.seller_ci;
  const s = contentSlide({ mark: 3, label: "模块③ 专题分析 · 问题②", title: `${tier["高风险"].sellers} 家高风险商家，贡献 ${F.share(sh["高风险"].qc)} 的商家品质客诉订单`,
    term: ["高风险商家", "参评商家中，平滑品质客诉率 ≥ 商家基准品质客诉率 × 2，且商家品质客诉订单不少于 3 单；平滑品质客诉率 =（商家品质客诉订单数 + 50 × 商家基准品质客诉率）÷（商家签收订单数 + 50）"],
    action: "举措 B：高风险商家和需关注商家整改；评估整改效果时设对照组" });
  const cats = ["商家数", "商家签收订单数", "商家品质客诉订单数"], kk = ["sellers", "delivered", "qc"];
  s.addChart(pres.charts.BAR, ["正常", "需关注", "高风险"].map(t => ({ name: t + "商家", labels: cats, values: kk.map(k => sh[t][k]) })), Object.assign({}, axis, {
    x: MX, y: 2.0, w: 7.6, h: 3.7, barDir: "bar", barGrouping: "percentStacked", barGapWidthPct: 55,
    chartColors: [C.gray, C.amber, C.pink], valAxisLabelFormatCode: "0%", showValue: true, dataLabelFormatCode: "0.0%",
    dataLabelPosition: "ctr", dataLabelColor: C.ink, dataLabelFontSize: 9, showLegend: true, legendPos: "t", legendFontSize: 10,
    catAxisOrientation: "maxMin", showTitle: true, title: `${D.seller_eligible} 家参评商家的构成（商家评估窗口：下单月 2018-03 至 2018-08）`, titleFontSize: 11, titleColor: C.ink,
  }));
  text(s, `参评商家：商家评估窗口内商家签收订单不少于 30 单的商家；一个订单含多个商家时，每个商家各计 1 单`, { x: MX, y: 5.75, w: 7.6, h: 0.5, fontSize: 10.5, color: C.muted });
  const x = 8.75, w = 4.0;
  stat(s, x, 2.0, w, F.qc(tier["高风险"].qc_rate), `高风险商家的品质客诉率（正常商家为 ${F.qc(tier["正常"].qc_rate)}）`);
  stat(s, x, 3.2, w, `${CI.high_risk_sig} / ${CI.high_risk_n} 家`, "95% 置信区间（Wilson）下限高于商家基准品质客诉率的高风险商家");
  stat(s, x, 4.4, w, F.times(BT["高风险"]["平均倍数"]), "回测：检验期品质客诉率 ÷ 检验期商家基准品质客诉率（3 组窗口按商家数加权）");
  s.addNotes(`第二处是高风险商家。判定用平滑品质客诉率：给每个商家先加 50 单"商家基准品质客诉率水平"的虚拟订单，避免 10 单里 1 单就被判为高风险。圈出的 ${tier["高风险"].sellers} 家只占参评商家的 ${F.share(sh["高风险"].sellers)}、商家签收订单的 ${F.share(sh["高风险"].delivered)}，却贡献了 ${F.share(sh["高风险"].qc)} 的商家品质客诉订单。两个检验：${CI.high_risk_sig} 家的 Wilson 置信区间下限都高于商家基准品质客诉率；回测中，这些商家下一个 6 个月的品质客诉率仍是商家基准品质客诉率的 ${F.times(BT["高风险"]["平均倍数"])}。`);
}

// ============================================================ 14 问题③ 假货与品类
{
  const info = D.info, top = D.category_top.slice(0, 10).reverse();
  const withInfo = ["1 1张图", "2 2-3张", "3 4张+"].reduce((a, k) => ({ n: a.n + info[k].n, f: a.f + info[k].fake * info[k].n }), { n: 0, f: 0 });
  const s = contentSlide({ mark: 3, label: "模块③ 专题分析 · 问题③", title: "假货集中在电脑配件和钟表礼品；大件家具少件漏发和质量缺陷多",
    term: ["假货客诉率", "命中假货标签的品质客诉订单数 ÷ 签收订单数，以\"单/万单\"表示（每 1 万个签收订单中的个数）"],
    action: "举措 C：一级类目 3C数码、钟表与潮流好物的正品与商品描述专项；商品信息缺一项不允许上架" });
  s.addChart(pres.charts.BAR, [{ name: "品质客诉率", labels: top.map(c => c.category_cn), values: top.map(c => c.qc_rate) }], Object.assign({}, axis, {
    x: MX, y: 2.0, w: 6.6, h: 4.3, barDir: "bar", barGapWidthPct: 45, chartColors: [C.pink], valAxisLabelFormatCode: "0%",
    showValue: true, dataLabelFormatCode: "0.00%", dataLabelPosition: "outEnd", dataLabelFontSize: 10, dataLabelColor: C.ink,
    showLegend: false, valAxisMinVal: 0, valAxisMaxVal: 0.12, valAxisMajorUnit: 0.02,
    showTitle: true, title: `品质客诉率最高的 10 个主品类（${Q}，签收订单 ≥ 300；全部签收订单为 ${F.qc(D.overview.qc_rate)}）`, titleFontSize: 10.5, titleColor: C.ink,
  }));
  const c0 = D.category_top[0];
  const cards = [
    ["假货", `假货客诉率：电脑配件 ${F.fake(fakeCat("电脑配件"))}，钟表礼品 ${F.fake(fakeCat("钟表礼品"))}；全部签收订单 ${F.fake(fakeAll)}（${Q}，按主品类）`],
    [`${c0.category_cn} ${F.qc(c0.qc_rate)}`, `少件漏发客诉率 ${F.qc(c0.missing_rate)}、质量缺陷客诉率 ${F.qc(c0.defect_rate)}；单件订单中重量 ≥ 15kg 的商品，品质客诉率 ${F.qc(D.heavy["4 ≥15kg"].qc)}`],
    ["商品信息缺失", `单件订单中，主商品缺少品类、图片、描述信息的，假货客诉率 ${F.fake(info["0 信息缺失"].fake)}；有 1 张及以上图片的 ${F.fake(withInfo.f / withInfo.n)}`],
  ];
  cards.forEach(([h, b], i) => {
    const y = 2.0 + i * 1.45, x = 7.55, w = W - MX - x;
    card(s, x, y, w, 1.33, i === 0 ? C.pinkTint : C.grayLight);
    text(s, h, { x: x + 0.25, y: y + 0.12, w: w - 0.5, h: 0.34, fontSize: 13.5, bold: true, color: i === 0 ? C.pink : C.ink });
    text(s, b, { x: x + 0.25, y: y + 0.5, w: w - 0.5, h: 0.8, fontSize: 11, color: C.ink });
  });
  s.addNotes(`第三处是假货。按主品类看，电脑配件的假货客诉率 ${F.fake(fakeCat("电脑配件"))}，钟表礼品 ${F.fake(fakeCat("钟表礼品"))}，全部签收订单只有 ${F.fake(fakeAll)}。另外两个发现：${c0.category_cn}品质客诉率 ${F.qc(c0.qc_rate)}，主要是少件漏发和质量缺陷，大件商品普遍如此；商品信息缺失的商品，假货客诉率明显更高，可以直接变成上架准入的要求。`);
}

// ============================================================ 15 品类结构重加权
{
  const s = contentSlide({ mark: 3, label: "模块③ 专题分析 · 品类结构", title: `穿戴类占比调为 75% 时，假货客诉率从 ${F.fake(V.reweight_2018.olist_mix.fake10k / 1e4)} 升到 ${F.fake(V.reweight_2018.target_mix.fake10k / 1e4)}`,
    term: ["品类结构重加权", `把穿戴类在签收订单中的占比从 ${F.share(V.olist_wear_share)} 调为 75%，用两类各自 2018 年 1-8 月的指标重算整体指标；75% 取自唯品会 2024 年财报报道的穿戴类 GMV 占比`],
    action: "穿戴类入仓质检把成分、标签与商品描述是否一致列为必检项" });
  const lab = ["穿戴类", "非穿戴类"];
  const bar = (title, v17, v18, x, fmt, max) => s.addChart(pres.charts.BAR, [
    { name: "2017 年", labels: lab, values: v17 }, { name: "2018 年 1-8 月", labels: lab, values: v18 },
  ], Object.assign({}, axis, {
    x, y: 2.0, w: 3.6, h: 3.7, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60, chartColors: [C.gray, C.pink],
    valAxisLabelFormatCode: fmt, dataLabelFormatCode: fmt, showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 9,
    dataLabelColor: C.ink, showLegend: true, legendPos: "b", legendFontSize: 9, showTitle: true, title, titleFontSize: 11,
    titleColor: C.ink, valAxisMinVal: 0, valAxisMaxVal: max,
  }));
  bar("品质客诉率", [V.wear["2017"].qc, V.nonwear["2017"].qc], [V.wear["2018"].qc, V.nonwear["2018"].qc], MX, "0.00%", 0.07);
  bar("假货客诉率（单/万单）", [V.wear["2017"].fake10k, V.nonwear["2017"].fake10k], [V.wear["2018"].fake10k, V.nonwear["2018"].fake10k], MX + 3.75, "0.0", 70);
  text(s, "穿戴类：主品类属于一级类目\"服饰鞋包\"，或主品类为\"钟表礼品\"\"童装\"的签收订单", { x: MX, y: 5.8, w: 7.4, h: 0.45, fontSize: 10.5, color: C.muted });
  const x = 8.2, w = W - MX - x;
  stat(s, x, 2.0, w, `${F.qc(V.wear["2017"].qc)} → ${F.qc(V.wear["2018"].qc)}`, `穿戴类品质客诉率，2017 年 → 2018 年 1-8 月（z = ${F.z(V.wear_z)}，${F.p(V.wear_p)}）`, C.pink, 26);
  card(s, x, 3.35, w, 2.9, C.grayLight);
  const down = D.samr.find(r => r.product === "羽绒服装");
  text(s, "外部参考：国家监督抽查", { x: x + 0.2, y: 3.47, w: w - 0.4, h: 0.3, fontSize: 12, bold: true, color: C.pink });
  text(s, `2023 年在 15 家电商平台抽查羽绒服 ${down.batches} 批次，${down.unqualified_batches} 批次不合格（不合格率 ${F.share(down.unqualified_rate)}），其中 19 批次是纤维含量与标称不符，属于货不对板。\n来源：市场监管总局抽查通报（经新闻转载），见 data/external/`,
    { x: x + 0.2, y: 3.82, w: w - 0.4, h: 2.35, fontSize: 10.5, color: C.ink });
  s.addNotes(`Olist 的穿戴类只占签收订单的 ${F.share(V.olist_wear_share)}，所以单独看穿戴类：品质客诉率从 ${F.qc(V.wear["2017"].qc)} 升到 ${F.qc(V.wear["2018"].qc)}，z 检验显著；假货客诉率从 ${V.wear["2017"].fake10k.toFixed(1)} 升到 ${V.wear["2018"].fake10k.toFixed(1)} 单/万单。把穿戴类占比调为 75%（取自唯品会 2024 年财报报道的穿戴类 GMV 占比，用 GMV 占比近似订单占比）重新加权，2018 年 1-8 月的假货客诉率会从 ${F.fake(V.reweight_2018.olist_mix.fake10k / 1e4)} 升到 ${F.fake(V.reweight_2018.target_mix.fake10k / 1e4)}。Olist 的服装样本小，这一页的结论是方向性的。`);
}

// ============================================================ 16 证伪
{
  const fz = D.falsify, t = fz.tenure, l = fz.late, r = fz.repurchase;
  const rAll = Object.values(r).reduce((a, x) => ({ n: a.n + x.customers, k: a.k + x.customers * x.repurchase_rate }), { n: 0, k: 0 });
  const s = contentSlide({ mark: 3, label: "模块③ 专题分析 · 证伪", title: "三个直觉上成立的假设：两个不成立，一个证据不足",
    term: ["证伪", "用数据检验一个直觉上成立的假设；数据不支持时，不据此投入治理资源"],
    action: "准入审核不是主要短板；物流时效与品质问题分开治理；复购问题等接入会员数据再回答" });
  const items = [
    ["新入驻商家品质更差？", "不成立", `入驻不足 3 个月的商家 ${F.qc(t["1 入驻<3个月"])}，入驻 12 个月以上 ${F.qc(t["4 12个月以上"])}`, "品质客诉率按商家签收订单计算（下单月 2017-07 至 2018-08）；入驻时长 = 下单时间 − 商家第一个订单的时间"],
    ["送晚了导致更多损坏？", "不成立", `延迟签收订单 ${F.qc(l["1"].qc)}，准时签收订单 ${F.qc(l["0"].qc)}；包装破损客诉率 ${F.qc(l["1"].package)} vs ${F.qc(l["0"].package)}`, "延迟签收订单：签收日期晚于承诺送达日期的签收订单（" + Q + "）"],
    ["首单遇到品质问题会流失？", "证据不足", `首单为品质客诉订单的用户复购率 ${F.share(r["1 首单品质客诉"].repurchase_rate)}，首单 5 星 ${F.share(r["4 首单5星"].repurchase_rate)}；全部用户 ${F.share(rAll.k / rAll.n)}`, "复购率：首单早于 2018-03-01、首单签收且有评价的用户中，分析窗口内下过 2 个及以上订单的用户所占比例"],
  ];
  items.forEach(([q, v, e, d], i) => {
    const x = MX + i * 4.1, y = 2.05, w = 3.9, h = 4.25;
    card(s, x, y, w, h, C.grayLight);
    text(s, q, { x: x + 0.25, y: y + 0.22, w: w - 0.5, h: 0.7, fontSize: 15, bold: true });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.25, y: y + 1.0, w: 1.3, h: 0.4, rectRadius: 0.2, fill: { color: i === 2 ? C.amber : C.muted }, line: { color: i === 2 ? C.amber : C.muted } });
    text(s, v, { x: x + 0.25, y: y + 1.0, w: 1.3, h: 0.4, fontSize: 12, bold: true, color: C.white, align: "center", valign: "middle" });
    text(s, e, { x: x + 0.25, y: y + 1.6, w: w - 0.5, h: 1.2, fontSize: 12.5, color: C.ink });
    text(s, d, { x: x + 0.25, y: y + 2.9, w: w - 0.5, h: 1.25, fontSize: 10, color: C.muted });
  });
  s.addNotes("三个直觉上合理的假设，数据都不支持。新入驻商家的品质客诉率并不更高；延迟签收订单的品质客诉率反而略低，用户主要在抱怨慢；首单体验对复购的影响在这份数据里看不出来，因为全部用户的复购率本身就很低。第三个我标的是证据不足而不是不成立，这个区别很重要：需要会员数据才能回答。");
}

// ============================================================ 17 举措与治理测算
{
  const sz = D.sizing;
  const s = contentSlide({ mark: 3, label: "模块③ 专题分析 · 举措", title: `三项举措在中性情景下，把品质客诉率从 ${F.qc(sz.baseline_rate)} 降到 ${F.qc(SC["中性"].rate)}`,
    term: ["治理测算", "以 2018 年 1-8 月的签收订单为基期，估算举措实施后的品质客诉率；一个品质客诉订单被多项举措覆盖时，按 1 − Π(1 − 各举措降幅) 叠加"],
    action: "先在部分仓库试点举措 A，用试点组相对对照组的变化评估效果" });
  const x0 = MX, y0 = 2.35, ch = 3.2, cw = 6.6, maxV = 0.06;
  const yOf = v => y0 + ch * (1 - v / maxV);
  s.addShape(pres.shapes.LINE, { x: x0, y: y0 + ch, w: cw, h: 0, line: { color: C.gray, width: 1 } });
  const bars = [["基期", 0, sz.baseline_rate, C.ink, F.qc(sz.baseline_rate)]];
  let level = sz.baseline_rate;
  sz.steps.forEach(st => { bars.push(["举措 " + st.code, level - st.delta_pp, level, C.pinkMid, F.pp(-st.delta_pp)]); level -= st.delta_pp; });
  bars.push(["中性情景", 0, level, C.pink, F.qc(level)]);
  const bw = 0.8, gap = (cw - bars.length * bw) / (bars.length + 1);
  bars.forEach(([lab, lo, hi, col, vlab], i) => {
    const x = x0 + gap + i * (bw + gap);
    s.addShape(pres.shapes.RECTANGLE, { x, y: yOf(hi), w: bw, h: yOf(lo) - yOf(hi), fill: { color: col }, line: { color: col } });
    text(s, vlab, { x: x - 0.35, y: yOf(hi) - 0.36, w: bw + 0.7, h: 0.32, fontSize: 12, bold: true, align: "center", valign: "bottom" });
    text(s, lab, { x: x - 0.35, y: y0 + ch + 0.08, w: bw + 0.7, h: 0.3, fontSize: 11.5, align: "center", color: C.muted });
  });
  text(s, `三组情景：悲观 ${F.qc(SC["悲观"].rate)} · 中性 ${F.qc(SC["中性"].rate)} · 乐观 ${F.qc(SC["乐观"].rate)}（各情景的降幅假设见附录④）`,
    { x: MX, y: 6.02, w: 6.8, h: 0.32, fontSize: 10.5, color: C.ink, bold: true });
  const acts = [
    ["A", "多件订单出库复核 + 分包裹提醒", "多件订单中命中少件漏发标签的品质客诉订单", "多件订单少件漏发客诉率"],
    ["B", "高风险商家和需关注商家整改", "主商家为高风险商家或需关注商家的品质客诉订单", "高风险商家数、高风险商家整改完成率"],
    ["C", "3C数码、钟表与潮流好物正品与商品描述专项", "主品类属于这两个一级类目、且命中假货或货不对板标签的品质客诉订单", "假货客诉率、货不对板客诉率"],
  ];
  acts.forEach(([c, n, obj, kpi], i) => {
    const x = 7.6, y = 2.0 + i * 1.45, w = W - MX - x;
    card(s, x, y, w, 1.35, C.grayLight);
    s.addShape(pres.shapes.OVAL, { x: x + 0.2, y: y + 0.18, w: 0.42, h: 0.42, fill: { color: C.pink }, line: { color: C.pink } });
    text(s, c, { x: x + 0.2, y: y + 0.18, w: 0.42, h: 0.42, fontSize: 14, bold: true, color: C.white, align: "center", valign: "middle" });
    text(s, n, { x: x + 0.78, y: y + 0.16, w: w - 1.0, h: 0.34, fontSize: 12.5, bold: true });
    text(s, `作用对象：${obj}`, { x: x + 0.78, y: y + 0.52, w: w - 1.0, h: 0.46, fontSize: 10, color: C.muted });
    text(s, `跟踪指标：${kpi}`, { x: x + 0.78, y: y + 0.98, w: w - 1.0, h: 0.3, fontSize: 10.5, color: C.pink, bold: true });
  });
  s.addNotes(`三项举措分别对应三处问题。A 是多件订单出库复核加分包裹提醒，中性情景假设降幅 50%，能降 ${F.pp(-sz.steps[0].delta_pp)}，收益最大；B 是高风险商家和需关注商家整改，假设 30%；C 是 3C数码、钟表与潮流好物的正品与商品描述专项，假设 30%。叠加时按一个品质客诉订单被任一举措避免的概率计算，避免重复。中性情景从 ${F.qc(sz.baseline_rate)} 降到 ${F.qc(SC["中性"].rate)}，悲观 ${F.qc(SC["悲观"].rate)}，乐观 ${F.qc(SC["乐观"].rate)}；降幅是可以和业务一起校准的假设参数。`);
}

// ============================================================ 18 差异化抽检
{
  const G = D.gain, c10 = SA.capture_at_10;
  const s = contentSlide({ mark: 3, label: "模块③ 专题分析 · 抽检", title: `出库只复核多件订单，就能覆盖 ${F.share(c10["出库复核：多件订单优先"])} 的出库类问题订单`,
    term: ["问题订单覆盖率", "按风险分从高到低抽检一定比例的签收订单时，抽到的问题订单数 ÷ 全部问题订单数；用 2017-09 至 2018-02 计算风险分，在下单月 2018-03 至 2018-08 上检验"],
    action: "入仓抽检按商家 × 品类风险分排序；接入商家历史质检结果后重新计算风险分" });
  const labels = G["抽检比例"].map((v, i) => (i % 2 ? "" : Math.round(v * 100) + "%"));
  const keys = [["出库复核：多件订单优先", "出库复核：多件订单优先（出库类问题订单）"], ["商家 × 品类风险分", "入仓抽检：商家 × 品类风险分"], ["商家风险分", "入仓抽检：商家风险分"], ["随机抽检", "入仓抽检：随机顺序"]];
  s.addChart(pres.charts.LINE, keys.map(([k, n]) => ({ name: n, labels, values: G[k] })), Object.assign({}, axis, {
    x: MX, y: 2.0, w: 7.4, h: 4.3, chartColors: [C.ink, C.pink, C.pinkMid, C.gray], lineSize: 2, lineDataSymbol: "none",
    valAxisLabelFormatCode: "0%", valAxisMinVal: 0, valAxisMaxVal: 1, showLegend: true, legendPos: "b", legendFontSize: 9,
    catAxisLabelFrequency: 2, showTitle: true, title: "增益曲线：横轴为抽检比例，纵轴为问题订单覆盖率", titleFontSize: 11, titleColor: C.ink,
  }));
  const x = 8.2, w = W - MX - x;
  stat(s, x, 2.0, w, F.share(c10["出库复核：多件订单优先"]), `复核全部多件订单（占签收订单 ${F.share(SA.multi_share)}）时的出库类问题订单覆盖率`, C.ink, 28);
  stat(s, x, 3.3, w, `${F.share(c10["商家 × 品类风险分"])} vs ${F.share(c10["随机抽检"])}`, "入仓抽检比例 10% 时的入仓类问题订单覆盖率：商家 × 品类风险分 vs 随机顺序", C.pink, 28);
  card(s, x, 4.6, w, 1.7, C.grayLight);
  text(s, "两类问题订单", { x: x + 0.2, y: 4.7, w: w - 0.4, h: 0.3, fontSize: 12, bold: true, color: C.pink });
  text(s, "入仓类：命中质量缺陷、货不对板或假货标签的品质客诉订单\n出库类：命中少件漏发标签的品质客诉订单", { x: x + 0.2, y: 5.03, w: w - 0.4, h: 1.2, fontSize: 10.5, color: C.ink });
  s.addNotes(`质检资源按风险分配，用样本外检验：用前 6 个月计算风险分，在后 6 个月的订单上看效果。出库类问题靠订单结构就能锁定：只复核占 ${F.share(SA.multi_share)} 的多件订单，就能覆盖 ${F.share(c10["出库复核：多件订单优先"])} 的出库类问题订单。入仓类问题更分散：抽检 10% 时，按商家乘品类的风险分抽，覆盖率 ${F.share(c10["商家 × 品类风险分"])}，随机抽是 ${F.share(c10["随机抽检"])}，是它的 ${F.times(c10["商家 × 品类风险分"] / c10["随机抽检"])}。公开数据只有商家和品类两个特征，接入商家历史质检结果后风险分会更准。`);
}

// ============================================================ 19 SQL 取数
{
  const cal = D.caliber_2018_03;
  const s = contentSlide({ mark: 4, label: "模块④ SQL 取数", title: `${D.sql_total} 道业务取数题全部实际运行，4 道与看板数字逐一核对一致`,
    term: ["对账", "同一个数用两条独立的计算路径算出并比较，完全一致才算通过；本项目用 SQL 题的结果核对数仓和看板"],
    action: "拿到取数需求先写口径和假设，再写 SQL；交付时附口径说明和自检结果" });
  table(s, [
    ["难度", "题数", "代表题目", "考点"],
    ["基础", String(D.sql_levels["基础"]), "月度订单概览、只取最后一次评价、差评率最高的品类、明细导出", "条件聚合、ROW_NUMBER 去重、一对多先去重、半开区间"],
    ["进阶", String(D.sql_levels["进阶"]), "月度品质客诉率、类目内前 3 名、连续 3 个月上升、中位数", "DENSE_RANK、LAG + 月份连续、分位数、递归 CTE 补 0"],
    ["高阶", String(D.sql_levels["高阶"]), "首单复购、帕累托、高风险商家、对账、连续 3 天", "customer_unique_id、累计窗口、贝叶斯平滑、Gaps & Islands"],
    ["开放", String(D.sql_levels["开放"]), "看板与业务方自己算的品质客诉率对不上", "按下单月归属 vs 按事件时间归属"],
  ], { x: MX, y: 2.05, w: 7.3, colW: [0.8, 0.7, 2.9, 2.9], fontSize: 11, rowH: 0.62 });
  const x = 8.2, w = W - MX - x;
  text(s, "同一需求，错误写法与正确写法的实际结果", { x, y: 2.05, w, h: 0.35, fontSize: 13, bold: true, color: C.pink });
  const cmp = [["按下单月归属 vs 分子按评价月、分母按签收月", F.qc(cal.b), F.qc(cal.a), "下单月 2018-03 的品质客诉率（Q18）"]];
  cmp.forEach(([n, a, b, d], i) => {
    const y = 2.5 + i * 1.1;
    card(s, x, y, w, 0.98, C.grayLight);
    text(s, n, { x: x + 0.2, y: y + 0.08, w: w - 0.4, h: 0.3, fontSize: 11.5, bold: true });
    text(s, `错：${a}`, { x: x + 0.2, y: y + 0.4, w: 1.9, h: 0.28, fontSize: 12, color: C.pink, bold: true });
    text(s, `对：${b}`, { x: x + 2.1, y: y + 0.4, w: w - 2.3, h: 0.28, fontSize: 12, color: C.green, bold: true });
    text(s, d, { x: x + 0.2, y: y + 0.68, w: w - 0.4, h: 0.25, fontSize: 9.5, color: C.muted });
  });
  bullets(s, [
    "两张一对多的表直接 JOIN 后求和：金额被放大，\"对不上\"的订单数虚高（Q14）",
    "用 customer_id 计算复购率：它是每个订单一个，复购率算出来是 0（Q09）",
    "多件订单 JOIN 商品行后计数：订单数被放大成商品行数（Q08）",
  ], { x, y: 3.65, w, h: 2.0, fontSize: 11 });
  text(s, "4 道对账题：月度品质客诉率、准时签收率、高风险商家名单、下单月 2018-03 的品质客诉率；5 道另有 Hive / Spark SQL 版本，与 MySQL 结果逐行核对；另附 45 分钟笔试模拟卷",
    { x: MX, y: 5.35, w: 7.3, h: 0.9, fontSize: 11, color: C.muted });
  s.addNotes(`SQL 部分把品控业务可能提的取数需求整理成 ${D.sql_total} 道题。取数最难的不是语法，而是把业务的一句话翻译成口径，所以每道题从业务方原话出发，先写口径和假设。右边是典型错误：比如下单月 2018-03 的品质客诉率，按下单月归属是 ${F.qc(cal.a)}；分子按评价月、分母按签收月是 ${F.qc(cal.b)}。所有答案都实际运行过，其中 4 道和看板数字逐一核对一致。`);
}

// ============================================================ 20 可信度
{
  const G = D.gold, lm = SPC.last_month_check, ki = D.known_issues;
  const s = contentSlide({ mark: "·", label: "项目方法 · 可信度", title: "所有数字可以复现、可以对账，已知局限已经量化",
    term: ["数据校验", `每次运行自动执行的 ${D.dq_checks} 项检查（跨层对账、主键唯一、分子不大于分母等），任一项不通过就不输出结果`],
    action: "接入内部数据后，先对齐口径，再接入入仓质检和退货数据" });
  card(s, MX, 2.05, 5.9, 4.25, C.pinkTint);
  text(s, `数据校验：${D.dq_checks} 项全部通过`, { x: MX + 0.3, y: 2.2, w: 5.4, h: 0.4, fontSize: 15, bold: true, color: C.pink });
  bullets(s, [
    "完整性：原始数据 → 订单宽表不丢单、不重复；标签覆盖全部评价",
    "唯一性：订单宽表每个订单一行，每个订单只取最后一次评价",
    "一致性：订单宽表 = 汇总表 = 看板，三处的订单数相等",
    "合理性：比率在 0 到 1 之间、分子不大于分母、品质客诉订单只来自 1-3 星",
    `已知数据问题公开并写明处理方式：时间倒挂 ${F.int(ki["时间倒挂（发货早于下单 / 签收早于发货）"])} 个订单、多条评价 ${F.int(ki["同一订单多条评价"])} 个订单、支付金额与商品金额不一致 ${F.int(ki["支付金额与商品+运费不一致(差额>1)"])} 个订单`,
  ], { x: MX + 0.3, y: 2.72, w: 5.3, h: 3.5, fontSize: 12 });
  const x = 6.85, w = W - MX - x;
  text(s, "局限", { x, y: 2.1, w, h: 0.4, fontSize: 15, bold: true });
  const lim = [
    ["规则偏保守", `标签精确率 ${F.share(G.precision)}、标签召回率 ${F.share(G.recall)}：品质客诉率的绝对值偏低；2017 年、2018 年标签召回率为 ${F.share(D.gold_by_year["2017"].recall)} 和 ${F.share(D.gold_by_year["2018"].recall)}，上升趋势不会被高估`],
    ["没有质检数据", "入仓质检合格率、问题商品拦截率已定义口径，待接入内部数据"],
    ["单一平台", "方法可以迁移；平滑参数（50 单）、预警规则需要用新数据重新校准"],
    ["最近一个月", `2018-08 品质客诉率 ${F.qc(lm.aug_rate)}：评价回收率与 7 月相当，与 7 月的差异不显著（${F.p(lm.p)}），继续观察`],
  ];
  lim.forEach(([h, b], i) => {
    const y = 2.55 + i * 0.95;
    text(s, h, { x, y, w, h: 0.3, fontSize: 13, bold: true, color: C.pink });
    text(s, b, { x, y: y + 0.32, w, h: 0.6, fontSize: 10.5, color: C.ink });
  });
  s.addNotes(`可信度分两部分。一是数据校验做成脚本，每次运行执行 ${D.dq_checks} 项检查，任何一项不通过就不输出结果；已知的数据问题不悄悄删掉，而是写明处理方式。二是局限：规则偏保守，标签召回率 ${F.share(G.recall)}，绝对值偏低，但两年的标签召回率相近，趋势结论成立；没有质检数据；最近一个月的回落还需要继续观察。`);
}

// ============================================================ 21 结尾
{
  const s = pres.addSlide();
  nextPage();
  s.background = { color: C.ink };
  text(s, "下一步", { x: MX, y: 1.0, w: 12, h: 0.7, fontSize: 34, bold: true, color: C.white, valign: "middle" });
  const todo = [
    ["对齐口径", "把品质客诉率、品质退货率与现有指标字典对齐，确认时间归属和去重规则"],
    ["接入质检与退货", "补齐入仓质检合格率、问题商品拦截率，把结果指标和过程指标连起来"],
    ["做一轮完整闭环", "从多件订单少件漏发切入，完成一轮\"发现 → 举措 → 复盘\""],
  ];
  todo.forEach(([h, b], i) => {
    const x = MX + i * 4.1, y = 2.3, w = 3.8;
    s.addShape(pres.shapes.OVAL, { x, y, w: 0.55, h: 0.55, fill: { color: C.pink }, line: { color: C.pink } });
    text(s, String(i + 1), { x, y, w: 0.55, h: 0.55, fontSize: 18, bold: true, color: C.white, align: "center", valign: "middle" });
    text(s, h, { x, y: y + 0.8, w, h: 0.45, fontSize: 20, bold: true, color: C.white });
    text(s, b, { x, y: y + 1.35, w, h: 1.2, fontSize: 13, color: C.onInk });
  });
  text(s, `项目材料：指标字典与商家品质月报模板（Excel）· 交互看板（HTML）· 专题分析报告（Word）· SQL 题库（${D.sql_total} 题 + 5 道 Hive 版 + 笔试模拟卷）· 精简版 PPT · 面试讲稿；全部代码可用 Docker 一键复现`,
    { x: MX, y: 5.5, w: 12, h: 0.5, fontSize: 12.5, color: C.onInkMuted });
  text(s, "谢谢！", { x: MX, y: 6.2, w: 6, h: 0.6, fontSize: 24, bold: true, color: C.pink });
  s.addNotes("下一步三件事：先对齐口径，再接入质检和退货数据，然后从多件订单少件漏发切入，完成一轮发现、举措、复盘。所有材料都可以一键复现。谢谢。");
}

// ============================================================ 附录
{
  const S = A.significance, CI = A.seller_ci;
  const s = contentSlide({ mark: "附", label: "附录① 统计检验", title: "品质客诉率的上升超出随机波动",
    term: ["两比例 z 检验", "检验两期品质客诉率之差是否超出随机波动；p 值 < 0.05 视为显著。95% 置信区间按 Wilson 方法计算"],
    action: "被问到\"这个差异显著吗\"时，用这一页回答" });
  table(s, [
    ["检验", "结果", "结论"],
    ["2017 年 vs 2018 年 1-8 月品质客诉率（两比例 z 检验）", `z = ${F.z(S.qc.z)}，${F.p(S.qc.p)}`, "显著上升"],
    ["95% 置信区间（Wilson）", `2017 年 ${F.qc(S.qc.ci2017[0])} – ${F.qc(S.qc.ci2017[1])}；2018 年 1-8 月 ${F.qc(S.qc.ci2018[0])} – ${F.qc(S.qc.ci2018[1])}`, "区间不重叠"],
    ["货不对板客诉率 / 假货客诉率", `z = ${F.z(S.mismatch.z)}（${F.p(S.mismatch.p)}）/ z = ${F.z(S.fake.z)}（${F.p(S.fake.p)}）`, "均显著上升"],
    ["控制图（中心线 = 2017 年品质客诉率）", `2017 年 12 个月均在控制限内；2018 年 ${SPC.beyond_ucl_months.length} 个月越限；连续 ${SPC.max_run_above} 个月高于中心线`, "持续偏移"],
    ["穿戴类 2017 年 vs 2018 年 1-8 月", `z = ${F.z(A.wear_view.wear_z)}，${F.p(A.wear_view.wear_p)}`, "显著上升"],
    ["高风险商家（Wilson 下限 > 商家基准品质客诉率）", `${CI.high_risk_sig} / ${CI.high_risk_n} 家显著；未平滑的品质客诉率 ≥ 商家基准 × 2 的 ${CI.raw2x_n} 家参评商家中 ${CI.raw2x_not_sig} 家不显著`, "平滑后的名单可信"],
  ], { x: MX, y: 2.05, w: W - 2 * MX, colW: [4.0, 5.6, 2.53], fontSize: 11, rowH: 0.56 });
  s.addNotes("两比例 z 检验用合并比例算标准误，|z| 大于 1.96 即在 5% 水平显著。控制图的中心线是 2017 年品质客诉率，控制限是中心线加减 3 倍根号下中心线乘以（1 减中心线）除以当月签收订单数，所以签收订单多的月份控制限更窄。Wilson 区间在小样本时比正态近似更准，适合商家这种样本量差别很大的场景。");
}
{
  const g = D.gold_by_type, by = D.gold_by_year;
  const s = contentSlide({ mark: "附", label: "附录② 标签评估", title: `标签精确率 ${F.share(D.gold.precision)}、标签召回率 ${F.share(D.gold.recall)}：规则偏保守，但两年一致`,
    term: ["标签召回率", "规则判为品质问题、且标注样本也判为品质问题的评价数 ÷ 标注样本判为品质问题的评价数"],
    action: "漏标主要是货不对板的口语化说法和只收到部分商品；迭代规则后另抽新样本评估" });
  const rows = [["品质问题标签", "标注样本中的条数", "标签精确率", "标签召回率"]].concat(
    Object.entries(g).map(([k, v]) => [k, String(v.support), v.precision == null ? "—" : F.share(v.precision), v.recall == null ? "—" : F.share(v.recall)]));
  rows.push(["任一品质问题标签", String(D.gold.support), F.share(D.gold.precision), F.share(D.gold.recall)]);
  table(s, rows, { x: MX, y: 2.05, w: 6.4, colW: [2.2, 1.4, 1.4, 1.4], fontSize: 12, rowH: 0.52 }, rows.length - 1);
  const x = 7.5, w = W - MX - x;
  stat(s, x, 2.05, w, `${F.share(by["2017"].recall)} vs ${F.share(by["2018"].recall)}`, "标注样本中下单年份为 2017 年 / 2018 年的评价，标签召回率", C.pink, 28);
  stat(s, x, 3.4, w, F.times(D.gold_cf), `标签精确率 ÷ 标签召回率；品质客诉率的真实值约为规则值乘以这个倍数（2018 年 1-8 月约 ${F.qc(A.scenarios.baseline * D.gold_cf)}）`, C.ink, 28, 0.8);
  text(s, "标注样本逐条明细见 outputs/qa/tag_gold_set.csv（葡语原文、中文释义、规则结果、判定）", { x, y: 5.1, w, h: 0.9, fontSize: 11, color: C.muted });
  s.addNotes(`标注样本是从全部签收订单中最后一次评价 1-3 星、有文字的评价里随机抽的 200 条，由大模型逐条读葡语原文判定，每条附中文释义方便人工抽查。标签精确率 ${F.share(D.gold.precision)}，标签召回率 ${F.share(D.gold.recall)}，规则偏保守，品质客诉率的绝对值偏低；关键是 2017 年和 2018 年的标签召回率相近，所以上升趋势不是规则造成的。`);
}
{
  const bt = A.backtest.rows;
  const wins = [...new Set(bt.map(r => r["检验窗口"]))];
  const get = (w_, g) => { const r = bt.find(x => x["检验窗口"] === w_ && x["分组"] === g); return r ? r["检验期倍数"] : 0; };
  const s = contentSlide({ mark: "附", label: "附录③ 商家分层回测", title: "三组回测窗口中，排序都是高风险商家 > 需关注商家 > 正常商家",
    term: ["回测", "用一个 6 个月窗口（训练期）给商家分层，再计算同一批商家在紧接着的 6 个月（检验期）的品质客诉率 ÷ 检验期的商家基准品质客诉率"],
    action: "评估整改效果必须设对照组，否则会把自然回落误判为整改成果" });
  s.addChart(pres.charts.BAR, ["高风险", "需关注", "正常"].map(g => ({ name: g + "商家", labels: wins.map(w_ => "检验期 " + w_.replace("~", " 至 ")), values: wins.map(w_ => get(w_, g)) })),
    Object.assign({}, axis, { x: MX, y: 2.0, w: 7.6, h: 4.3, barDir: "col", barGrouping: "clustered", barGapWidthPct: 50,
      chartColors: [C.pink, C.amber, C.gray], valAxisLabelFormatCode: "0.0", showValue: true, dataLabelFormatCode: "0.0",
      dataLabelPosition: "outEnd", dataLabelFontSize: 9, dataLabelColor: C.ink, showLegend: true, legendPos: "b", legendFontSize: 10,
      valAxisMinVal: 0, valAxisMaxVal: 3, showTitle: true, title: "检验期品质客诉率 ÷ 检验期商家基准品质客诉率（倍）", titleFontSize: 11, titleColor: C.ink }));
  const x = 8.55, w = W - MX - x, raw = BT["对照：未平滑的品质客诉率 ≥ 商家基准品质客诉率 × 2"];
  stat(s, x, 2.05, w, F.times(BT["高风险"]["平均倍数"]), `高风险商家（3 组窗口共 ${BT["高风险"]["窗口商家数"]} 家次），按商家数加权`);
  stat(s, x, 3.3, w, F.times(raw["平均倍数"]), `对照：未平滑的品质客诉率 ≥ 商家基准 × 2 的商家（${raw["窗口商家数"]} 家次）；名单更长、倍数更低`, C.ink);
  const hr = bt.filter(r => r["分组"] === "高风险" && r["检验期品质客诉率"] < r["训练期品质客诉率"]);
  text(s, `${wins.length} 组窗口中有 ${hr.length} 组，高风险商家的品质客诉率从训练期到检验期回落（${hr.map(r => F.qc(r["训练期品质客诉率"]) + " → " + F.qc(r["检验期品质客诉率"])).join("，")}）`,
    { x, y: 4.65, w, h: 1.6, fontSize: 11, color: C.ink });
  s.addNotes("回测：用一个 6 个月窗口给商家分层，再看同一批商家下一个 6 个月的品质客诉率，除以当期的商家基准品质客诉率。三组窗口里排序每次都是高风险大于需关注大于正常，说明分层有预测力。高风险商家每组只有 3 到 4 家，所以看三组合计。同时能看到回落，评估整改效果必须设对照组。");
}
{
  const s = contentSlide({ mark: "附", label: "附录④ 治理测算的情景与敏感性", title: `悲观情景也能降到 ${F.qc(SC["悲观"].rate)}；最敏感的是举措 A 的降幅`,
    term: ["情景", "举措降幅的三组假设：悲观（A 30%、B 15%、C 15%）、中性（50%、30%、30%）、乐观（70%、45%、45%）"],
    action: "上线后先验证举措 A 的真实降幅，再更新测算" });
  table(s, [["情景", "举措 A 降幅", "举措 B 降幅", "举措 C 降幅", "治理后品质客诉率"]].concat(
    ["悲观", "中性", "乐观"].map(k => [k + "情景", `${Math.round(SC[k].params[0] * 100)}%`, `${Math.round(SC[k].params[1] * 100)}%`, `${Math.round(SC[k].params[2] * 100)}%`, F.qc(SC[k].rate)])),
  { x: MX, y: 2.05, w: W - 2 * MX, colW: [1.8, 2.5, 2.5, 2.5, 2.83], fontSize: 12, rowH: 0.5 }, 2);
  const t = A.scenarios.tornado;
  table(s, [["单因素敏感性（其余两项取中性降幅）", "取悲观降幅时", "取乐观降幅时", "影响幅度"]].concat(
    t.map(r => [r["参数"], F.qc(r["悲观时品质客诉率"]), F.qc(r["乐观时品质客诉率"]), F.pp(r["影响幅度"]).replace("+", "")])),
  { x: MX, y: 4.35, w: W - 2 * MX, colW: [5.2, 2.3, 2.3, 2.33], fontSize: 12, rowH: 0.45 });
  s.addNotes(`三组情景：悲观 ${F.qc(SC["悲观"].rate)}，中性 ${F.qc(SC["中性"].rate)}，乐观 ${F.qc(SC["乐观"].rate)}。敏感性分析每次只改一项举措的降幅、其余取中性值，举措 A 的影响最大，所以上线后最该先验证多件订单复核的真实效果：先在部分仓库试点，用试点组相对对照组的变化评估。`);
}

pres.writeFile({ fileName: path.join(ROOT, "ppt", "品控数据分析项目_面试汇报.pptx") }).then(f => console.log("写入", f));
