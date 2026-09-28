"""Step 8：专题分析 —— 差评在降、品质客诉在升：品控瓶颈定位与治理测算。

输出
  outputs/figures/*.png          报告 / PPT 用图
  outputs/analysis_results.json  报告与 PPT 引用的全部数字（单一数据源，避免手抄出错）
  outputs/analysis_tables.xlsx   各分析的明细表（面试时可以现场翻）

分析框架（假设驱动）
  H0 大盘：差评率与品质客诉率走势是否一致？差评结构怎么变？
  H1 上升归因：品质客诉率上升是"结构变化"还是"同类恶化"？（因素分解）
  H2 订单结构：多件 / 多商家订单是否更容易出品质问题？
  H3 商家：品质客诉是否集中在少数商家？
  H4 品类 / 商品：哪些品类高风险？商品信息完整度是否相关？
  H5 证伪：新商家更差？晚到导致更多损坏？首单为品质客诉订单影响复购？
  H6 治理测算：三项举措能把品质客诉率降到多少？
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, PercentFormatter

from common import FIG_DIR, OUT_DIR, query

# ---------------------------------------------------------------- 图表样式（统一在 viz_style.py）
from viz_style import (AMBER, AXIS, CRIT, DARK, FAKE, GRAY, INK, INK2, MUTED, PCT, PCT1, PINK, PINK2, QC, SHARE,  # noqa: E402
                       SURFACE, WARN, month_labels, plt, save)


def f(df):
    """MySQL DECIMAL → float"""
    for c in df.columns:
        if df[c].dtype == object:
            try:
                df[c] = pd.to_numeric(df[c])
            except (ValueError, TypeError):
                pass
    return df


R = {}          # 结论数字
TABLES = {}     # 明细表

# ================================================================ H0 大盘
kpi = f(query("SELECT * FROM ads_qc_kpi_month ORDER BY purchase_month"))
TABLES["月度KPI"] = kpi
tot = f(query("""
    SELECT COUNT(*) orders, SUM(is_delivered) delivered, SUM(is_delivered*is_quality_complaint) qc,
           SUM(is_delivered*is_quality_complaint)/SUM(is_delivered) qc_rate,
           SUM(is_bad)/SUM(has_review) bad_rate, AVG(review_score) avg_score, SUM(gmv) gmv,
           COUNT(DISTINCT main_seller_id) sellers, COUNT(DISTINCT customer_unique_id) customers
    FROM dwd_qc_order WHERE in_scope = 1""")).iloc[0]
R["overview"] = {k: float(v) for k, v in tot.items()}

period = f(query("""
    SELECT CASE WHEN purchase_month <= '2017-06' THEN '2017H1'
                WHEN purchase_month <= '2017-12' THEN '2017H2' ELSE '2018M1-8' END p,
           SUM(is_delivered*is_quality_complaint)/SUM(is_delivered) qc_rate,
           SUM(is_bad)/SUM(has_review) bad_rate,
           SUM(is_bad*is_quality_complaint)/SUM(is_bad) bad_quality_share,
           SUM(is_bad*is_fulfill_complaint)/SUM(is_bad) bad_fulfill_share,
           1 - SUM(is_delivered*is_late)/SUM(is_delivered) on_time_rate
    FROM dwd_qc_order WHERE in_scope = 1 GROUP BY 1 ORDER BY 1"""))
TABLES["半年度对比"] = period
R["period"] = period.set_index("p").to_dict(orient="index")

# 差评中品质原因占比（按月）
badmix_m = f(query("""
    SELECT purchase_month,
           SUM(is_bad*is_quality_complaint)/SUM(is_bad) bad_quality_share,
           SUM(is_bad*is_fulfill_complaint)/SUM(is_bad) bad_fulfill_share
    FROM dwd_qc_order WHERE in_scope = 1 GROUP BY 1 ORDER BY 1"""))
kpi = kpi.merge(badmix_m, on="purchase_month")
r18 = kpi[kpi.purchase_month.between("2018-04", "2018-08")]
R["bad_quality_share_2018M4_8"] = float((r18.bad_quality_share * 1).mean())
R["bad_rate_2018M3"] = float(kpi.set_index("purchase_month").loc["2018-03", "bad_rate"])
R["bad_rate_2018M8"] = float(kpi.set_index("purchase_month").loc["2018-08", "bad_rate"])
R["on_time_2018M3"] = float(kpi.set_index("purchase_month").loc["2018-03", "on_time_rate"])

# 图1：小多图 —— 差评率 / 准时签收率 / 品质客诉率（三个量纲，不用双轴）
x = np.arange(len(kpi))
labels = month_labels(list(kpi.purchase_month))
qc2017 = float(query("""SELECT SUM(is_delivered*is_quality_complaint)/SUM(is_delivered) FROM dwd_qc_order
                        WHERE in_scope = 1 AND purchase_month <= '2017-12'""").iloc[0, 0])
fig, axes = plt.subplots(3, 1, figsize=(10, 7.4), sharex=True, gridspec_kw={"hspace": 0.5})
for ax, col, title, color, fmt, lab in [
    (axes[0], "bad_rate", "差评率（最后一次评价为 1-2 星的订单数 ÷ 有评价的订单数）", GRAY, PCT, SHARE),
    (axes[1], "on_time_rate", "准时签收率（签收日期不晚于承诺送达日期的签收订单数 ÷ 签收订单数）", GRAY, PCT, SHARE),
    (axes[2], "qc_rate", "品质客诉率（品质客诉订单数 ÷ 签收订单数）", PINK, PCT1, QC),
]:
    y = kpi[col].astype(float).values
    ax.plot(x, y, color=color if col != "qc_rate" else PINK, lw=2, solid_capstyle="round")
    ax.scatter([x[-1]], [y[-1]], s=40, color=color if col != "qc_rate" else PINK, zorder=3,
               edgecolor=SURFACE, linewidth=2)
    ax.set_title(title, fontsize=11)
    ax.yaxis.set_major_formatter(fmt)
    ax.text(x[-1] + 0.3, y[-1], lab(y[-1]), va="center", fontsize=10, color=INK)
    ax.set_xlim(-0.5, len(x) - 0.2)
    ax.grid(axis="x", visible=False)
    ax.tick_params(axis="x", length=0)
for ax in axes[:2]:
    for line in ax.get_lines():
        line.set_color(MUTED)
    for c in ax.collections:
        c.set_color(MUTED)
i3 = list(kpi.purchase_month).index("2018-03")
axes[0].annotate(f"2018-03：差评率 {SHARE(kpi.bad_rate.iloc[i3])}", xy=(i3, kpi.bad_rate.iloc[i3]), xytext=(8.6, 0.21),
                 fontsize=9, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
axes[1].annotate(f"2018-03：准时签收率 {SHARE(kpi.on_time_rate.iloc[i3])}", xy=(i3, kpi.on_time_rate.iloc[i3]),
                 xytext=(8.2, 0.83), fontsize=9, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
axes[2].axhline(qc2017, color=AXIS, lw=1)
axes[2].text(12.2, qc2017 - 0.0010, f"2017 年品质客诉率 {QC(qc2017)}", fontsize=9, color=MUTED, va="top")
axes[2].set_xticks(x, labels, fontsize=9)
save(fig, "fig01_trend_small_multiples")

# 图2：差评原因结构（按季度，100% 堆叠）
badmix_q = f(query("""
    SELECT CONCAT(YEAR(purchase_ts), 'Q', QUARTER(purchase_ts)) q,
           SUM(CASE WHEN complaint_group = '品质问题' THEN 1 ELSE 0 END) quality,
           SUM(CASE WHEN complaint_group = '履约服务' THEN 1 ELSE 0 END) fulfill,
           SUM(CASE WHEN complaint_type = '未命中标签差评' THEN 1 ELSE 0 END) other,
           SUM(CASE WHEN complaint_type = '无文字差评' THEN 1 ELSE 0 END) notext
    FROM dwd_qc_order WHERE in_scope = 1 AND review_score <= 2
    GROUP BY 1 ORDER BY 1"""))
TABLES["差评原因结构_季度"] = badmix_q
parts = [("quality", "主标签为品质问题标签", PINK), ("fulfill", "主标签为履约服务标签", DARK),
         ("other", "有文字、未命中标签", AMBER), ("notext", "无文字", GRAY)]
share = badmix_q[[p[0] for p in parts]].div(badmix_q[[p[0] for p in parts]].sum(axis=1), axis=0)
fig, ax = plt.subplots(figsize=(10, 4.2))
left = np.zeros(len(share))
xq = np.arange(len(share))
for key, name, color in parts:
    ax.bar(xq, share[key], bottom=left, width=0.55, color=color, label=name, edgecolor=SURFACE, linewidth=2)
    if key == "quality":
        for i, v in enumerate(share[key]):
            ax.text(i, v / 2, SHARE(v), ha="center", va="center", color="white", fontsize=10, fontweight="bold")
    left += share[key].values
qlabels = list(badmix_q.q)
qlabels[-1] = qlabels[-1] + "\n（7、8 月）"
ax.set_xticks(xq, qlabels)
ax.yaxis.set_major_formatter(PCT)
ax.set_ylim(0, 1)
ax.set_title("差评订单按主标签分类（按下单季度；差评 = 最后一次评价为 1-2 星）", fontsize=11, pad=30)
ax.legend(ncol=4, loc="upper left", bbox_to_anchor=(0, 1.1))
ax.grid(axis="x", visible=False)
save(fig, "fig02_bad_review_reason_mix")
R["bad_quality_share_by_quarter"] = dict(zip(badmix_q.q, share["quality"].round(4)))

# ================================================================ H1 上升归因
typ = f(query("""
    SELECT CASE WHEN purchase_month <= '2017-12' THEN '2017' ELSE '2018M1-8' END p,
           SUM(is_delivered) d,
           SUM(is_delivered*qc_missing)/SUM(is_delivered)  missing,
           SUM(is_delivered*qc_defect)/SUM(is_delivered)   defect,
           SUM(is_delivered*qc_mismatch)/SUM(is_delivered) mismatch,
           SUM(is_delivered*qc_fake)/SUM(is_delivered)     fake,
           SUM(is_delivered*qc_package)/SUM(is_delivered)  package,
           SUM(is_delivered*is_quality_complaint)/SUM(is_delivered) qc
    FROM dwd_qc_order WHERE in_scope = 1 GROUP BY 1 ORDER BY 1"""))
TABLES["结果指标_年度"] = typ
R["type_by_year"] = typ.set_index("p").drop(columns="d").to_dict(orient="index")


def decompose(dim_sql: str):
    d = f(query(f"""
        SELECT CASE WHEN purchase_month <= '2017-12' THEN 'A' ELSE 'B' END p, {dim_sql} seg,
               SUM(is_delivered) n, SUM(is_delivered*is_quality_complaint) qc
        FROM dwd_qc_order WHERE in_scope = 1 GROUP BY 1, 2"""))
    pv = d.pivot(index="seg", columns="p", values=["n", "qc"]).fillna(0)
    wA, wB = pv["n"]["A"] / pv["n"]["A"].sum(), pv["n"]["B"] / pv["n"]["B"].sum()
    rA = (pv["qc"]["A"] / pv["n"]["A"]).fillna(0)
    rB = (pv["qc"]["B"] / pv["n"]["B"]).fillna(0)
    out = {
        "rate_A": float((wA * rA).sum()), "rate_B": float((wB * rB).sum()),
        "mix_effect": float(((wB - wA) * rA).sum()),
        "within_effect": float((wA * (rB - rA)).sum()),
        "interaction": float(((wB - wA) * (rB - rA)).sum()),
    }
    seg = pd.DataFrame({"权重2017": wA, "权重2018": wB, "品质客诉率2017": rA, "品质客诉率2018": rB,
                        "组内贡献": wA * (rB - rA)}).sort_values("组内贡献", ascending=False)
    return out, seg


R["decomp_order_type"], seg_ot = decompose("CASE WHEN item_cnt = 1 THEN '单件' ELSE '多件' END")
R["decomp_category"], seg_cat = decompose("COALESCE(main_category_l1, '未知')")
TABLES["因素分解_一级类目"] = seg_cat.reset_index()
TABLES["因素分解_单多件"] = seg_ot.reset_index()
R["decomp_category_top"] = {k: float(v) for k, v in seg_cat["组内贡献"].head(4).items()}

# 图3：5 个结果指标，2017 年 vs 2018 年 1-8 月
fig, ax = plt.subplots(figsize=(10, 4))
names = [("missing", "少件漏发客诉率"), ("defect", "质量缺陷客诉率"), ("mismatch", "货不对板客诉率"), ("fake", "假货客诉率"), ("package", "包装破损客诉率")]
xi = np.arange(len(names))
a = typ.set_index("p").loc["2017"]
b = typ.set_index("p").loc["2018M1-8"]
ax.bar(xi - 0.15, [a[k] for k, _ in names], width=0.28, color=GRAY, label="2017 年")
ax.bar(xi + 0.15, [b[k] for k, _ in names], width=0.28, color=PINK, label="2018 年 1-8 月")
for i, (k, _) in enumerate(names):
    lab = (lambda v: f"{v * 1e4:.1f}") if k == "fake" else QC   # 假货客诉率用"单/万单"
    ax.text(i - 0.15, a[k] + 0.0004, lab(a[k]), ha="center", va="bottom", fontsize=8.5, color=MUTED)
    ax.text(i + 0.15, b[k] + 0.0004, lab(b[k]), ha="center", va="bottom", fontsize=8.5, color=INK)
ax.set_xticks(xi, [n + ("\n（数据标签单位：单/万单）" if k == "fake" else "") for k, n in names])
ax.yaxis.set_major_formatter(PCT1)
ax.set_ylim(0, max(max(b[k] for k, _ in names), max(a[k] for k, _ in names)) * 1.3)
ax.set_title("5 个结果指标（命中该标签的品质客诉订单数 ÷ 签收订单数）", fontsize=11)
ax.legend(loc="upper right")
ax.grid(axis="x", visible=False)
save(fig, "fig03_type_yoy")

# ================================================================ H2 订单结构
ot = f(query("""
    SELECT CASE WHEN item_cnt = 1 THEN '1 单件' WHEN seller_cnt > 1 THEN '4 多商家'
                WHEN sku_cnt > 1 THEN '3 单商家多SKU' ELSE '2 同SKU多件' END t,
           COUNT(*) n, AVG(is_quality_complaint) qc, AVG(qc_missing) missing,
           AVG(is_quality_complaint) - AVG(CASE WHEN qc_missing = 1 THEN 1 ELSE 0 END * is_quality_complaint) qc_ex_missing,
           SUM(is_bad)/SUM(has_review) bad_rate
    FROM dwd_qc_order WHERE in_scope = 1 AND is_delivered = 1 GROUP BY 1 ORDER BY 1"""))
ot["order_share"] = ot.n / ot.n.sum()
TABLES["订单结构"] = ot
share_multi = f(query("""
    SELECT SUM(item_cnt > 1)/COUNT(*) order_share,
           SUM((item_cnt > 1) * is_quality_complaint)/SUM(is_quality_complaint) qc_share,
           SUM((item_cnt > 1) * qc_missing)/SUM(qc_missing) missing_share,
           AVG(CASE WHEN item_cnt > 1 THEN is_quality_complaint END) multi_qc,
           AVG(CASE WHEN item_cnt = 1 THEN is_quality_complaint END) single_qc,
           SUM(CASE WHEN item_cnt > 1 AND qc_missing = 1 AND review_date >= DATE(delivered_ts) THEN 1 ELSE 0 END)
             / SUM(CASE WHEN item_cnt > 1 AND qc_missing = 1 THEN 1 ELSE 0 END) review_after_delivered
    FROM dwd_qc_order WHERE in_scope = 1 AND is_delivered = 1""")).iloc[0]
R["multi_item"] = {k: float(v) for k, v in share_multi.items()}
R["order_type"] = ot.set_index("t")[["n", "qc", "missing", "bad_rate", "order_share"]].to_dict(orient="index")

fig, ax = plt.subplots(figsize=(10, 3.8))
yi = np.arange(len(ot))[::-1]
miss = ot.missing.values
rest = ot.qc.values - ot.missing.values
rest = np.clip(rest, 0, None)
ax.barh(yi, miss, height=0.5, color=DARK, label="命中少件漏发标签", edgecolor=SURFACE, linewidth=2)
ax.barh(yi, rest, left=miss, height=0.5, color=PINK, label="未命中少件漏发标签", edgecolor=SURFACE, linewidth=2)
for i, (q_, n_, s_) in enumerate(zip(ot.qc, ot.n, ot.order_share)):
    ax.text(q_ + 0.004, yi[i], f"{QC(q_)}   （{int(n_):,} 单，占签收订单 {SHARE(s_)}）", va="center", fontsize=10)
ax.set_yticks(yi, [{"单件": "单件订单", "同SKU多件": "同 SKU 多件", "单商家多SKU": "单商家多 SKU", "多商家": "多商家"}[t[2:]]
                   for t in ot.t])
ax.xaxis.set_major_formatter(PCT)
ax.set_xlim(0, ot.qc.max() * 1.75)
ax.set_title("品质客诉率 × 订单结构（下单月 2017-01 至 2018-08 的签收订单）", fontsize=11, pad=26)
ax.legend(ncol=2, loc="upper left", bbox_to_anchor=(0, 1.12))
ax.grid(axis="y", visible=False)
save(fig, "fig04_order_structure")

# ================================================================ H3 商家
sc = f(query("SELECT * FROM ads_seller_scorecard"))
TABLES["商家品质分_近6月"] = sc.sort_values("quality_score")
tier = sc.groupby("risk_level").agg(sellers=("seller_id", "count"), delivered=("delivered_cnt", "sum"),
                                    qc=("qc_cnt", "sum"), gmv=("gmv", "sum"))
tier = tier.reindex(["正常", "需关注", "高风险"])
tier_share = tier.div(tier.sum())
tier["qc_rate"] = tier.qc / tier.delivered
R["seller_tier"] = tier.to_dict(orient="index")
R["seller_tier_share"] = tier_share.to_dict(orient="index")
R["seller_benchmark_qc_rate"] = float(sc.benchmark_qc_rate.iloc[0])
R["seller_eligible"] = int(len(sc))
R["seller_eligible_order_cover"] = float(query("""
    SELECT (SELECT SUM(delivered_cnt) FROM ads_seller_scorecard) / SUM(delivered_cnt) FROM dws_seller_month
    WHERE purchase_month BETWEEN '2018-03' AND '2018-08'""").iloc[0, 0])

fig, ax = plt.subplots(figsize=(10, 3.4))
cols = [("sellers", "商家数"), ("delivered", "商家签收订单数"), ("qc", "商家品质客诉订单数")]
tcolors = {"正常": GRAY, "需关注": WARN, "高风险": CRIT}
yi = np.arange(len(cols))[::-1]
for j, (c, name) in enumerate(cols):
    left = 0
    for t in ["正常", "需关注", "高风险"]:
        v = tier_share.loc[t, c]
        ax.barh(yi[j], v, left=left, height=0.52, color=tcolors[t], edgecolor=SURFACE, linewidth=2,
                label=t + "商家" if j == 0 else None)
        if t != "高风险":
            ax.text(left + v / 2, yi[j], SHARE(v), ha="center", va="center", fontsize=10,
                    color=INK, fontweight="bold")
        left += v
    ax.text(1.015, yi[j], f"高风险商家 {SHARE(tier_share.loc['高风险', c])}", va="center", fontsize=10, color=INK)
ax.set_yticks(yi, [n for _, n in cols])
ax.xaxis.set_major_formatter(PCT)
ax.set_xlim(0, 1.2)
ax.set_xticks([0, .2, .4, .6, .8, 1])
ax.set_title(f"商家分层：{len(sc)} 家参评商家的构成（商家评估窗口：下单月 2018-03 至 2018-08）", fontsize=11)
ax.legend(ncol=3, loc="upper left", bbox_to_anchor=(0, -0.12))
ax.grid(axis="y", visible=False)
save(fig, "fig05_seller_tier")

# 帕累托：按平滑品质客诉率从高到低排序商家，累计商家签收订单占比 vs 累计商家品质客诉订单占比
sc_sorted = sc.sort_values(["qc_rate_smooth", "seller_id"], ascending=[False, True], kind="mergesort").reset_index(drop=True)   # 同分按商家 ID，结果不随行序变化
sc_sorted["cum_orders"] = sc_sorted.delivered_cnt.cumsum() / sc_sorted.delivered_cnt.sum()
sc_sorted["cum_qc"] = sc_sorted.qc_cnt.cumsum() / sc_sorted.qc_cnt.sum()
k10 = (sc_sorted.cum_orders <= 0.10).sum()
R["pareto_top10pct_orders_qc_share"] = float(sc_sorted.cum_qc.iloc[k10 - 1])
R["pareto_top10pct_orders_sellers"] = int(k10)

# ================================================================ H4 品类 / 商品
cat = f(query("SELECT * FROM ads_category_quality"))
TABLES["品类品质排行"] = cat.sort_values("qc_rate", ascending=False)
p_rate = float(R["overview"]["qc_rate"])
fig, ax = plt.subplots(figsize=(10, 5.2))
hi = cat.qc_rate >= 1.2 * p_rate
ax.scatter(cat.delivered_cnt[~hi], cat.qc_rate[~hi], s=46, color=GRAY, edgecolor=SURFACE, linewidth=2, zorder=3)
ax.scatter(cat.delivered_cnt[hi], cat.qc_rate[hi], s=56, color=DARK, edgecolor=SURFACE, linewidth=2, zorder=3)
ax.axhline(p_rate, color=AXIS, lw=1)
ax.text(cat.delivered_cnt.min() * 0.95, p_rate + 0.0012, f"全部签收订单 {QC(p_rate)}", va="bottom", fontsize=9, color=MUTED)
# 标注：全部黑色点 + 体量最大的几个品类（偏移量手工调过，避免重叠）
offsets = {"办公家具": (8, 0, "left"), "家装建材": (8, 0, "left"), "未知品类": (8, 0, "left"),
           "居家舒适": (0, 11, "center"), "影音设备": (0, -12, "center"), "客厅家具": (8, 2, "left"),
           "家用电器": (8, 0, "left"), "手机通讯": (0, 11, "center"), "家具软装": (-8, -1, "right"),
           "电脑配件": (8, 8, "left"), "床品布艺卫浴": (-6, -12, "right"), "运动休闲": (-8, 10, "right"),
           "美妆健康": (-8, -11, "right")}
for _, r_ in cat[cat.category_cn.isin(offsets)].iterrows():
    dx, dy, ha = offsets[r_.category_cn]
    ax.annotate(f"{r_.category_cn} {QC(r_.qc_rate)}", (r_.delivered_cnt, r_.qc_rate), xytext=(dx, dy),
                textcoords="offset points", fontsize=9, color=INK2, va="center", ha=ha)
ax.set_xscale("log")
ax.set_xlim(240, 12500)
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v):,}"))
ax.yaxis.set_major_formatter(PCT)
ax.set_xlabel("主品类的签收订单数（对数轴）")
ax.set_title("品类体量 × 品质客诉率（下单月 2017-01 至 2018-08，签收订单 ≥ 300 的主品类；\n"
             "黑点 = 品质客诉率 ≥ 全部签收订单的 1.2 倍）", fontsize=11)
save(fig, "fig06_category_scatter")
R["category_top"] = cat.sort_values("qc_rate", ascending=False).head(6)[
    ["category_cn", "delivered_cnt", "qc_rate", "defect_rate", "mismatch_rate", "missing_rate", "qc_share"]
].to_dict(orient="records")

# 大件 / 办公家具
heavy = f(query("""
    SELECT CASE WHEN i.product_weight_g < 1000 THEN '1 <1kg' WHEN i.product_weight_g < 5000 THEN '2 1-5kg'
                WHEN i.product_weight_g < 15000 THEN '3 5-15kg' ELSE '4 ≥15kg' END w,
           COUNT(*) n, AVG(q.is_quality_complaint) qc, AVG(q.qc_missing) missing, AVG(q.qc_defect) defect
    FROM dwd_qc_order q JOIN dwd_order_item i ON i.order_id = q.order_id
    WHERE q.in_scope = 1 AND q.is_delivered = 1 AND q.item_cnt = 1 AND i.product_weight_g IS NOT NULL
    GROUP BY 1 ORDER BY 1"""))
TABLES["单件订单_重量段"] = heavy
R["heavy"] = heavy.set_index("w").to_dict(orient="index")

# 商品信息完整度（单件订单，排除订单结构干扰）
info = f(query("""
    SELECT CASE WHEN i.product_photos_qty IS NULL THEN '0 信息缺失' WHEN i.product_photos_qty = 1 THEN '1 1张图'
                WHEN i.product_photos_qty <= 3 THEN '2 2-3张' ELSE '3 4张+' END g,
           COUNT(*) n, AVG(q.is_quality_complaint) qc, AVG(q.qc_mismatch) mismatch, AVG(q.qc_fake) fake
    FROM dwd_qc_order q JOIN dwd_order_item i ON i.order_id = q.order_id
    WHERE q.in_scope = 1 AND q.is_delivered = 1 AND q.item_cnt = 1 GROUP BY 1 ORDER BY 1"""))
TABLES["单件订单_商品图片数"] = info
R["info"] = info.set_index("g").to_dict(orient="index")

fake_cat = f(query("""
    SELECT main_category_cn, COUNT(*) n, SUM(qc_fake) fake, AVG(qc_fake) fake_rate
    FROM dwd_qc_order WHERE in_scope = 1 AND is_delivered = 1
    GROUP BY 1 HAVING n >= 300 ORDER BY fake_rate DESC LIMIT 6"""))
TABLES["假货客诉率_品类TOP"] = fake_cat
R["fake_top"] = fake_cat.to_dict(orient="records")
R["fake_platform"] = float(query("SELECT AVG(qc_fake) FROM dwd_qc_order WHERE in_scope=1 AND is_delivered=1").iloc[0, 0])

# ================================================================ H5 证伪
tenure = f(query("""
    WITH first_sale AS (
        SELECT os.seller_id, MIN(o.purchase_ts) first_ts
        FROM dwd_order_seller os JOIN dwd_order o ON os.order_id = o.order_id GROUP BY os.seller_id)
    SELECT CASE WHEN DATEDIFF(q.purchase_ts, fs.first_ts) < 90 THEN '1 入驻<3个月'
                WHEN DATEDIFF(q.purchase_ts, fs.first_ts) < 180 THEN '2 3-6个月'
                WHEN DATEDIFF(q.purchase_ts, fs.first_ts) < 365 THEN '3 6-12个月' ELSE '4 12个月以上' END g,
           COUNT(*) n, SUM(q.is_delivered*q.is_quality_complaint)/SUM(q.is_delivered) qc
    FROM dwd_order_seller os JOIN dwd_qc_order q ON os.order_id = q.order_id
    JOIN first_sale fs ON os.seller_id = fs.seller_id
    WHERE q.in_scope = 1 AND q.purchase_ts >= '2017-07-01' GROUP BY 1 ORDER BY 1"""))
late = f(query("""
    SELECT is_late, COUNT(*) n, AVG(is_quality_complaint) qc, AVG(qc_defect) defect, AVG(qc_package) package,
           SUM(is_bad)/SUM(has_review) bad_rate
    FROM dwd_qc_order WHERE in_scope = 1 AND is_delivered = 1 GROUP BY 1"""))
repurchase = f(query("""
    WITH c AS (
        SELECT customer_unique_id, is_quality_complaint, is_bad, review_score, has_review, is_delivered, purchase_ts,
               ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY purchase_ts) rn,
               COUNT(*)     OVER (PARTITION BY customer_unique_id) n_orders
        FROM dwd_qc_order WHERE in_scope = 1)
    SELECT CASE WHEN is_quality_complaint = 1 THEN '1 首单品质客诉' WHEN is_bad = 1 THEN '2 首单差评（非品质）'
                WHEN review_score = 5 THEN '4 首单5星' ELSE '3 首单3-4星' END g,
           COUNT(*) customers, AVG(n_orders > 1) repurchase_rate
    FROM c WHERE rn = 1 AND is_delivered = 1 AND has_review = 1 AND purchase_ts < '2018-03-01'
    GROUP BY 1 ORDER BY 1"""))
TABLES["证伪_商家入驻时长"] = tenure
TABLES["证伪_是否延迟签收"] = late
TABLES["证伪_首单体验与复购"] = repurchase
R["falsify"] = {
    "tenure": tenure.set_index("g")["qc"].to_dict(),
    "late": late.set_index("is_late")[["qc", "defect", "package", "bad_rate"]].to_dict(orient="index"),
    "repurchase": repurchase.set_index("g")[["customers", "repurchase_rate"]].to_dict(orient="index"),
}

# ================================================================ H6 治理测算
# 以 2018 年 1-8 月签收订单为基期，每个品质客诉订单按其命中的举措计算"被避免的概率"，
# 多个举措叠加时 p = 1 - Π(1 - p_i)，避免重复计算。
base = f(query("""
    SELECT q.order_id, q.item_cnt, q.qc_missing, q.qc_fake, q.qc_mismatch, q.main_category_l1,
           q.is_quality_complaint, s.risk_level
    FROM dwd_qc_order q LEFT JOIN ads_seller_scorecard s ON q.main_seller_id = s.seller_id
    WHERE q.in_scope = 1 AND q.is_delivered = 1 AND q.purchase_month >= '2018-01'"""))
N = len(base)
qc = base[base.is_quality_complaint == 1].copy()
ACTIONS = [
    ("A", "多件订单出库复核 + 分包裹提醒", "多件订单中命中少件漏发标签的品质客诉订单减少 50%",
     lambda d: ((d.item_cnt > 1) & (d.qc_missing == 1)) * 0.5),
    ("B", "高风险商家和需关注商家整改", "主商家为高风险商家或需关注商家的品质客诉订单减少 30%",
     lambda d: d.risk_level.isin(["高风险", "需关注"]) * 0.3),
    ("C", "3C数码、钟表与潮流好物正品与商品描述专项", "主品类属于一级类目 3C数码、钟表与潮流好物且命中假货或货不对板标签的品质客诉订单减少 30%",
     lambda d: (d.main_category_l1.isin(["3C数码", "钟表与潮流好物"]) & ((d.qc_fake == 1) | (d.qc_mismatch == 1))) * 0.3),
]
survive = np.ones(len(qc))
steps = []
rate0 = len(qc) / N
prev = rate0
for code, name, assumption, fn in ACTIONS:
    survive = survive * (1 - fn(qc).astype(float).values)
    cur = survive.sum() / N
    steps.append({"code": code, "name": name, "assumption": assumption, "delta_pp": prev - cur, "rate_after": cur})
    prev = cur
R["sizing"] = {"baseline_rate": rate0, "baseline_orders": N, "steps": steps, "target_rate": prev}
TABLES["治理测算"] = pd.DataFrame(steps)

fig, ax = plt.subplots(figsize=(10, 4))
xs = np.arange(len(steps) + 2)
ax.bar(0, rate0, width=0.5, color=PINK)
ax.text(0, rate0 + 0.0008, QC(rate0), ha="center", fontsize=10)
level = rate0
for i, s in enumerate(steps, start=1):
    ax.bar(i, s["delta_pp"], bottom=level - s["delta_pp"], width=0.5, color=PINK2)
    ax.text(i, level + 0.0008, f"−{s['delta_pp'] * 100:.2f}pp", ha="center", fontsize=10)
    level -= s["delta_pp"]
ax.bar(len(steps) + 1, level, width=0.5, color=PINK)
ax.text(len(steps) + 1, level + 0.0008, QC(level), ha="center", fontsize=10, fontweight="bold")
short = {"A": "举措 A\n多件订单\n出库复核", "B": "举措 B\n高风险商家、\n需关注商家整改", "C": "举措 C\n3C数码、钟表与潮流好物\n正品与商品描述专项"}
ax.set_xticks(xs, ["基期\n2018 年 1-8 月"] + [short[s["code"]] for s in steps] + ["中性情景\n治理后"], fontsize=9.5)
ax.yaxis.set_major_formatter(PCT1)
ax.set_ylim(0, rate0 * 1.2)
ax.set_title("治理测算：中性情景下的品质客诉率（举措 A 降幅 50%、B 30%、C 30%）", fontsize=11)
ax.grid(axis="x", visible=False)
save(fig, "fig07_sizing_waterfall")

# ---------------------------------------------------------------- 输出
def to_py(o):
    if isinstance(o, dict):
        return {str(k): to_py(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_py(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return round(float(o), 6)
    return o


(OUT_DIR / "analysis_results.json").write_text(json.dumps(to_py(R), ensure_ascii=False, indent=2), encoding="utf-8")
with pd.ExcelWriter(OUT_DIR / "analysis_tables.xlsx") as xw:
    for name, df in TABLES.items():
        df.to_excel(xw, sheet_name=name[:31], index=False)
print("  → outputs/analysis_results.json, outputs/analysis_tables.xlsx")
