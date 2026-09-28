// 专题分析报告正文（只写一份，同时渲染成 Word 和 Markdown）
// 所有数字来自 outputs/deck_data.json；术语与数字格式以 docs/00_术语与口径.md 为准。
// 第 3、5 章每一节的结构相同：关键术语 → 结论 → 依据 → 动作（与讲稿、PPT 一致）。
const path = require("path");
const fs = require("fs");
const { F } = require("../ppt/deck_kit");

const ROOT = path.resolve(__dirname, "..");
const D = JSON.parse(fs.readFileSync(path.join(ROOT, "outputs", "deck_data.json"), "utf8"));
const FIG = f => path.join(ROOT, "outputs", "figures", f);

const T17 = D.type_by_year["2017"], T18 = D.type_by_year["2018M1-8"];
const DC = D.decomp_category, MI = D.multi_item, ST = D.seller_tier, SS = D.seller_tier_share, SZ = D.sizing;
const OT = D.order_type, FZ = D.falsify, CT = D.category_top;
const A = D.adv, SPC = A.spc, SIG = A.significance, VV = A.wear_view, SA = A.sampling, BT = A.backtest, SC = A.scenarios;
const G = D.gold, GY = D.gold_by_year, LM = SPC.last_month_check, KI = D.known_issues;
const ci = c => `${F.qc(c[0])} 至 ${F.qc(c[1])}`;
const Q = "下单月 2017-01 至 2018-08";
const OTN = { "1 单件": "单件订单", "2 同SKU多件": "同 SKU 多件", "3 单商家多SKU": "单商家多 SKU", "4 多商家": "多商家" };
const fakeAll = D.fake_counts.fake / D.fake_counts.n;
const fakeCat = name => { const r = D.fake_top.find(x => x.main_category_cn === name); return r.fake / r.n; };
const withInfo = ["1 1张图", "2 2-3张", "3 4张+"].reduce((a, k) => ({ n: a.n + D.info[k].n, f: a.f + D.info[k].fake * D.info[k].n }), { n: 0, f: 0 });
const rAll = Object.values(FZ.repurchase).reduce((a, x) => ({ n: a.n + x.customers, k: a.k + x.customers * x.repurchase_rate }), { n: 0, k: 0 });
const RAW = BT.pooled["对照：未平滑的品质客诉率 ≥ 商家基准品质客诉率 × 2"];
const hrDrop = BT.rows.filter(r => r["分组"] === "高风险" && r["检验期品质客诉率"] < r["训练期品质客诉率"]);

// 一节 = 标题 + 关键术语 + 结论 + 依据 + 动作
const sec = (title, term, conclusion, evidence, action) => [
  { t: "h2", text: title },
  { t: "kv", k: "关键术语", text: `${term[0]}——${term[1]}。` },
  { t: "kv", k: "结论", text: conclusion },
  ...evidence,
  { t: "kv", k: "动作", text: action },
];

const meta = {
  title: "差评率在下降，品质客诉率在上升",
  subtitle: "电商品控专题分析报告：品质问题在哪里、为什么、怎么治理",
  info: [
    ["数据", "Olist Brazilian E-Commerce Public Dataset（巴西电商平台公开的脱敏真实订单）"],
    ["分析范围", `${Q}，签收订单 ${F.int(D.counts.scope_delivered)} 个`],
    ["术语与口径", "docs/00_术语与口径.md；指标字典 v1.0（docs/品控指标字典.xlsx）"],
    ["复现", "python scripts/run_pipeline.py（MySQL 8.0）"],
  ],
};

