// 生成 6 页精简版 PPT（配合 5 分钟讲稿）：node ppt/build_deck_short.js
// 每一页对应讲稿（ppt/talk_track.js）的一部分：标题 = 结论，关键术语、动作与讲稿相同，备注 = 这一部分的讲稿全文。
// 与完整版共用设计系统（deck_kit.js）和数据（outputs/deck_data.json）。
const path = require("path");
const fs = require("fs");
const { C, W, MX, F, axis, monthLabels, createDeck } = require("./deck_kit");
const { talkTrack, spoken } = require("./talk_track");

const ROOT = path.resolve(__dirname, "..");
const D = JSON.parse(fs.readFileSync(path.join(ROOT, "outputs", "deck_data.json"), "utf8"));
const A = D.adv;
const { sections } = talkTrack(D);
const { pres, nextPage, text, contentSlide, card, stat } = createDeck("差评率在下降，品质客诉率在上升（精简版）");

const T18 = D.type_by_year["2018M1-8"], MI = D.multi_item, SH = D.seller_tier_share, V = A.wear_view;
const SC = A.scenarios.scenarios, SA = A.sampling, DC = D.decomp_category, SPC = A.spc;
const Q = "下单月 2017-01 至 2018-08";
const PLACEHOLDER = "F2B84B";   // 待填写项用醒目的琥珀色，交付前替换
const fakeAll = D.fake_counts.fake / D.fake_counts.n;
const fakeCat = name => { const r = D.fake_top.find(x => x.main_category_cn === name); return r.fake / r.n; };
const sec = i => sections[i - 1];
const slideOf = i => contentSlide({ mark: i, label: `${i} / 6 · ${sec(i).name}`, title: sec(i).headline || sec(i).conclusion.replace(/。$/, ""),
  term: sec(i).term, action: sec(i).action });

// ============================================================ 1 开场（封面）
{
  const s = pres.addSlide();
  nextPage();
  s.background = { color: C.ink };
  text(s, "电商品控数据分析项目 · 精简版", { x: MX, y: 1.1, w: 10, h: 0.5, fontSize: 18, color: C.pink, bold: true });
  text(s, "差评率在下降，品质客诉率在上升", { x: MX, y: 1.7, w: 12.2, h: 1.1, fontSize: 44, bold: true, color: C.white, valign: "middle" });
  text(s, "指标体系 · 经营看板 · 专题分析 · SQL 取数", { x: MX, y: 2.85, w: 12, h: 0.55, fontSize: 22, color: C.onInk, valign: "middle" });
  s.addText([
    { text: "核心指标　品质客诉率", options: { bold: true, color: C.pink } },
    { text: "：" + sec(1).term[1], options: { color: C.onInk } },
  ], { x: MX, y: 3.75, w: 12, h: 0.7, fontFace: "Microsoft YaHei", fontSize: 14, isTextBox: true, margin: 0, valign: "top" });
  text(s, `${F.int(D.counts.scope_delivered)}`, { x: MX, y: 4.55, w: 3.5, h: 0.6, fontSize: 30, bold: true, color: C.white, valign: "bottom" });
  text(s, `个签收订单（${Q}）`, { x: MX, y: 5.2, w: 4.5, h: 0.35, fontSize: 12, color: C.onInkMuted });
  s.addShape(pres.shapes.LINE, { x: MX, y: 5.75, w: W - 2 * MX, h: 0, line: { color: "3A363D", width: 0.75 } });
  text(s, "【姓名】　｜　【手机】　｜　【邮箱】", { x: MX, y: 5.95, w: 8, h: 0.45, fontSize: 18, bold: true, color: PLACEHOLDER, valign: "middle" });
  text(s, "数据：Olist Brazilian E-Commerce Public Dataset（巴西电商平台公开的脱敏真实订单）", { x: MX, y: 6.55, w: 12, h: 0.35, fontSize: 12, color: C.onInkMuted, valign: "middle" });
  s.addNotes(spoken(sec(1)) + "\n\n（交付前把琥珀色的姓名、手机、邮箱换成自己的。）");
}

