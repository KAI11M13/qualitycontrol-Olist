// 专题分析报告正文（只写一份，同时渲染成 Word 和 Markdown）
// 所有数字来自 outputs/deck_data.json
const path = require("path");
const fs = require("fs");

const ROOT = path.resolve(__dirname, "..");
const D = JSON.parse(fs.readFileSync(path.join(ROOT, "outputs", "deck_data.json"), "utf8"));
const FIG = f => path.join(ROOT, "outputs", "figures", f);

const pct = (v, d = 1) => (v * 100).toFixed(d) + "%";
const pp = (v, d = 2) => (v >= 0 ? "+" : "−") + Math.abs(v * 100).toFixed(d) + "pp";
const num = v => Math.round(v).toLocaleString("en-US");

const P = D.period, T17 = D.type_by_year["2017"], T18 = D.type_by_year["2018M1-8"];
const DC = D.decomp_category, MI = D.multi_item, ST = D.seller_tier, SS = D.seller_tier_share, SZ = D.sizing;
const OT = D.order_type, FZ = D.falsify, CT = D.category_top;
const chg = k => (T18[k] / T17[k] - 1) * 100;
const A = D.adv, SPC = A.spc, SIG = A.significance, VV = A.vip_view, SA = A.sampling, BT = A.backtest, SC = A.scenarios;
const G = D.gold, GY = D.gold_by_year;
const ci = (c, d = 2) => `${pct(c[0], d)}–${pct(c[1], d)}`;
const ym = m => `${m.slice(0, 4)} 年 ${Number(m.slice(5))} 月`;

const meta = {
  title: "差评在降，品质客诉在升",
  subtitle: "电商品控专题分析报告：品质问题的结构、瓶颈与治理测算",
  info: [
    ["数据", "Olist Brazilian E-Commerce Public Dataset（巴西电商平台脱敏真实订单）"],
    ["分析窗口", "2017-01 至 2018-08（按下单月），签收订单 " + num(D.counts.scope_delivered) + " 单"],
    ["口径", "品控指标字典 v1.0（docs/品控指标字典.xlsx）"],
    ["复现", "python scripts/run_pipeline.py（MySQL 8.0）"],
  ],
};