const blocks = [
  { t: "h1", text: "摘要" },
  { t: "callout", items: [
    `结论：差评率在下降，品质客诉率在上升，而且是持续偏移。品质客诉率从 2017 年的 ${F.qc(DC.rate_A)} 升到 2018 年 1-8 月的 ${F.qc(DC.rate_B)}（z = ${F.z(SIG.qc.z)}，${F.p(SIG.qc.p)}），控制图上 2017-10 至 2018-08 连续 ${SPC.max_run_above} 个月高于中心线；差评率随准时签收率变化，下单月 2018-03 准时签收率 ${F.share(D.on_time_rate[14])}、差评率 ${F.share(D.bad_rate[14])}。`,
    `原因：上升来自组内效应（${F.pp(DC.within_effect)}），结构效应只有 ${F.pp(DC.mix_effect)}；差评品质原因占比从 2017Q1 的 ${F.share(D.mix.quality[0])} 升到 2018Q3 的 ${F.share(D.mix.quality[6])}。`,
    `问题：集中在三处。多件订单占签收订单 ${F.share(MI.order_share)}，贡献 ${F.share(MI.qc_share)} 的品质客诉订单；${ST["高风险"].sellers} 家高风险商家贡献 ${F.share(SS["高风险"].qc)} 的商家品质客诉订单；假货集中在电脑配件（${F.fake(fakeCat("电脑配件"))}）和钟表礼品（${F.fake(fakeCat("钟表礼品"))}）。`,
    `举措：多件订单出库复核、高风险商家和需关注商家整改、一级类目 3C数码、钟表与潮流好物的正品与商品描述专项，中性情景下把品质客诉率从 ${F.qc(SZ.baseline_rate)} 降到 ${F.qc(SC.scenarios["中性"].rate)}（悲观 ${F.qc(SC.scenarios["悲观"].rate)}，乐观 ${F.qc(SC.scenarios["乐观"].rate)}）。`,
    `可信度：${D.dq_checks} 项数据校验全部通过；标注样本 200 条，标签精确率 ${F.share(G.precision)}、标签召回率 ${F.share(G.recall)}，2017 年与 2018 年标签召回率相近，上升趋势不会被高估。`,
  ] },

  { t: "h1", text: "1. 背景与问题" },
  { t: "p", text: "2018 年差评率从 3 月的高点快速回落，直觉上会认为用户体验在改善。但差评由多种原因混合而成：没收到货、送得慢、服务差、商品本身有问题。品控关心的是其中\"商品本身有问题\"的部分是否也在改善。本报告回答四个问题：" },
  { t: "bullets", items: [
    "差评率下降，是否代表商品品质在改善？",
    "如果品质问题在上升，是结构效应（卖了更多高品质客诉率的类目），还是组内效应（同一类目自身变差）？",
    "品质问题集中在哪里：哪个标签、哪类订单、哪些商家、哪些品类？",
    "哪些举措可以落地，能把品质客诉率降到多少？",
  ] },

  { t: "h1", text: "2. 数据与口径" },
  { t: "h2", text: "2.1 数据来源" },
  { t: "p", text: `使用 Olist 公开的巴西电商平台真实订单数据：${F.int(D.counts.orders)} 个订单、${F.int(D.counts.items)} 个商品行、${F.int(D.counts.reviews_raw)} 条评价（每个订单只取最后一次评价后为 ${F.int(D.counts.reviews)} 条）、${F.int(D.counts.sellers)} 家商家、${F.int(D.counts.products)} 个商品、${D.counts.categories} 个品类。2016 年和 2018-09 以后的订单很少，分析范围取${Q}。` },
  { t: "table", head: ["品控环节", "本项目数据", "说明"], widths: [2600, 3400, 3000], rows: [
    ["供应商 / 品牌方", "Olist 商家（seller）", "直接对应"],
    ["客诉记录", "最后一次评价的星级 + 葡语评价文字", "用关键词规则识别标签"],
    ["发货时效", "平台规定发货时限（shipping_limit_date）", "直接对应"],
    ["商品详情质量", "品类、图片数、描述字数", "对应动销商品信息完整率"],
    ["入仓质检 / 退货原因", "无", "口径已定义，待接入"],
  ] },
  { t: "h2", text: "2.2 核心概念：品质客诉率" },
  { t: "p", text: "品质客诉率 = 品质客诉订单数 ÷ 签收订单数；分子、分母按同一下单月归属，保证是同一批订单。品质客诉订单要同时满足三个条件：" },
  { t: "bullets", items: [
    "是签收订单：订单状态为\"已签收\"（delivered）且签收时间不为空；",
    "最后一次评价为 1-3 星：同一订单有多条评价时，只使用提交时间最晚的一条；",
    "最后一次评价的文字命中至少一个品质问题标签：假货、质量缺陷、货不对板、少件漏发、包装破损。",
  ] },
  { t: "p", text: "一个订单可以同时命中多个标签，所以 5 个结果指标（命中该标签的品质客诉订单数 ÷ 签收订单数）之和大于品质客诉率。需要互斥的结构占比时使用主标签：按\"假货 > 质量缺陷 > 货不对板 > 少件漏发 > 包装破损 > 未收到货 > 物流延迟 > 服务售后\"的优先级取一个标签。" },
  { t: "h2", text: "2.3 标签识别规则与标注样本" },
  { t: "p", text: "公开数据没有客诉记录，本项目用葡语关键词规则从评价文字中识别 8 个标签（5 个品质问题标签、3 个履约服务标签）。规则先做小写与去重音处理，并剔除\"sem defeito（没有瑕疵）\"这类否定表述。规则迭代期（v0.4）按规则结果分层抽取 140 条评价逐条复核，据判错的样本修正了 8 条规则；定版（v1.0）后用标注样本评估：" },
  { t: "p", text: `标注样本从 ${F.int(D.gold_population)} 条"签收订单、最后一次评价 1-3 星、有文字"的评价中随机抽取 200 条，由大模型逐条阅读葡语原文给出真实标签（判定时不看规则结果），每条附中文释义，明细在 outputs/qa/tag_gold_set.csv，可逐条人工抽查。` },
  { t: "table", head: ["品质问题标签", "标注样本中的条数", "标签精确率", "标签召回率"], widths: [3000, 2000, 2000, 2000],
    rows: Object.entries(D.gold_by_type).map(([k, v]) => [k, String(v.support), v.precision == null ? "—" : F.share(v.precision), v.recall == null ? "—" : F.share(v.recall)])
      .concat([["合计", String(G.support), F.share(G.precision), F.share(G.recall)]]) },
  { t: "bullets", items: [
    `标签精确率 = 规则判为品质问题、且标注样本也判为品质问题的评价数 ÷ 规则判为品质问题的评价数；标签召回率的分母换成标注样本判为品质问题的评价数。规则的标签精确率高、标签召回率偏低，属于偏保守；漏标主要是货不对板的口语化说法和"只收到部分商品"。`,
    `绝对值：品质客诉率的真实值约为规则值 × 标签精确率 ÷ 标签召回率（倍数 ${F.times(D.gold_cf)}），2018 年 1-8 月约 ${F.qc(SC.baseline * D.gold_cf)}。报告中的品质客诉率一律是规则值，是保守值。`,
    `趋势：标注样本中下单年份为 2017 年、2018 年的评价，标签召回率分别为 ${F.share(GY["2017"].recall)}、${F.share(GY["2018"].recall)}（${GY["2017"].support} 条 / ${GY["2018"].support} 条）。2018 年不高于 2017 年，所以真实的上升幅度只会更大，两年对比不受漏标影响。`,
  ] },
  { t: "h2", text: "2.4 数据校验" },
  { t: "p", text: `每次运行自动执行 ${D.dq_checks} 项数据校验（跨层对账、主键唯一、分子不大于分母、比率在 0 到 1 之间等），任一项不通过就不输出结果；本次全部通过。已知数据问题写明处理方式、不悄悄删除：时间倒挂 ${F.int(KI["时间倒挂（发货早于下单 / 签收早于发货）"])} 个订单、有多条评价 ${F.int(KI["同一订单多条评价"])} 个订单、支付金额与商品金额不一致 ${F.int(KI["支付金额与商品+运费不一致(差额>1)"])} 个订单，详见 outputs/qa/dq_report.md。` },

  { t: "h1", text: "3. 分析发现" },
  ...sec("3.1 结论①：品质客诉率持续偏移，差评率跟着准时签收率变化",
    ["持续偏移", "控制图上连续 9 个及以上月份落在中心线同一侧，说明变化不是随机波动"],
    `品质客诉率从 2017 年的 ${F.qc(DC.rate_A)} 升到 2018 年 1-8 月的 ${F.qc(DC.rate_B)}，是持续偏移；同期差评率的下降来自物流改善。`,
    [
      { t: "img", path: FIG("fig01_trend_small_multiples.png"), w: 16, caption: "图 1　差评率、准时签收率与品质客诉率（三个指标量纲不同，分开画，不使用双轴）" },
      { t: "p", text: `差评率与准时签收率几乎是镜像：下单月 2018-03 准时签收率降到 ${F.share(D.on_time_rate[14])}，差评率升到 ${F.share(D.bad_rate[14])}；2018-08 准时签收率回到 ${F.share(D.on_time_rate[19])}，差评率回落到 ${F.share(D.bad_rate[19])}。品质客诉率的走势与之无关。` },
      { t: "img", path: FIG("fig08_p_chart.png"), w: 16, caption: `图 2　品质客诉率控制图（中心线 = 2017 年品质客诉率 ${F.qc(SPC.p0)}；控制限 = 中心线 ± 3σ，随当月签收订单数变化）` },
      { t: "p", text: `控制图：中心线 = 2017 年的品质客诉率 ${F.qc(SPC.p0)}；上控制限 / 下控制限 = 中心线 ± 3 × √（中心线 × (1 − 中心线) ÷ 当月签收订单数）。2017 年 12 个月均在控制限内；${SPC.beyond_ucl_months.join("、")} 越限（当月品质客诉率高于上控制限）；2017-10 至 2018-08 连续 ${SPC.max_run_above} 个月高于中心线，构成持续偏移。` },
      { t: "table", head: ["检验", "结果", "结论"], widths: [3200, 3800, 2000], rows: [
        ["2017 年 vs 2018 年 1-8 月品质客诉率（两比例 z 检验）", `z = ${F.z(SIG.qc.z)}，${F.p(SIG.qc.p)}`, "显著上升"],
        ["95% 置信区间（Wilson）", `2017 年 ${ci(SIG.qc.ci2017)}；2018 年 1-8 月 ${ci(SIG.qc.ci2018)}`, "区间不重叠"],
        ["货不对板客诉率 / 假货客诉率", `z = ${F.z(SIG.mismatch.z)}（${F.p(SIG.mismatch.p)}）/ z = ${F.z(SIG.fake.z)}（${F.p(SIG.fake.p)}）`, "均显著上升"],
      ] },
      { t: "p", text: `最后一个月：2018-08 品质客诉率回落到 ${F.qc(LM.aug_rate)}（2018-07 为 ${F.qc(LM.jul_rate)}）。评价回收率（有评价的签收订单 ÷ 签收订单）8 月 ${F.share(LM.aug_review_rate)}、7 月 ${F.share(LM.jul_review_rate)}，相当；只统计签收后 7 天内提交的评价，8 月 ${F.qc(LM.aug_rate_7d)} 仍低于 7 月 ${F.qc(LM.jul_rate_7d)}。但与 7 月的差异不显著（z = ${F.z(LM.z)}，${F.p(LM.p)}），且仍在控制限内，只能作为回落信号继续观察。` },
    ],
    "考核品控用品质客诉率，差评率只作为体验指标观察；每月用控制图判断是否越限或持续偏移。"),

  ...sec("3.2 结论②：差评里品质问题的占比在上升",
    ["差评品质原因占比", "最后一次评价为差评（1-2 星）的订单中，主标签属于品质问题标签的订单所占的比例（分母含无文字的差评）"],
    `差评品质原因占比从 2017Q1 的 ${F.share(D.mix.quality[0])} 升到 2018Q3 的 ${F.share(D.mix.quality[6])}。`,
    [
      { t: "img", path: FIG("fig02_bad_review_reason_mix.png"), w: 16, caption: "图 3　差评订单按主标签分类（按下单季度；2018Q3 只有 7、8 两个月）" },
      { t: "p", text: `2017 年四个季度，差评品质原因占比在 ${F.share(Math.min(...D.mix.quality.slice(0, 4)))} 至 ${F.share(Math.max(...D.mix.quality.slice(0, 4)))} 之间；2018Q2、2018Q3 为 ${F.share(D.mix.quality[5])}、${F.share(D.mix.quality[6])}。主标签为履约服务标签的差评占比在 2018Q1 最高（${F.share(D.mix.fulfill[4])}），之后回落。` },
    ],
    "物流问题缓解之后，差评里剩下的品质问题交给品控治理。"),

  ...sec("3.3 结论③：上升来自组内效应",
    ["组内效应", "Σ（2017 年各一级类目签收订单占比 × 该类目品质客诉率的变化），衡量同一类目自身变差带来的变化；结构效应 = Σ（各类目签收订单占比的变化 × 2017 年该类目品质客诉率）"],
    `品质客诉率变化 ${F.pp(DC.rate_B - DC.rate_A)}，其中组内效应 ${F.pp(DC.within_effect)}、结构效应 ${F.pp(DC.mix_effect)}、交互项 ${F.pp(DC.interaction)}：上升来自同一类目自身变差，而不是卖了更多高品质客诉率的类目。`,
    [
      { t: "p", text: `整体品质客诉率 = Σ（各一级类目签收订单占比 × 该类目品质客诉率），所以两期之差 = 结构效应 + 组内效应 + 交互项。按单件订单 / 多件订单分解，结构效应同样很小（${F.pp(D.decomp_order_type.mix_effect)}）。组内效应最大的一级类目依次是：${Object.keys(D.decomp_category_top).join("、")}。` },
      { t: "img", path: FIG("fig03_type_yoy.png"), w: 15, caption: "图 4　5 个结果指标：2017 年 vs 2018 年 1-8 月" },
      { t: "p", text: `分标签看：货不对板客诉率 ${F.qc(T17.mismatch)} → ${F.qc(T18.mismatch)}，假货客诉率 ${F.fake(T17.fake)} → ${F.fake(T18.fake)}，少件漏发客诉率 ${F.qc(T17.missing)} → ${F.qc(T18.missing)}，质量缺陷客诉率 ${F.qc(T17.defect)} → ${F.qc(T18.defect)}。问题更多出在"描述与实物不符"和"正品"，而不是商品质量本身。` },
    ],
    "治理对象是具体类目里的订单、商家和商品，而不是调整品类结构。"),

  ...sec("3.4 问题①：多件订单",
    ["多件订单", "件数不少于 2 的签收订单（件数 = 订单包含的商品行数），分为同 SKU 多件、单商家多 SKU、多商家三类"],
    `多件订单占签收订单 ${F.share(MI.order_share)}，贡献 ${F.share(MI.qc_share)} 的品质客诉订单，增加的部分主要是少件漏发。`,
    [
      { t: "img", path: FIG("fig04_order_structure.png"), w: 15, caption: `图 5　不同订单结构的品质客诉率（${Q}；黑色为命中少件漏发标签的部分）` },
      { t: "table", head: ["订单结构", "签收订单数", "占签收订单", "品质客诉率", "少件漏发客诉率", "差评率"], widths: [2000, 1400, 1300, 1500, 1500, 1300],
        rows: Object.keys(OT).sort().map(k => [OTN[k], F.int(OT[k].n), F.share(OT[k].order_share), F.qc(OT[k].qc), F.qc(OT[k].missing), F.share(OT[k].bad_rate)]) },
      { t: "p", text: `多件订单品质客诉率 ${F.qc(MI.multi_qc)}，是单件订单 ${F.qc(MI.single_qc)} 的 ${F.times(MI.multi_qc / MI.single_qc)}；全部少件漏发客诉订单中，${F.share(MI.missing_share)} 来自多件订单。多件订单中命中少件漏发标签的品质客诉订单，${F.share(MI.review_after_delivered)} 的评价日期不早于签收日期：不是"还没收齐就评价"，而是签收后确实缺件——漏发，或分包裹没有同时送达、也没有告知用户。两种情况都指向出库环节。` },
    ],
    "举措 A：多件订单出库复核 + 分包裹提醒（见第 5 章）。"),

  ...sec("3.5 问题②：高风险商家",
    ["高风险商家", "参评商家中，平滑品质客诉率 ≥ 商家基准品质客诉率 × 2，且商家品质客诉订单不少于 3 单的商家"],
    `${ST["高风险"].sellers} 家高风险商家占参评商家的 ${F.share(SS["高风险"].sellers)}、商家签收订单的 ${F.share(SS["高风险"].delivered)}，贡献 ${F.share(SS["高风险"].qc)} 的商家品质客诉订单；回测中下一个 6 个月仍是商家基准品质客诉率的 ${F.times(BT.pooled["高风险"]["平均倍数"])}。`,
    [
      { t: "img", path: FIG("fig05_seller_tier.png"), w: 15, caption: `图 6　${D.seller_eligible} 家参评商家的构成（商家评估窗口：下单月 2018-03 至 2018-08）` },
      { t: "bullets", items: [
        "参评商家：商家评估窗口内商家签收订单不少于 30 单的商家；一个订单含多个商家时，每个商家各计 1 单（商家签收订单、商家品质客诉订单）。",
        `商家基准品质客诉率 = 商家评估窗口内全部商家的商家品质客诉订单之和 ÷ 商家签收订单之和 = ${F.qc(D.seller_benchmark)}；一个订单含多个商家时重复计入，所以不等于品质客诉率。`,
        "平滑品质客诉率 =（商家品质客诉订单数 + 50 × 商家基准品质客诉率）÷（商家签收订单数 + 50）：给每个商家先加 50 单\"商家基准水平\"的虚拟订单，避免\"10 单里 1 单 = 10%\"的小样本商家被误判。",
        "商家品质分 = 品质客诉率 50% + 差评率 20% + 发货超时率 15% + 准时签收率 15%，每项按参评商家中的百分位排名打分，只用于商家之间排序。",
      ] },
      { t: "table", head: ["商家分层", "商家数", "商家签收订单数", "商家品质客诉订单数", "品质客诉率", "商家品质客诉订单占比"], widths: [1600, 1200, 1600, 1800, 1400, 1400],
        rows: ["正常", "需关注", "高风险"].map(t => [t + "商家", String(ST[t].sellers), F.int(ST[t].delivered), F.int(ST[t].qc), F.qc(ST[t].qc_rate), F.share(SS[t].qc)]) },
      { t: "p", text: `名单是否可信，做了两项检验。① 显著性：${A.seller_ci.high_risk_sig} 家高风险商家的 Wilson 95% 置信区间下限都高于商家基准品质客诉率；如果不平滑、只看未平滑的品质客诉率 ≥ 商家基准 × 2，${A.seller_ci.raw2x_n} 家参评商家中有 ${A.seller_ci.raw2x_not_sig} 家并不显著。② 回测：用一个 6 个月窗口（训练期）分层，看同一批商家在接下来 6 个月（检验期）的表现。` },
      { t: "img", path: FIG("fig11_backtest.png"), w: 15, caption: "图 7　回测：检验期品质客诉率 ÷ 检验期商家基准品质客诉率（3 组窗口）" },
      { t: "bullets", items: [
        `3 组窗口按商家数加权：高风险商家（${BT.pooled["高风险"]["窗口商家数"]} 家次）${F.times(BT.pooled["高风险"]["平均倍数"])}，需关注商家 ${F.times(BT.pooled["需关注"]["平均倍数"])}，正常商家 ${F.times(BT.pooled["正常"]["平均倍数"])}；每组窗口的排序都成立。`,
        `对照：未平滑的品质客诉率 ≥ 商家基准 × 2 的规则圈出 ${RAW["窗口商家数"]} 家次，检验期只有 ${F.times(RAW["平均倍数"])}：平滑后名单更短、倍数更高。`,
        `回落：${hrDrop.length} 组窗口中，高风险商家的品质客诉率从训练期到检验期回落（${hrDrop.map(r => F.qc(r["训练期品质客诉率"]) + " → " + F.qc(r["检验期品质客诉率"])).join("，")}）。评估整改效果必须设对照组，否则会把自然回落误判为整改成果。`,
      ] },
    ],
    "举措 B：高风险商家和需关注商家整改；评估效果时设对照组。"),

  ...sec("3.6 问题③：假货与高风险品类",
    ["假货客诉率", "命中假货标签的品质客诉订单数 ÷ 签收订单数，以\"单/万单\"表示（每 1 万个签收订单中的个数）"],
    `假货集中在电脑配件（${F.fake(fakeCat("电脑配件"))}）和钟表礼品（${F.fake(fakeCat("钟表礼品"))}），全部签收订单为 ${F.fake(fakeAll)}（${Q}，按主品类）。`,
    [
      { t: "img", path: FIG("fig06_category_scatter.png"), w: 15, caption: `图 8　主品类的体量与品质客诉率（${Q}，签收订单 ≥ 300 的主品类）` },
      { t: "bullets", items: [
        `${CT[0].category_cn}：品质客诉率 ${F.qc(CT[0].qc_rate)}，是全部签收订单（${F.qc(D.overview.qc_rate)}）的 ${F.times(CT[0].qc_rate / D.overview.qc_rate)}；少件漏发客诉率 ${F.qc(CT[0].missing_rate)}，质量缺陷客诉率 ${F.qc(CT[0].defect_rate)}。单件订单中主商品重量 ≥ 15kg 的，品质客诉率 ${F.qc(D.heavy["4 ≥15kg"].qc)}，是 1-5kg 商品（${F.qc(D.heavy["2 1-5kg"].qc)}）的 ${F.times(D.heavy["4 ≥15kg"].qc / D.heavy["2 1-5kg"].qc)}。`,
        `商品信息缺失：单件订单中，主商品缺少品类、图片、描述信息的，假货客诉率 ${F.fake(D.info["0 信息缺失"].fake)}；有 1 张及以上图片的 ${F.fake(withInfo.f / withInfo.n)}。图片张数本身（1 张 vs 4 张及以上）与品质客诉率关系不大。`,
      ] },
    ],
    "举措 C：一级类目 3C数码、钟表与潮流好物的正品与商品描述专项；商品信息缺一项不允许上架。"),

  ...sec("3.7 品类结构：穿戴类",
    ["品类结构重加权", `把穿戴类在签收订单中的占比从 ${F.share(VV.olist_wear_share)} 调为 75%，其余 25% 为非穿戴类，用两类各自 2018 年 1-8 月的指标重算整体指标；75% 取自唯品会 2024 年财报报道的穿戴类 GMV 占比，这里用 GMV 占比近似订单占比`],
    `穿戴类占比调为 75% 时，2018 年 1-8 月的假货客诉率从 ${F.fake(VV.reweight_2018.olist_mix.fake10k / 1e4)} 升到 ${F.fake(VV.reweight_2018.target_mix.fake10k / 1e4)}，品质客诉率变化不大（${F.qc(VV.reweight_2018.olist_mix.qc)} → ${F.qc(VV.reweight_2018.target_mix.qc)}）。`,
    [
      { t: "p", text: "穿戴类：主品类属于一级类目\"服饰鞋包\"（箱包配饰、鞋靴、运动服饰、女装、男装、内衣泳装、旅行箱包），或主品类为\"钟表礼品\"\"童装\"的签收订单。" },
      { t: "img", path: FIG("fig09_wearables.png"), w: 15, caption: "图 9　穿戴类 vs 非穿戴类：品质客诉率与假货客诉率（2017 年 vs 2018 年 1-8 月）" },
      { t: "bullets", items: [
        `穿戴类品质客诉率 ${F.qc(VV.wear["2017"].qc)} → ${F.qc(VV.wear["2018"].qc)}（z = ${F.z(VV.wear_z)}，${F.p(VV.wear_p)}）；非穿戴类 ${F.qc(VV.nonwear["2017"].qc)} → ${F.qc(VV.nonwear["2018"].qc)}。`,
        `穿戴类假货客诉率 ${VV.wear["2017"].fake10k.toFixed(1)} → ${VV.wear["2018"].fake10k.toFixed(1)} 单/万单，主要来自钟表礼品；非穿戴类 ${VV.nonwear["2017"].fake10k.toFixed(1)} → ${VV.nonwear["2018"].fake10k.toFixed(1)} 单/万单。`,
        `服装（主品类为男装、女装、鞋靴、内衣泳装、运动服饰，共 ${F.int(VV.apparel.n)} 个签收订单）货不对板客诉率 ${F.qc(VV.apparel.mismatch)}（95% 置信区间 ${ci(VV.apparel.mismatch_ci)}）：尺码、颜色、材质与描述不符是服装的主要品质问题。Olist 的服装样本小，结论是方向性的。`,
      ] },
      { t: "p", text: "外部参考：国家市场监督管理总局的产品质量抽查结果（数字取自公告及其新闻转载，引用前应核对原文，出处见 data/external/README.md）。" },
      { t: "table", head: ["年份", "抽查范围", "产品", "批次 / 不合格批次", "不合格率", "要点"], widths: [700, 1900, 1700, 1400, 1000, 2300],
        rows: D.samr.map(r => [String(r.year), r.scope, r.product, r.batches === "" ? "—" : `${F.int(r.batches)} / ${F.int(r.unqualified_batches)}`, r.unqualified_rate === "" ? "—" : F.share(r.unqualified_rate), r.note || "—"]) },
      { t: "p", text: "与本项目方向一致的两点：电商渠道羽绒服不合格的主因是纤维含量、含绒量与标称不符，属于货不对板；小型企业、流通领域的不合格率明显高于大型企业、生产领域（见上表要点），支持按供应商规模和历史表现分配抽检（见 5.4）。" },
    ],
    "穿戴类入仓质检把成分、标签与商品描述是否一致列为必检项。"),

  { t: "h1", text: "4. 不成立或证据不足的假设" },
  { t: "table", head: ["假设", "结论", "证据", "对决策的含义"], widths: [2100, 1100, 3300, 2500], rows: [
    ["新入驻商家品质更差", "不成立", `入驻不足 3 个月的商家 ${F.qc(FZ.tenure["1 入驻<3个月"])}，入驻 12 个月以上 ${F.qc(FZ.tenure["4 12个月以上"])}（按商家签收订单计算，下单月 2017-07 至 2018-08；入驻时长 = 下单时间 − 商家第一个订单的时间）`, "治理重点放在存量商家的持续监控"],
    ["送晚了导致更多损坏", "不成立", `延迟签收订单品质客诉率 ${F.qc(FZ.late["1"].qc)}，准时签收订单 ${F.qc(FZ.late["0"].qc)}；包装破损客诉率 ${F.qc(FZ.late["1"].package)} vs ${F.qc(FZ.late["0"].package)}（延迟签收订单：签收日期晚于承诺送达日期的签收订单）`, "物流时效与品质问题分开治理"],
    ["首单遇到品质问题会流失", "证据不足", `首单为品质客诉订单的用户复购率 ${F.share(FZ.repurchase["1 首单品质客诉"].repurchase_rate)}，首单 5 星 ${F.share(FZ.repurchase["4 首单5星"].repurchase_rate)}，全部用户 ${F.share(rAll.k / rAll.n)}（复购率：首单早于 2018-03-01、首单签收且有评价的用户中，分析范围内下过 2 个及以上订单的用户所占比例）`, "需要会员与复购数据验证"],
  ] },

  { t: "h1", text: "5. 举措与治理测算" },
  ...sec("5.1 治理测算",
    ["治理测算", "以 2018 年 1-8 月的签收订单为基期，估算三项举措实施后的品质客诉率；一个品质客诉订单被多项举措覆盖时，避免概率按 1 − Π(1 − 各举措降幅) 叠加"],
    `中性情景下，三项举措把品质客诉率从 ${F.qc(SZ.baseline_rate)} 降到 ${F.qc(SZ.target_rate)}。`,
    [
      { t: "img", path: FIG("fig07_sizing_waterfall.png"), w: 15, caption: "图 10　治理测算：中性情景下三项举措对品质客诉率的影响" },
      { t: "table", head: ["举措", "作用对象", "中性降幅", "品质客诉率变化", "跟踪指标"], widths: [2200, 2900, 1000, 1300, 1600], rows: [
        ["A 多件订单出库复核 + 分包裹提醒", "多件订单中命中少件漏发标签的品质客诉订单", "50%", F.pp(-SZ.steps[0].delta_pp), "多件订单少件漏发客诉率"],
        ["B 高风险商家和需关注商家整改", "主商家为高风险商家或需关注商家的品质客诉订单", "30%", F.pp(-SZ.steps[1].delta_pp), "高风险商家数、高风险商家整改完成率"],
        ["C 3C数码、钟表与潮流好物正品与商品描述专项", "主品类属于这两个一级类目、且命中假货或货不对板标签的品质客诉订单", "30%", F.pp(-SZ.steps[2].delta_pp), "假货客诉率、货不对板客诉率"],
        ["合计", `基期 ${F.int(SZ.baseline_orders)} 个签收订单`, "", `${F.qc(SZ.baseline_rate)} → ${F.qc(SZ.target_rate)}`, "品质客诉率"],
      ] },
    ],
    "降幅是假设参数，和业务方一起校准后再更新测算。"),
  ...sec("5.2 情景与敏感性",
    ["情景", "举措降幅的三组假设：悲观（A 30%、B 15%、C 15%）、中性（50%、30%、30%）、乐观（70%、45%、45%）"],
    `悲观情景 ${F.qc(SC.scenarios["悲观"].rate)}，中性 ${F.qc(SC.scenarios["中性"].rate)}，乐观 ${F.qc(SC.scenarios["乐观"].rate)}；最敏感的是举措 A 的降幅。`,
    [
      { t: "table", head: ["情景", "举措 A 降幅", "举措 B 降幅", "举措 C 降幅", "治理后品质客诉率"], widths: [1400, 1900, 1900, 1900, 1900],
        rows: ["悲观", "中性", "乐观"].map(k => [k + "情景", ...SC.scenarios[k].params.map(v => `${Math.round(v * 100)}%`), F.qc(SC.scenarios[k].rate)]) },
      { t: "img", path: FIG("fig12_scenarios.png"), w: 15, caption: "图 11　治理测算：三组情景下的品质客诉率" },
      { t: "p", text: `单因素敏感性（每次只改一项举措的降幅，其余取中性值）：举措 A 从悲观取到乐观，治理后品质客诉率相差 ${F.pp(SC.tornado[0]["影响幅度"]).replace("+", "")}，影响最大。测算基于规则识别的品质客诉订单；如果漏标在各类订单中分布相近，按真实值换算后降幅比例基本不变。` },
    ],
    "上线后最先用试点验证举措 A 的真实降幅。"),
  ...sec("5.3 举措说明",
    ["举措 A / B / C", "分别作用于多件订单、高风险商家和需关注商家、一级类目 3C数码、钟表与潮流好物，与第 3 章的三处问题一一对应"],
    "三项举措分别落在仓配出库、商家管理、商品准入三个环节。",
    [
      { t: "bullets", items: [
        "A：多件订单出库前称重或逐件扫码复核；必须分包裹时，在订单页和消息里告知\"您的订单分 N 个包裹发出\"；评价邀请延后到全部包裹签收之后。",
        "B：高风险商家 30 天整改期（下架问题商品、补充商品信息、发货复核），复评仍为高风险商家则限流；需关注商家每周跟踪。",
        "C：入驻时核验品牌授权；对假货客诉率高的商品抽检；商品详情必须包含型号、规格、实拍图，缺一项不允许上架（动销商品信息完整率目标 100%）。",
      ] },
    ],
    "每项举措指定跟踪指标（见 5.1 表），在看板上每月复盘。"),
  ...sec("5.4 差异化抽检",
    ["问题订单覆盖率", "按风险分从高到低抽检一定比例的签收订单时，抽到的问题订单数 ÷ 全部问题订单数；入仓类问题订单 = 命中质量缺陷、货不对板或假货标签的品质客诉订单，出库类问题订单 = 命中少件漏发标签的品质客诉订单"],
    `出库只复核多件订单，就能覆盖 ${F.share(SA.capture_at_10["出库复核：多件订单优先"])} 的出库类问题订单；入仓抽检 10% 时，按商家 × 品类风险分抽检的覆盖率 ${F.share(SA.capture_at_10["商家 × 品类风险分"])}，随机顺序 ${F.share(SA.capture_at_10["随机抽检"])}。`,
    [
      { t: "p", text: `风险分用 2017-09 至 2018-02 的签收订单计算（商家风险分 = 主商家的平滑入仓类问题率；商家 × 品类风险分再乘以主品类的平滑入仓类问题率 ÷ 全部签收订单的入仓类问题率），在下单月 2018-03 至 2018-08 的 ${F.int(SA.test_orders)} 个签收订单上检验（样本外）。` },
      { t: "img", path: FIG("fig10_sampling_gain.png"), w: 15, caption: "图 12　增益曲线：横轴为抽检比例，纵轴为问题订单覆盖率（样本外检验）" },
      { t: "bullets", items: [
        `出库复核：多件订单占签收订单 ${F.share(SA.multi_share)}，复核全部多件订单即可覆盖 ${F.share(SA.capture_at_10["出库复核：多件订单优先"])} 的出库类问题订单，少件漏发几乎被订单结构锁定。`,
        `入仓抽检：抽检比例 10% 时，商家 × 品类风险分 ${F.share(SA.capture_at_10["商家 × 品类风险分"])} vs 随机顺序 ${F.share(SA.capture_at_10["随机抽检"])}（${F.times(SA.capture_at_10["商家 × 品类风险分"] / SA.capture_at_10["随机抽检"])}）；抽检比例 20% 时 ${F.share(SA.capture_at_20["商家 × 品类风险分"])} vs ${F.share(SA.capture_at_20["随机抽检"])}。`,
        "入仓抽检提升有限，是因为公开数据只有商家和品类两个特征；接入商家历史质检结果、品牌授权、商品信息完整度后，风险分会更准。",
      ] },
    ],
    "入仓抽检按商家 × 品类风险分排序；接入商家历史质检结果后重新计算风险分。"),
  ...sec("5.5 效果评估",
    ["双重差分", "（试点组实施后 − 实施前）−（对照组同期的后 − 前），用来剔除同期的共同变化"],
    "举措 A、C 先在部分仓库或商家试点，用双重差分评估效果。",
    [
      { t: "p", text: "试点观察 8 周；同时跟踪平均发货时长和发货超时率，防止复核拖慢发货。举措 B 要注意回落：被选为高风险商家的商家即使不干预，下期品质客诉率也可能回落（见 3.5），所以同样需要对照组。" },
    ],
    "先在部分仓库试点举措 A，用试点组相对对照组的变化评估效果。"),

  { t: "h1", text: "6. 局限与下一步" },
  { t: "bullets", items: [
    `评价不等于客诉记录：标签精确率 ${F.share(G.precision)}、标签召回率 ${F.share(G.recall)}，品质客诉率的绝对值偏低；两年的标签召回率相近，趋势结论不受影响。接入客服记录与退货原因后可以交叉验证。`,
    "没有入仓质检、抽检数据：入仓质检合格率、问题商品拦截率、品质退货率的口径已在指标字典中定义，接入后可以把结果指标和过程指标连起来。",
    "单一平台：品类结构、履约模式与其他平台不同；方法可以迁移，平滑参数（50 单）、预警规则需要用新数据重新校准。",
    "最近月份的订单还有一部分没有签收或评价，最近 1-2 个月的数字会被后续评价修正，周报中需要标注。",
    "外部参考数据（监管抽查结果、穿戴类 GMV 占比）取自公告、新闻转载与财报报道，引用前应核对原文。",
  ] },

  { t: "h1", text: "附录：项目文件" },
  { t: "table", head: ["内容", "位置"], widths: [3200, 5800], rows: [
    ["术语与口径", "docs/00_术语与口径.md"],
    ["指标体系与指标字典", "docs/02_指标体系.md、docs/品控指标字典.xlsx"],
    ["交互看板与 BI 搭建指南", "dashboard/index.html、docs/04_BI看板设计与搭建指南.md"],
    [`SQL 取数题库（${D.sql_total} 题）`, "docs/05_SQL面试题库.md、sql/interview/"],
    ["数仓 SQL", "sql/01_ods_ddl.sql 至 sql/06_ads.sql"],
    ["分析明细表", "outputs/analysis_tables.xlsx、outputs/advanced_tables.xlsx"],
    ["数据校验报告、标注样本（含中文释义）", "outputs/qa/"],
    ["商家品质月报模板（Excel 公式 + 数据透视表）", "docs/商家品质月报模板.xlsx"],
    ["面试讲稿", "docs/10_面试讲稿.md"],
    ["外部参考数据", "data/external/"],
  ] },
];

module.exports = { meta, blocks };