// ============================================================ 2 结论
{
  const s = slideOf(2);
  const labels = monthLabels(D.months), p0 = SPC.p0;
  s.addChart(pres.charts.LINE, [
    { name: "品质客诉率", labels, values: D.p_chart.p },
    { name: "上控制限", labels, values: D.p_chart.ucl },
    { name: "下控制限", labels, values: D.p_chart.lcl },
    { name: `中心线 ${F.qc(p0)}（2017 年品质客诉率）`, labels, values: labels.map(() => p0) },
  ], Object.assign({}, axis, {
    x: MX, y: 2.0, w: 7.6, h: 3.8, chartColors: [C.pink, C.gray, C.gray, C.ink], lineSize: 2, lineDataSymbol: "none",
    valAxisLabelFormatCode: "0.0%", valAxisMinVal: 0.02, valAxisMaxVal: 0.065, valAxisMajorUnit: 0.005, showLegend: true, legendPos: "b",
    legendFontSize: 9, catAxisLabelFontSize: 9, catAxisLabelRotate: 0,
  }));
  text(s, `2017-10 至 2018-08 连续 ${SPC.max_run_above} 个月高于中心线；${SPC.beyond_ucl_months.length} 个月越限（${SPC.beyond_ucl_months.join("、")}）`,
    { x: MX, y: 5.88, w: 7.6, h: 0.4, fontSize: 11.5, color: C.ink, bold: true });
  const x = 8.75, w = W - MX - x;
  stat(s, x, 2.0, w, `${F.share(D.bad_rate[14])} → ${F.share(D.bad_rate[19])}`,
    `差评率，下单月 2018-03 → 2018-08；同期准时签收率 ${F.share(D.on_time_rate[14])} → ${F.share(D.on_time_rate[19])}`, C.muted, 28);
  stat(s, x, 3.4, w, `${F.qc(DC.rate_A)} → ${F.qc(DC.rate_B)}`,
    `品质客诉率，2017 年 → 2018 年 1-8 月（z = ${F.z(A.significance.qc.z)}，${F.p(A.significance.qc.p)}）`, C.pink, 28);
  stat(s, x, 4.8, w, `${F.share(D.mix.quality[0])} → ${F.share(D.mix.quality[6])}`, "差评品质原因占比，下单季度 2017Q1 → 2018Q3", C.ink, 28);
  s.addNotes(spoken(sec(2)));
}

// ============================================================ 3 指标
{
  const s = slideOf(3);
  const lx = MX, lw = 5.75;
  card(s, lx, 2.0, lw, 0.95, C.pink);
  text(s, "核心指标　品质客诉率", { x: lx + 0.25, y: 2.07, w: lw - 0.5, h: 0.4, fontSize: 16, bold: true, color: C.white });
  text(s, `品质客诉订单数 ÷ 签收订单数；2018 年 1-8 月 ${F.qc(A.scenarios.baseline)}`, { x: lx + 0.25, y: 2.48, w: lw - 0.5, h: 0.4, fontSize: 11.5, color: C.white });
  text(s, "结果指标：按 5 个品质问题标签拆开（2018 年 1-8 月）", { x: lx, y: 3.08, w: lw, h: 0.3, fontSize: 11.5, bold: true, color: C.pink });
  const l1 = [["少件漏发客诉率", F.qc(T18.missing)], ["货不对板客诉率", F.qc(T18.mismatch)], ["质量缺陷客诉率", F.qc(T18.defect)], ["包装破损客诉率", F.qc(T18.package)], ["假货客诉率", F.fake(T18.fake)]];
  const tw = (lw - 4 * 0.1) / 5;
  l1.forEach(([k, v], i) => {
    const x = lx + i * (tw + 0.1);
    card(s, x, 3.42, tw, 0.9, C.pinkTint);
    text(s, k, { x: x + 0.08, y: 3.47, w: tw - 0.12, h: 0.3, fontSize: 9.5, color: C.muted });
    text(s, v, { x: x + 0.08, y: 3.8, w: tw - 0.12, h: 0.4, fontSize: k === "假货客诉率" ? 10.5 : 14, bold: true, valign: "middle" });
  });
  text(s, "体验指标：差评率等，只观察，不用于考核品控", { x: lx, y: 4.45, w: lw, h: 0.3, fontSize: 11.5, bold: true, color: C.pink });
  text(s, "过程指标：商品准入、商家管理、仓配履约三个环节（另有需要内部数据的待接入指标）", { x: lx, y: 4.8, w: lw, h: 0.55, fontSize: 11.5, color: C.ink });
  text(s, "三条口径规则：按下单月归属；只取最后一次评价；汇总表只存订单数，最后再算比率", { x: lx, y: 5.45, w: lw, h: 0.55, fontSize: 11.5, color: C.ink });
  const rx = 6.75, rw = W - MX - rx, rh = rw * 1640 / 2720;
  s.addImage({ path: path.join(ROOT, "docs", "images", "dashboard_overview_top.png"), x: rx, y: 2.0, w: rw, h: rh });
  s.addShape(pres.shapes.RECTANGLE, { x: rx, y: 2.0, w: rw, h: rh, fill: { type: "none" }, line: { color: C.line, width: 0.75 } });
  text(s, "看板第一屏：核心指标、体验指标、控制图和预警清单；第二屏：结果指标、一级类目和订单结构",
    { x: rx, y: 2.0 + rh + 0.12, w: rw, h: 0.55, fontSize: 11, color: C.muted });
  s.addNotes(spoken(sec(3)));
}