const blocks = [
  { t: "h1", text: "摘要" },
  { t: "callout", items: [
    `差评率由物流主导，不能用来评价品控：2018 年 3 月物流危机时准时签收率跌到 ${pct(D.on_time_rate[14])}，差评率冲到 ${pct(D.bad_rate[14])}；物流恢复后 8 月差评率回落到 ${pct(D.bad_rate[19])}。`,
    `品质客诉率在上升：2017 年 ${pct(DC.rate_A, 2)} → 2018 年 1-8 月 ${pct(DC.rate_B, 2)}（${pp(DC.rate_B - DC.rate_A)}，z = ${SIG.qc.z.toFixed(2)}，p < 0.0001），p 控制图上自 ${ym(SPC.run_start_month)}起连续 ${SPC.max_run_above} 个月高于 2017 年基线；1-2 星差评中品质类占比从 2017Q1 的 ${pct(D.mix.quality[0], 0)} 升到 2018Q3 的 ${pct(D.mix.quality[6], 0)}。`,
    `上升不是结构变化，而是同类订单变差：因素分解中结构效应 ${pp(DC.mix_effect)}、组内效应 ${pp(DC.within_effect)}；增长最快的是货不对板（+${chg("mismatch").toFixed(0)}%）和假货（+${chg("fake").toFixed(0)}%）。`,
    `三个瓶颈：① 多件订单占签收单 ${pct(MI.order_share, 0)}，贡献 ${pct(MI.qc_share, 0)} 的品质客诉和 ${pct(MI.missing_share, 0)} 的少件客诉；② ${ST["高风险"].sellers} 家高风险商家占 ${pct(SS["高风险"].delivered)} 订单、贡献 ${pct(SS["高风险"].qc)} 品质客诉；③ 办公家具品质客诉率 ${pct(CT[0].qc_rate)}，3C/钟表假货集中，信息缺失商品假货投诉率约为信息完整商品的 9 倍。`,
    `唯品会视角：穿戴类品质客诉率涨得更快（${pct(VV.wear["2017"].qc)} → ${pct(VV.wear["2018"].qc)}）；按唯品会穿戴类约 75% 的品类结构重新加权，假货投诉从每万单 ${VV.reweight_2018.olist_mix.fake10k.toFixed(0)} 升到 ${VV.reweight_2018.vip_mix.fake10k.toFixed(0)}，正品管控的优先级应高于 Olist 场景。`,
    `三项举措（多件订单出库复核、高风险商家整改、3C/钟表正品专项）中性情景下可把品质客诉率从 ${pct(SZ.baseline_rate, 2)} 降到 ${pct(SZ.target_rate, 2)}，达到 4.0% 的目标线；三档情景区间 ${pct(SC.scenarios["乐观"].rate, 2)}–${pct(SC.scenarios["悲观"].rate, 2)}。`,
  ] },

  { t: "h1", text: "1. 背景与问题" },
  { t: "p", text: "2018 年平台差评率从 3 月的高点快速回落，直觉上会认为用户体验在改善。但差评是多种原因的混合：没收到货、送得慢、服务差、商品本身有问题。对品控团队来说，关心的是其中\"商品本身有问题\"的那一部分是否也在改善。" },
  { t: "p", text: "本报告要回答四个问题：" },
  { t: "bullets", items: [
    "差评率下降，是否代表商品品质在改善？",
    "如果品质问题在上升，是卖了更多高风险品类（结构变化），还是同类商品本身变差（组内恶化）？",
    "品质问题集中在哪里：哪类问题、哪类订单、哪些商家、哪些品类？",
    "有哪些可落地的举措，能把品质客诉率降到多少？",
  ] },

  { t: "h1", text: "2. 数据与口径" },
  { t: "h2", text: "2.1 数据来源与业务映射" },
  { t: "p", text: `使用 Olist 公开的巴西电商平台真实订单数据，共 ${num(D.counts.orders)} 个订单、${num(D.counts.items)} 个商品行、${num(D.counts.reviews_raw)} 条评价（去重后 ${num(D.counts.reviews)} 条）、${num(D.counts.sellers)} 家商家、${num(D.counts.products)} 个商品、${D.counts.categories} 个品类。各表行数与官方数据集一致。2016 年（仅 300 余单）和 2018 年 9 月以后（仅 20 单）数据不完整，分析窗口取 2017-01 至 2018-08。` },
  { t: "table", head: ["唯品会品控环节", "本项目数据", "说明"], widths: [2600, 3400, 3000], rows: [
    ["供应商 / 品牌方", "Olist 商家（seller）", "直接映射"],
    ["客诉 / 售后工单", "评价星级 + 评价原文（葡语）", "用文本打标还原问题类型"],
    ["供应商发货时效", "shipping_limit_date（发货 SLA）", "直接映射"],
    ["商品详情页质量", "品类、图片数、描述字数", "映射为商品信息完整率"],
    ["入仓质检 / 退货原因", "无", "已定义口径，待接入"],
  ] },
  { t: "h2", text: "2.2 核心口径" },
  { t: "bullets", items: [
    "品质客诉单：签收订单中，用户最后一次评价为 1-3 星，且评价文本命中假货 / 质量缺陷 / 货不对板 / 少件漏发 / 包装破损任一类问题。",
    "品质客诉率 = 品质客诉单 ÷ 签收单；分子分母都按下单月归属（cohort），保证是同一批订单。",
    "签收 = 订单状态为 delivered 且签收时间不为空；同一订单多条评价时保留最后一次提交的评价。",
    "问题类型允许多选（一条评价可同时命中多类）；需要互斥结构时，按\"假货 > 质量缺陷 > 货不对板 > 少件漏发 > 包装 > 未收货 > 延迟 > 服务\"取主标签。",
  ] },
  { t: "h2", text: "2.3 评价文本打标与准确性评估" },
  { t: "p", text: `公开数据没有客诉工单，本项目用葡语关键词规则把评价文本打成 8 类问题标签。规则先做小写与去重音归一化，并剔除\"sem defeito（没有瑕疵）\"这类否定式表述。打标质量做了两轮评估。两轮的判定都由大模型（Claude）逐条阅读葡语原文完成，每条附中文释义，样本文件在 outputs/qa/，可以逐条人工抽查。` },
  { t: "p", text: `第一轮（规则迭代期 v0.4，只看准确率）：按规则打出的标签分层抽样 ${D.tag_samples} 条（7 类 × 20 条），综合准确率 ${pct(D.tag_accuracy)}。误判样本用于修正规则（v0.4 → v1.0）：` },
  { t: "table", head: ["问题类型", "v0.4 准确率", "主要误判（已修正）"], widths: [2600, 1600, 4800], rows: [
    ["假货 / 非正品", pct(D.tag_accuracy_by_type.fake, 0), "—"],
    ["包装破损", pct(D.tag_accuracy_by_type.package, 0), "—"],
    ["少件 / 漏发", pct(D.tag_accuracy_by_type.missing, 0), "发票金额问题、裸发无包装被误判"],
    ["物流延迟", pct(D.tag_accuracy_by_type.delay, 0), "\"保质期\"中的\"prazo\"被误判为时效"],
    ["货不对板", pct(D.tag_accuracy_by_type.mismatch, 0), "运费、部分到货被误判"],
    ["质量缺陷", pct(D.tag_accuracy_by_type.defect, 0), "\"lixo（垃圾）\"等骂店铺的泛化词"],
    ["未收到货", pct(D.tag_accuracy_by_type.not_received, 0), "部分到货被归为未收货"],
  ] },
  { t: "p", text: `第二轮（v1.0 定版后，准确率 + 召回率）：第一轮只抽\"打上了标签\"的评价，算不出漏标。第二轮从 ${num(D.gold_population)} 条\"已签收、1-3 星、有文字\"的评价中随机抽 200 条盲评（判定时不看规则结果），再与规则结果对比：` },
  { t: "table", head: ["问题类型", "金标准条数", "准确率", "召回率"], widths: [3000, 2000, 2000, 2000],
    rows: Object.entries(D.gold_by_type).map(([k, v]) => [k, String(v.support), v.precision == null ? "—" : pct(v.precision, 0), v.recall == null ? "—" : pct(v.recall, 0)])
      .concat([["合计（任一品质问题）", String(G.support), pct(G.precision), pct(G.recall)]]) },
  { t: "bullets", items: [
    `规则准确率高、召回率偏低，属于偏保守：漏标主要是货不对板的多样说法（\"寄来的和买的不像\"\"颜色型号被换\"）和部分到货。`,
    `绝对值：真实品质客诉率 ≈ 规则值 × 准确率 ÷ 召回率，校正系数约 ${D.gold_cf.toFixed(2)}，2018 年 1-8 月真实值约 ${pct(SC.baseline * D.gold_cf)}。报告中的品质客诉率统一按规则口径，是保守值。`,
    `趋势：2017 年、2018 年召回率分别为 ${pct(GY["2017"].recall, 0)}、${pct(GY["2018"].recall, 0)}（样本 ${GY["2017"].support} / ${GY["2018"].support} 条，差异不显著）。2018 年召回率不高于 2017 年，所以真实的上升幅度只会更大，两年对比和结构性结论不受漏标影响。`,
    "下一步：用这 200 条作为开发集迭代规则 v1.1，再随机抽一批新样本做测试集，避免在评估集上过拟合。",
  ] },
  { t: "h2", text: "2.4 数据质量" },
  { t: "p", text: `每次跑数自动执行 ${D.dq_checks} 项校验（跨层对账、主键唯一、分子 ≤ 分母、比率在 [0,1] 等），全部通过。已知问题如 189 单时间倒挂、547 单重复评价、249 单支付与商品金额不一致，均在 outputs/qa/dq_report.md 中披露并写明处理方式。` },

  { t: "h1", text: "3. 分析发现" },
  { t: "h2", text: "3.1 差评率跟着物流走，品质客诉率在上升" },
  { t: "img", path: FIG("fig01_trend_small_multiples.png"), w: 16, caption: "图 1　差评率、准时签收率与品质客诉率（三个量纲不同的指标分开画，不使用双轴）" },
  { t: "p", text: `差评率和准时签收率几乎是镜像：2017 年 11 月（黑五）和 2018 年 2-3 月准时率下滑时，差评率同步冲高；4 月之后物流恢复，差评率回到 11%-13%。品质客诉率的走势与之无关：2017 年上半年约 ${pct(P["2017H1"].qc_rate)}，下半年 ${pct(P["2017H2"].qc_rate)}，2018 年 1-8 月升至 ${pct(P["2018M1-8"].qc_rate)}。` },
  { t: "p", text: "注：2018 年 8 月品质客诉率回落到 4.4%，部分原因是最近下单的订单评价尚在回收（右删失），不宜解读为好转。" },
  { t: "img", path: FIG("fig08_p_chart.png"), w: 16, caption: `图 2　品质客诉率 p 控制图（阶段Ⅰ = 2017 年，中心线 p0 = ${pct(SPC.p0, 2)}，控制限 ±3σ 随月签收量变化）` },
  { t: "p", text: `上升是趋势还是随机波动？用统计过程控制（SPC）判断：以 2017 年为阶段Ⅰ建立基线（12 个月全部在控制限内），中心线 p0 = ${pct(SPC.p0, 2)}，控制限 p0 ± 3√(p0(1 − p0) / n)，n 为当月签收单。2018 年进入阶段Ⅱ后，${SPC.beyond_ucl_months.map(ym).join("、")}越出上控制限；自 ${ym(SPC.run_start_month)}起连续 ${SPC.max_run_above} 个月高于中心线，在 ${ym(SPC.run9_signal_month)}触发\"连续 9 点在中心线同侧\"判异准则。结论：过程均值发生了持续偏移，不是随机波动。` },
  { t: "table", head: ["检验", "结果", "结论"], widths: [3200, 3800, 2000], rows: [
    ["品质客诉率 2017 vs 2018 年 1-8 月（两比例 z 检验）", `z = ${SIG.qc.z.toFixed(2)}，p < 0.0001`, "显著上升"],
    ["95% 置信区间（Wilson）", `2017：${ci(SIG.qc.ci2017)}；2018：${ci(SIG.qc.ci2018)}`, "区间不重叠"],
    ["货不对板率 / 假货投诉率", `z = ${SIG.mismatch.z.toFixed(2)} / z = ${SIG.fake.z.toFixed(2)}（p = ${SIG.fake.p.toFixed(4)}）`, "均显著上升"],
  ] },

  { t: "h2", text: "3.2 差评里，品质问题占比从 22% 升到 35%" },
  { t: "img", path: FIG("fig02_bad_review_reason_mix.png"), w: 16, caption: "图 3　1-2 星差评的原因结构（按主标签，互斥口径）" },
  { t: "p", text: `2017 年各季度，品质类在差评中占 ${pct(D.mix.quality[0], 0)}-${pct(D.mix.quality[2], 0)}；2018Q2 起跳到 ${pct(D.mix.quality[5], 0)}-${pct(D.mix.quality[6], 0)}。履约类占比在物流危机的 2018Q1 最高（${pct(D.mix.fulfill[4], 0)}），之后回落。物流问题被解决后，剩下的差评里品质问题越来越突出。` },

  { t: "h2", text: "3.3 上升来自同类订单变差，而非结构变化" },
  { t: "p", text: "平台品质客诉率可以写成各一级类目的加权平均：R = Σ wᵢ·rᵢ（wᵢ 为类目签收单占比，rᵢ 为类目品质客诉率）。两期变化可分解为：" },
  { t: "bullets", items: [
    `结构效应 Σ Δwᵢ·rᵢ⁰ = ${pp(DC.mix_effect)}：高客诉类目卖得更多带来的变化`,
    `组内效应 Σ wᵢ⁰·Δrᵢ = ${pp(DC.within_effect)}：类目自身客诉率变化带来的变化`,
    `交互项 Σ Δwᵢ·Δrᵢ = ${pp(DC.interaction)}`,
  ] },
  { t: "p", text: `结论：上升几乎全部来自组内效应；按单件 / 多件订单分解结果相同（结构效应 ${pp(D.decomp_order_type.mix_effect)}）。组内贡献最大的类目依次是 3C 数码、钟表礼品、家居家纺、母婴玩具。` },
  { t: "img", path: FIG("fig03_type_yoy.png"), w: 15, caption: "图 4　各类品质问题发生率：2017 全年 vs 2018 年 1-8 月" },
  { t: "p", text: `分问题类型看，货不对板（${pct(T17.mismatch, 2)} → ${pct(T18.mismatch, 2)}，+${chg("mismatch").toFixed(0)}%）和假货（${pct(T17.fake, 2)} → ${pct(T18.fake, 2)}，+${chg("fake").toFixed(0)}%）增长最快；质量缺陷基本持平（+${chg("defect").toFixed(0)}%）。问题更多出在\"描述与实物不符\"和\"正品管控\"，而不是生产质量。` },

  { t: "h2", text: "3.4 瓶颈①：多件订单的少件 / 漏发" },
  { t: "img", path: FIG("fig04_order_structure.png"), w: 15, caption: "图 5　不同订单结构的品质客诉率（橙色为少件 / 漏发）" },
  { t: "table", head: ["订单结构", "签收单", "占比", "品质客诉率", "少件 / 漏发率", "差评率"], widths: [2000, 1400, 1100, 1500, 1500, 1500],
    rows: Object.keys(OT).sort().map(k => [k.slice(2), num(OT[k].n), pct(OT[k].order_share), pct(OT[k].qc), pct(OT[k].missing), pct(OT[k].bad_rate)]) },
  { t: "p", text: `多件订单只占签收单的 ${pct(MI.order_share)}，却贡献了 ${pct(MI.qc_share)} 的品质客诉和 ${pct(MI.missing_share)} 的少件客诉；多件订单品质客诉率 ${pct(MI.multi_qc)}，是单件订单（${pct(MI.single_qc)}）的 ${(MI.multi_qc / MI.single_qc).toFixed(1)} 倍，多商家订单最高（${pct(OT["4 多商家"].qc)}）。` },
  { t: "p", text: `进一步验证：${pct(MI.review_after_delivered)} 的多件订单少件投诉，提交时订单已显示签收。因此不是\"没收齐就急着评价\"，而是用户在签收状态下确实缺件——要么漏发，要么分包裹没有同步送达且未告知用户。两种情况都指向出库环节。` },

  { t: "h2", text: "3.5 瓶颈②：少数高风险商家" },
  { t: "img", path: FIG("fig05_seller_tier.png"), w: 15, caption: `图 6　商家风险分层（近 6 个月签收 ≥ 30 单的 ${D.seller_eligible} 家商家，覆盖 ${pct(D.seller_cover, 0)} 订单）` },
  { t: "p", text: "商家品质分 = 品质客诉率 50% + 差评率 20% + 发货超时率 15% + 延迟签收率 15%，各分项按参评商家的分位数打分。风险分层使用贝叶斯平滑后的客诉率：平滑客诉率 =（客诉单 + 50 × 平台客诉率）÷（签收单 + 50），避免\"10 单 1 客诉 = 10%\"的小样本商家被误判。不平滑时会圈出 302 家商家，平滑并加门槛后为 10 家。" },
  { t: "table", head: ["风险等级", "商家数", "签收单", "品质客诉单", "品质客诉率", "客诉占比"], widths: [1600, 1300, 1500, 1600, 1500, 1500],
    rows: ["正常", "需关注", "高风险"].map(t => [t, String(ST[t].sellers), num(ST[t].delivered), num(ST[t].qc), pct(ST[t].qc_rate), pct(SS[t].qc)]) },
  { t: "p", text: `${ST["高风险"].sellers} 家高风险商家占 ${pct(SS["高风险"].delivered)} 的签收单，贡献 ${pct(SS["高风险"].qc)} 的品质客诉，平均品质客诉率 ${pct(ST["高风险"].qc_rate)}，是正常商家（${pct(ST["正常"].qc_rate)}）的 ${(ST["高风险"].qc_rate / ST["正常"].qc_rate).toFixed(1)} 倍。按平滑客诉率从高到低排序，排在最前、合计占参评商家 10% 签收单的 ${D.pareto_top10pct_orders_sellers} 家商家，贡献了 ${pct(D.pareto_top10pct_orders_qc_share)} 的品质客诉。` },
  { t: "p", text: `名单可信吗？两项检验：① 统计显著性：平滑后圈出的 ${A.seller_ci.high_risk_n} 家高风险商家，Wilson 95% 置信区间下限全部高于平台客诉率；如果不平滑、按原始客诉率 ≥ 2 倍筛选，${A.seller_ci.raw2x_n} 家参评商家中有 ${A.seller_ci.raw2x_not_sig} 家并不显著，属于小样本噪声。② 预测力回测：用一个 6 个月窗口分层，看这些商家下一个 6 个月的表现。` },
  { t: "img", path: FIG("fig11_backtest.png"), w: 15, caption: "图 7　商家风险分层回测：检验期品质客诉率 ÷ 平台（三个滚动窗口）" },
  { t: "bullets", items: [
    `三个窗口合计，被判为高风险的商家（${BT.pooled["高风险"]["窗口商家数"]} 家次）下一期品质客诉率平均仍是平台的 ${BT.pooled["高风险"]["平均倍数"].toFixed(1)} 倍，需关注 ${BT.pooled["需关注"]["平均倍数"].toFixed(1)} 倍，正常 ${BT.pooled["正常"]["平均倍数"].toFixed(1)} 倍，排序在每个窗口都成立；商家前后两期客诉率的秩相关为 ${Math.min(...Object.values(BT.spearman)).toFixed(2)}–${Math.max(...Object.values(BT.spearman)).toFixed(2)}。`,
    `不平滑的规则圈出 ${BT.pooled["不平滑：原始客诉率 ≥ 2 倍"]["窗口商家数"]} 家次，下一期只有平台的 ${BT.pooled["不平滑：原始客诉率 ≥ 2 倍"]["平均倍数"].toFixed(2)} 倍：平滑用更少的名单换来了更高的命中。`,
    `均值回归：${BT.rows.filter(r => r["分组"] === "高风险" && r["检验期客诉率"] < r["训练期客诉率"]).length} 个窗口中高风险商家下一期客诉率明显回落（${BT.rows.filter(r => r["分组"] === "高风险" && r["检验期客诉率"] < r["训练期客诉率"]).map(r => pct(r["训练期客诉率"]) + " → " + pct(r["检验期客诉率"])).join("，")}）。评估整改效果必须设对照组，否则会把自然回落误判为整改成果。`,
  ] },

  { t: "h2", text: "3.6 瓶颈③：高风险品类与商品信息" },
  { t: "img", path: FIG("fig06_category_scatter.png"), w: 15, caption: "图 8　品类体量与品质客诉率（签收 ≥ 300 单的品类）" },
  { t: "bullets", items: [
    `办公家具品质客诉率 ${pct(CT[0].qc_rate)}，是平台的 ${(CT[0].qc_rate / D.overview.qc_rate).toFixed(1)} 倍：少件 / 漏发 ${pct(CT[0].missing_rate)}（缺螺丝、缺配件），质量缺陷 ${pct(CT[0].defect_rate)}。单件订单中 ≥ 15kg 大件的品质客诉率为 ${pct(D.heavy["4 ≥15kg"].qc)}，约为 1-5kg 商品（${pct(D.heavy["2 1-5kg"].qc)}）的 2 倍。`,
    `假货投诉集中在电脑配件（${(D.fake_top[1].fake_rate * 1e4).toFixed(0)} 单 / 万单）、钟表礼品（${(D.fake_top[3].fake_rate * 1e4).toFixed(0)} 单 / 万单），平台平均 ${(D.fake_platform * 1e4).toFixed(0)} 单 / 万单。`,
    `商品信息缺失（无品类、图片、描述）的单件订单，品质客诉率 ${pct(D.info["0 信息缺失"].qc)}、假货投诉率 ${pct(D.info["0 信息缺失"].fake, 2)}，后者约为信息完整商品的 9 倍。图片张数本身（1 张 vs 4 张以上）与品质客诉率关系不大。`,
  ] },

  { t: "h2", text: "3.7 放到唯品会的品类结构下" },
  { t: "p", text: `Olist 以家居、3C、美妆为主，穿戴类（服饰鞋包、钟表礼品、童装）只占签收单的 ${pct(VV.olist_wear_share)}；唯品会 2024 年穿戴类 GMV 占比约 75%（财报报道口径，见 data/external/）。因此把穿戴类单独拿出来看，并按唯品会的品类结构重新加权：` },
  { t: "img", path: FIG("fig09_wearables.png"), w: 15, caption: "图 9　穿戴类 vs 非穿戴类：品质客诉率与假货投诉（2017 vs 2018 年 1-8 月）" },
  { t: "bullets", items: [
    `穿戴类品质客诉率 ${pct(VV.wear["2017"].qc)} → ${pct(VV.wear["2018"].qc)}（z = ${VV.wear_z.toFixed(2)}，p = ${VV.wear_p.toFixed(3)}），涨幅 +${((VV.wear["2018"].qc / VV.wear["2017"].qc - 1) * 100).toFixed(0)}%，高于非穿戴类（${pct(VV.nonwear["2017"].qc)} → ${pct(VV.nonwear["2018"].qc)}，+${((VV.nonwear["2018"].qc / VV.nonwear["2017"].qc - 1) * 100).toFixed(0)}%）。`,
    `穿戴类假货投诉从每万单 ${VV.wear["2017"].fake10k.toFixed(0)} 升到 ${VV.wear["2018"].fake10k.toFixed(0)}，主要来自钟表礼品；非穿戴类 ${VV.nonwear["2017"].fake10k.toFixed(0)} → ${VV.nonwear["2018"].fake10k.toFixed(0)}。`,
    `服饰类（男装、女装、鞋靴、内衣、运动服饰，共 ${VV.apparel.n} 单）货不对板率 ${pct(VV.apparel.mismatch)}（95% 置信区间 ${ci(VV.apparel.mismatch_ci, 1)}），约为平台的 3 倍，尺码、颜色、材质与描述不符是服饰的主要品质问题。`,
    `按唯品会 75% 穿戴类的结构对 2018 年 1-8 月重新加权：整体品质客诉率变化不大（${pct(VV.reweight_2018.olist_mix.qc, 2)} → ${pct(VV.reweight_2018.vip_mix.qc, 2)}），但假货投诉从每万单 ${VV.reweight_2018.olist_mix.fake10k.toFixed(0)} 升到 ${VV.reweight_2018.vip_mix.fake10k.toFixed(0)}，少件 / 漏发从 ${pct(VV.reweight_2018.olist_mix.missing, 2)} 降到 ${pct(VV.reweight_2018.vip_mix.missing, 2)}。含义：唯品会场景下，正品管控和描述一致性的权重要高于 Olist，多件订单少件问题的权重较低。`,
  ] },
  { t: "p", text: "外部参考：国家市场监管总局的产品质量抽查结果与上面的方向一致。以下数字取自监管公告的新闻转载，引用前应核对原文，出处见 data/external/README.md：" },
  { t: "table", head: ["年份", "抽查范围", "产品", "批次 / 不合格", "不合格率", "要点"], widths: [700, 1900, 1700, 1300, 1000, 2400],
    rows: D.samr.map(r => [String(r.year), r.scope, r.product, r.batches === "" ? "—" : `${num(r.batches)} / ${num(r.unqualified_batches)}`, r.unqualified_rate === "" ? "—" : pct(r.unqualified_rate), r.note || "—"]) },
  { t: "p", text: "对品控的启示：① 电商渠道羽绒服不合格的主因是纤维含量、含绒量与标称不符，和本项目\"货不对板\"的上升方向一致，服饰类入仓质检应把成分 / 标签一致性列为必检项；② 小型企业不合格率（13.2%）约为大型企业（0.8%）的 16 倍，流通领域（19.6%）高于生产领域（6.7%），支持按供应商规模和历史表现做分层抽检（见 5.3）。" },

  { t: "h1", text: "4. 被证伪或证据不足的假设" },
  { t: "table", head: ["假设", "结论", "证据", "对决策的含义"], widths: [2100, 1100, 3200, 2600], rows: [
    ["新入驻商家品质更差", "不成立", `入驻 < 3 个月 ${pct(FZ.tenure["1 入驻<3个月"])}，12 个月以上 ${pct(FZ.tenure["4 12个月以上"])}`, "治理重点放在存量商家的持续监控"],
    ["送晚了导致更多损坏", "不成立", `延迟签收订单品质客诉率 ${pct(FZ.late["1"].qc)}，准时订单 ${pct(FZ.late["0"].qc)}；包装破损率几乎相同`, "物流时效与品质问题分开治理"],
    ["首单品质问题导致流失", "证据不足", `首单品质客诉用户复购率 ${pct(FZ.repurchase["1 首单品质客诉"].repurchase_rate)}，首单 5 星 ${pct(FZ.repurchase["4 首单5星"].repurchase_rate)}，平台整体复购约 4%`, "需唯品会会员与复购数据验证"],
  ] },

  { t: "h1", text: "5. 建议与治理测算" },
  { t: "img", path: FIG("fig07_sizing_waterfall.png"), w: 15, caption: "图 10　三项举措的品质客诉率治理测算" },
  { t: "p", text: `测算以 2018 年 1-8 月的 ${num(SZ.baseline_orders)} 个签收订单为基线（品质客诉率 ${pct(SZ.baseline_rate, 2)}）。每个品质客诉单按其命中的举措计算\"被避免的概率\"，多项举措叠加时 p = 1 − Π(1 − pᵢ)，避免重复计算。` },
  { t: "table", head: ["举措", "负责方", "测算假设", "预计降幅", "跟踪指标"], widths: [2400, 1300, 2300, 1200, 1800], rows: [
    ["A 多件订单出库复核 + 分包裹提醒", "仓配 / 商家", "多件订单少件客诉 −50%", "−" + (SZ.steps[0].delta_pp * 100).toFixed(2) + "pp", "多件订单少件率"],
    ["B 高风险 / 需关注商家整改", "商家管理", "该类商家品质客诉 −30%", "−" + (SZ.steps[1].delta_pp * 100).toFixed(2) + "pp", "高风险商家数、整改闭环率"],
    ["C 3C 数码 / 钟表礼品正品与描述专项", "品控 + 类目", "两类目假货、货不对板客诉 −30%", "−" + (SZ.steps[2].delta_pp * 100).toFixed(2) + "pp", "假货投诉率（每万单）"],
    ["合计", "", "", `${pct(SZ.baseline_rate, 2)} → ${pct(SZ.target_rate, 2)}`, "品质客诉率"],
  ] },
  { t: "h2", text: "5.1 情景与敏感性" },
  { t: "p", text: "上表中的降幅是假设参数，因此给出三档情景，并逐个变动参数看影响（其余参数取中性值）：" },
  { t: "table", head: ["情景", "A 多件订单少件客诉降幅", "B 风险商家客诉降幅", "C 3C / 钟表假货与货不对板降幅", "治理后品质客诉率"], widths: [1000, 2000, 1900, 2300, 1800],
    rows: ["悲观", "中性", "乐观"].map(k => [k, ...SC.scenarios[k].params.map(v => pct(v, 0)), pct(SC.scenarios[k].rate, 2)]) },
  { t: "img", path: FIG("fig12_scenarios.png"), w: 15, caption: "图 11　三档情景与单因素敏感性（龙卷风图）" },
  { t: "p", text: `即使悲观情景也能降到 ${pct(SC.scenarios["悲观"].rate, 2)}，中性情景 ${pct(SC.scenarios["中性"].rate, 2)} 达到 4.0% 目标。A 的假设影响最大（区间宽 ${(SC.tornado[0]["影响幅度"] * 100).toFixed(2)}pp），上线后应最先用试点验证多件订单复核的真实效果。测算基于规则打标口径；如果漏标在各类订单中分布相近，按校正系数换算后，降幅比例基本不变。` },
  { t: "h2", text: "5.2 举措说明" },
  { t: "bullets", items: [
    "A：多件订单出库前称重或逐件扫码复核；必须分包裹时，在订单页和消息里告知\"您的订单分 N 个包裹发出\"；评价邀请延后到全部包裹签收之后。",
    "B：高风险商家 30 天整改期（下架问题商品、补充商品信息、发货复核），复评仍为高风险则限流；需关注商家周度跟踪。",
    "C：3C / 钟表类目入驻时核验品牌授权；对高假货投诉商品抽检；商品详情页必须包含型号、规格、实拍图，缺失即不予上架（商品信息完整率 100% 作为准入卡口）。",
  ] },
  { t: "h2", text: "5.3 差异化抽检：质检资源按风险分配" },
  { t: "p", text: `举措 A、B、C 都需要质检 / 复核资源，关键是把有限的资源先投到风险最高的订单上。用 ${SA.train} 的数据给商家和\"商家 × 品类\"打风险分，在 ${SA.test} 的 ${num(SA.test_orders)} 个签收订单上做样本外检验：` },
  { t: "img", path: FIG("fig10_sampling_gain.png"), w: 15, caption: "图 12　增益曲线：按风险分从高到低抽检 X% 的订单，能覆盖多少问题订单（样本外）" },
  { t: "bullets", items: [
    `出库复核：只复核多件订单（占 ${pct(SA.multi_share, 0)}），就能覆盖 ${pct(SA.capture_at_10["出库复核：多件订单优先（少件问题）"], 0)} 的少件 / 漏发问题订单，少件问题几乎被订单结构锁定。`,
    `入仓抽检：抽 10% 时，按\"商家 × 品类\"风险分能覆盖 ${pct(SA.capture_at_10["商家 × 品类风险分"])} 的缺陷 / 货不对板 / 假货订单，随机抽检只有 ${pct(SA.capture_at_10["随机抽检"])}，是随机的 ${(SA.capture_at_10["商家 × 品类风险分"] / SA.capture_at_10["随机抽检"]).toFixed(2)} 倍；抽 20% 时为 ${pct(SA.capture_at_20["商家 × 品类风险分"], 0)} vs ${pct(SA.capture_at_20["随机抽检"], 0)}。`,
    "提升有限，是因为公开数据只有商家和品类两个维度。实际场景可以加入供应商历史质检结果、品牌授权、商品信息完整度、SKU 退货率等特征。外部抽检数据中小型企业与大型企业的不合格率相差约 16 倍，说明供应商维度的区分度很高。",
  ] },
  { t: "h2", text: "5.4 效果评估方法" },
  { t: "p", text: "举措 A、C 建议先在部分商家 / 仓库试点，与条件相近的对照组比较，用双重差分（试点前后变化 − 对照组前后变化）评估效果，观察 8 周；护栏指标为平均出库时长和发货超时率，防止复核拖慢发货。举措 B 要注意均值回归：被选为高风险的商家即使不干预，下期客诉率也可能回落，因此同样需要对照组。" },

  { t: "h1", text: "6. 局限与下一步" },
  { t: "bullets", items: [
    `评价不等于客诉工单：随机 200 条盲评显示规则准确率 ${pct(G.precision, 0)}、召回率 ${pct(G.recall, 0)}，品质客诉率绝对值被低估约 1/4（两年召回率相近，趋势结论不受影响）。打标判定由大模型完成，已附中文释义供人工抽查。接入客服工单与退货原因后可以交叉验证并替换。`,
    "缺少入仓质检、抽检数据：已在指标字典中定义入仓质检合格率、问题商品拦截率、品质退货率等过程指标，接入后可以把结果指标和过程指标连起来。",
    "巴西市场与唯品会的品类结构、履约模式不同：方法可以迁移，目标值（4.0%）、平滑参数（m = 50）、风险阈值需要用唯品会数据重新估计。",
    "最近月份存在右删失：评价和签收仍在回收，最后 1-2 个月的指标偏乐观，看板和周报中需标注。",
    "外部参考数据（监管抽检结果、唯品会品类结构）取自新闻转载与财报报道，数字引用前应核对原文。",
  ] },

  { t: "h1", text: "附录：项目文件" },
  { t: "table", head: ["内容", "位置"], widths: [3200, 5800], rows: [
    ["指标体系与指标字典", "docs/02_指标体系.md、docs/品控指标字典.xlsx"],
    ["交互看板与 BI 搭建指南", "dashboard/index.html、docs/04_BI看板设计与搭建指南.md"],
    ["SQL 面试题库（19 题）", "docs/05_SQL面试题库.md、sql/interview/"],
    ["数仓 SQL", "sql/01_ods_ddl.sql ~ sql/06_ads.sql"],
    ["分析明细表", "outputs/analysis_tables.xlsx"],
    ["数据质量报告、打标复核样本、金标准集（含中文释义）", "outputs/qa/"],
    ["进阶分析：控制图、显著性检验、回测、情景测算、差异化抽检", "scripts/13_advanced_analysis.py、outputs/advanced_tables.xlsx"],
    ["商家品质月报模板（Excel 公式 + 透视表）", "docs/商家品质月报模板.xlsx"],
    ["Tableau Public 搭建清单", "docs/07_Tableau_Public搭建清单.md"],
    ["外部参考数据（监管抽检、唯品会品类结构）", "data/external/"],
  ] },
];

module.exports = { meta, blocks };