// ============================================================ 4 问题
{
  const s = slideOf(4);
  text(s, `因素分解（2017 年 → 2018 年 1-8 月）：品质客诉率 ${F.pp(DC.rate_B - DC.rate_A)}，其中组内效应 ${F.pp(DC.within_effect)}，结构效应 ${F.pp(DC.mix_effect)}`,
    { x: MX, y: 2.0, w: W - 2 * MX, h: 0.35, fontSize: 12.5, bold: true, color: C.ink });
  const cols = [
    [`${F.share(MI.order_share)} → ${F.share(MI.qc_share)}`, "多件订单",
      `多件订单占签收订单 ${F.share(MI.order_share)}，贡献 ${F.share(MI.qc_share)} 的品质客诉订单；品质客诉率 ${F.qc(MI.multi_qc)}，是单件订单 ${F.qc(MI.single_qc)} 的 ${F.times(MI.multi_qc / MI.single_qc)}（${Q}）`,
      "对应环节：仓配出库"],
    [`${D.seller_tier["高风险"].sellers} 家 → ${F.share(SH["高风险"].qc)}`, "高风险商家",
      `占参评商家 ${F.share(SH["高风险"].sellers)}，商家签收订单占 ${F.share(SH["高风险"].delivered)}，商家品质客诉订单占 ${F.share(SH["高风险"].qc)}；回测中下一个 6 个月仍是商家基准品质客诉率的 ${F.times(A.backtest.pooled["高风险"]["平均倍数"])}`,
      "对应环节：商家管理"],
    [F.fake(fakeCat("电脑配件")), "假货",
      `假货客诉率：电脑配件 ${F.fake(fakeCat("电脑配件"))}、钟表礼品 ${F.fake(fakeCat("钟表礼品"))}，全部签收订单 ${F.fake(fakeAll)}（${Q}）；穿戴类占比从 ${F.share(V.olist_wear_share)} 调为 75% 时，2018 年 1-8 月从 ${F.fake(V.reweight_2018.olist_mix.fake10k / 1e4)} 升到 ${F.fake(V.reweight_2018.target_mix.fake10k / 1e4)}`,
      "对应环节：商品准入"],
  ];
  const cw = (W - 2 * MX - 2 * 0.3) / 3;
  cols.forEach(([big, head, body, act], i) => {
    const x = MX + i * (cw + 0.3), y = 2.5, h = 3.8;
    card(s, x, y, cw, h, C.grayLight);
    text(s, head, { x: x + 0.3, y: y + 0.2, w: cw - 0.6, h: 0.4, fontSize: 15, bold: true });
    text(s, big, { x: x + 0.3, y: y + 0.62, w: cw - 0.6, h: 0.7, fontSize: 24, bold: true, color: C.pink, valign: "bottom" });
    text(s, body, { x: x + 0.3, y: y + 1.45, w: cw - 0.6, h: 1.75, fontSize: 11.5, color: C.ink });
    s.addShape(pres.shapes.LINE, { x: x + 0.3, y: y + 3.22, w: cw - 0.6, h: 0, line: { color: C.line, width: 0.75 } });
    text(s, act, { x: x + 0.3, y: y + 3.3, w: cw - 0.6, h: 0.4, fontSize: 12.5, bold: true, color: C.pink, valign: "middle" });
  });
  text(s, "穿戴类占比 75% 取自唯品会 2024 年财报报道的穿戴类 GMV 占比，用 GMV 占比近似订单占比", { x: MX, y: 6.33, w: 9, h: 0.14, fontSize: 8.5, color: C.muted });
  s.addNotes(spoken(sec(4)));
}

// ============================================================ 5 举措
{
  const s = slideOf(5);
  text(s, "治理后的品质客诉率：基期与三组情景", { x: MX, y: 2.0, w: 6.5, h: 0.32, fontSize: 12.5, bold: true });
  const bars = [["基期", A.scenarios.baseline, C.ink], ["悲观", SC["悲观"].rate, C.pinkMid], ["中性", SC["中性"].rate, C.pink], ["乐观", SC["乐观"].rate, C.pinkDark]];
  const x0 = MX + 0.2, y0 = 2.5, ch = 3.1, vmax = 0.06, bw = 1.05, gap = 0.55;
  const yOf = v => y0 + ch * (1 - v / vmax);
  const xEnd = x0 + 4 * bw + 3 * gap;
  bars.forEach(([lab, v, col], i) => {
    const x = x0 + i * (bw + gap);
    s.addShape(pres.shapes.RECTANGLE, { x, y: yOf(v), w: bw, h: y0 + ch - yOf(v), fill: { color: col }, line: { color: col } });
    text(s, F.qc(v), { x, y: yOf(v) + 0.1, w: bw, h: 0.35, fontSize: 14, bold: true, color: C.white, align: "center", valign: "top" });
    text(s, lab === "基期" ? "基期" : lab + "情景", { x: x - 0.25, y: y0 + ch + 0.08, w: bw + 0.5, h: 0.3, fontSize: 11.5, align: "center", color: C.muted });
  });
  s.addShape(pres.shapes.LINE, { x: x0 - 0.1, y: y0 + ch, w: xEnd - x0 + 0.2, h: 0, line: { color: C.gray, width: 0.75 } });
  text(s, "基期：2018 年 1-8 月；降幅假设 悲观 A 30%、B 15%、C 15%，中性 50%、30%、30%，乐观 70%、45%、45%",
    { x: MX, y: 6.0, w: 6.7, h: 0.35, fontSize: 10, color: C.muted });
  const rx = 7.55, rw = W - MX - rx;
  const acts = [["A", "多件订单出库复核 + 分包裹提醒"], ["B", "高风险商家和需关注商家整改"], ["C", "3C数码、钟表与潮流好物正品与商品描述专项"]];
  acts.forEach(([k, t], i) => {
    const y = 2.0 + i * 0.58;
    s.addShape(pres.shapes.OVAL, { x: rx, y: y + 0.03, w: 0.4, h: 0.4, fill: { color: C.pink }, line: { color: C.pink } });
    text(s, k, { x: rx, y: y + 0.03, w: 0.4, h: 0.4, fontSize: 13, bold: true, color: C.white, align: "center", valign: "middle" });
    text(s, t, { x: rx + 0.55, y: y + 0.05, w: rw - 0.55, h: 0.36, fontSize: 12.5, bold: true, valign: "middle" });
  });
  card(s, rx, 3.85, rw, 2.45, C.pinkTint);
  text(s, "质检按风险分配（用 2017-09 至 2018-02 计算风险分，在下单月 2018-03 至 2018-08 上检验）", { x: rx + 0.25, y: 3.95, w: rw - 0.5, h: 0.5, fontSize: 11, bold: true, color: C.pink });
  const c10 = SA.capture_at_10;
  stat(s, rx + 0.25, 4.45, 2.3, F.share(c10["出库复核：多件订单优先"]), "出库复核只看多件订单时的出库类问题订单覆盖率", C.ink, 24, 0.8);
  stat(s, rx + 2.75, 4.45, rw - 3.0, `${F.share(c10["商家 × 品类风险分"])} vs ${F.share(c10["随机抽检"])}`, "入仓抽检 10% 时的入仓类问题订单覆盖率：风险分 vs 随机", C.pink, 24, 0.8);
  s.addNotes(spoken(sec(5)));
}

// ============================================================ 6 可信度
{
  const s = slideOf(6);
  const G = D.gold, GY = D.gold_by_year;
  const facts = [
    [`${D.dq_checks} 项`, "数据校验", "每次运行自动执行（跨层对账、主键唯一、分子不大于分母等），最近一次全部通过；任一项不通过就不输出结果"],
    [`${F.share(G.precision)} / ${F.share(G.recall)}`, "标签精确率 / 标签召回率", `标注样本 200 条（从 ${F.int(D.gold_population)} 条中随机抽取）；2017 年、2018 年标签召回率 ${F.share(GY["2017"].recall)}、${F.share(GY["2018"].recall)}，上升趋势不会被高估`],
    [`${D.sql_total} 道`, "SQL 取数题", "全部实际运行；4 道与看板数字逐一核对一致；5 道另有 Hive / Spark SQL 版本，与 MySQL 结果逐行核对"],
  ];
  const cw = (W - 2 * MX - 2 * 0.3) / 3;
  facts.forEach(([v, h, b], i) => {
    const x = MX + i * (cw + 0.3), y = 2.1;
    card(s, x, y, cw, 4.15, i === 0 ? C.pinkTint : C.grayLight);
    text(s, v, { x: x + 0.3, y: y + 0.3, w: cw - 0.6, h: 0.7, fontSize: 26, bold: true, color: C.pink, valign: "bottom" });
    text(s, h, { x: x + 0.3, y: y + 1.1, w: cw - 0.6, h: 0.4, fontSize: 15, bold: true });
    text(s, b, { x: x + 0.3, y: y + 1.6, w: cw - 0.6, h: 2.3, fontSize: 12, color: C.ink });
  });
  s.addNotes(spoken(sec(6)) + "谢谢。");
}

pres.writeFile({ fileName: path.join(ROOT, "ppt", "品控数据分析项目_面试汇报_精简版.pptx") }).then(f => console.log("写入", f));
