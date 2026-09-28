"""Step 13：进阶分析 —— 统计严谨度与唯品会视角。

  A. 统计过程控制：p 控制图（2017 年为阶段Ⅰ基线，2018 年为阶段Ⅱ监控）+ 判异准则
  B. 显著性：两比例 z 检验；商家 Wilson 置信区间，与贝叶斯平滑互相印证
  C. 唯品会视角：穿戴类（唯品会 GMV 占比 75%）的品质表现，按唯品会品类结构重加权
  D. 差异化抽检：样本外测算（用前 6 个月打分，后 6 个月检验）同样抽检量能多拦截多少问题
  E. 商家风险模型回测：3 个时间窗口，检验"高风险"标签下一期是否仍然高风险
  F. 治理测算三档情景 + 单因素敏感性
输出：outputs/advanced_results.json、outputs/advanced_tables.xlsx、fig08 ~ fig12
"""
import json

import numpy as np
import pandas as pd
from scipy import stats

from common import OUT_DIR, query
from viz_style import AXIS, BLUE, CRIT, GRAY, INK, INK2, MUTED, ORANGE, PCT, PCT1, SURFACE, WARN, plt, save

R, T = {}, {}


def num(df):
    for c in df.columns:
        if df[c].dtype == object:
            try:
                df[c] = pd.to_numeric(df[c])
            except (ValueError, TypeError):
                pass
    return df


def ztest(x1, n1, x2, n2):
    p = (x1 + x2) / (n1 + n2)
    z = (x2 / n2 - x1 / n1) / np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return float(z), float(2 * (1 - stats.norm.cdf(abs(z))))


def wilson(x, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = x / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


# ======================================================================== A. p 控制图
k = num(query("SELECT purchase_month m, delivered_cnt n, qc_cnt x FROM ads_qc_kpi_month ORDER BY 1"))
base = k[k.m <= "2017-12"]
p0 = base.x.sum() / base.n.sum()
k["p"] = k.x / k.n
k["sigma"] = np.sqrt(p0 * (1 - p0) / k.n)
k["ucl"], k["lcl"] = p0 + 3 * k.sigma, p0 - 3 * k.sigma
k["beyond"] = np.where(k.p > k.ucl, "上限外", np.where(k.p < k.lcl, "下限外", ""))
# 判异准则 2（Nelson）：连续 9 点落在中心线同一侧
side = np.sign(k.p - p0)
run, runs = 0, []
for i, sgn in enumerate(side):
    run = run + 1 if i and sgn == side.iloc[i - 1] and sgn != 0 else 1
    runs.append(run)
k["run_same_side"] = runs
first_run9 = k[(k.run_same_side >= 9) & (side > 0)].m.min()
run_start_idx = int(k[k.m == first_run9].index[0]) - 8 if isinstance(first_run9, str) else None
T["p控制图"] = k
phase1_in = bool((base.p.between(k.lcl[:len(base)], k.ucl[:len(base)])).all()) if "p" in base else None
R["spc"] = {
    "p0": p0, "phase1_all_in_control": bool(k[k.m <= "2017-12"].beyond.eq("").all()),
    "beyond_ucl_months": k[k.beyond == "上限外"].m.tolist(),
    "run9_signal_month": first_run9, "run_start_month": k.m.iloc[run_start_idx] if run_start_idx is not None else None,
    "max_run_above": int(k[side > 0].run_same_side.max()),
}

fig, ax = plt.subplots(figsize=(10, 4.4))
x = np.arange(len(k))
ax.fill_between(x, k.lcl, k.ucl, step="mid", color=BLUE, alpha=0.06, linewidth=0)
ax.step(x, k.ucl, where="mid", color=AXIS, lw=1)
ax.step(x, k.lcl, where="mid", color=AXIS, lw=1)
ax.hlines(p0, -0.5, len(k) - 0.5, color=INK2, lw=1)
ax.plot(x, k.p, color=BLUE, lw=2, zorder=3)
ax.scatter(x, k.p, s=30, color=BLUE, edgecolor=SURFACE, linewidth=1.5, zorder=4)
out = k.beyond == "上限外"
ax.scatter(x[out], k.p[out], s=60, color=CRIT, edgecolor=SURFACE, linewidth=2, zorder=5, label="越出上控制限")
ax.axvline(11.5, color=AXIS, lw=1)
ax.text(0.2, 0.0195, "阶段Ⅰ：2017 年基线（12 个月全部受控）", fontsize=9, color=MUTED)
ax.text(11.8, 0.0195, "阶段Ⅱ：2018 年监控", fontsize=9, color=MUTED)
ax.text(len(k) - 0.4, p0, f"中心线 {p0:.2%}", fontsize=9, color=INK2, va="center")
ax.text(len(k) - 0.4, k.ucl.iloc[-1], "UCL", fontsize=9, color=MUTED, va="center")
ax.text(len(k) - 0.4, k.lcl.iloc[-1], "LCL", fontsize=9, color=MUTED, va="center")
rs = R["spc"]["run_start_month"]
if rs:
    i0 = int(k[k.m == rs].index[0])
    ax.annotate("", xy=(len(k) - 1, 0.0565), xytext=(i0, 0.0565), arrowprops=dict(arrowstyle="-", color=ORANGE, lw=2))
    ax.text((i0 + len(k) - 1) / 2, 0.0572, f"连续 {R['spc']['max_run_above']} 个月高于中心线（判异：≥9 点同侧）",
            fontsize=9, color=INK, ha="center")
ax.set_xticks(x, [m[2:].replace("-", ".") for m in k.m], fontsize=9)
ax.yaxis.set_major_formatter(PCT1)
ax.set_ylim(0.018, 0.062)
ax.set_xlim(-0.5, len(k) + 0.8)
ax.grid(axis="x", visible=False)
ax.legend(loc="lower right", bbox_to_anchor=(1, 0.06))
ax.set_title("品质客诉率 p 控制图（控制限随每月签收量变化，±3σ）")
save(fig, "fig08_p_chart")

# ======================================================================== B. 显著性
yr = num(query("""
    SELECT CASE WHEN purchase_month <= '2017-12' THEN '2017' ELSE '2018' END p,
           SUM(is_delivered) n, SUM(is_delivered * is_quality_complaint) x,
           SUM(is_delivered * qc_fake) xf, SUM(is_delivered * qc_mismatch) xm
    FROM dwd_qc_order WHERE in_scope = 1 GROUP BY 1 ORDER BY 1""")).set_index("p")
z, pv = ztest(yr.x["2017"], yr.n["2017"], yr.x["2018"], yr.n["2018"])
zf, pf = ztest(yr.xf["2017"], yr.n["2017"], yr.xf["2018"], yr.n["2018"])
zm, pm = ztest(yr.xm["2017"], yr.n["2017"], yr.xm["2018"], yr.n["2018"])
ci17 = wilson(yr.x["2017"], yr.n["2017"])
ci18 = wilson(yr.x["2018"], yr.n["2018"])
R["significance"] = {
    "qc": {"z": z, "p": pv, "ci2017": ci17, "ci2018": ci18},
    "fake": {"z": zf, "p": pf}, "mismatch": {"z": zm, "p": pm},
}

sc = num(query("SELECT * FROM ads_seller_scorecard"))
pr = float(sc.platform_qc_rate.iloc[0])
lo_hi = [wilson(x_, n_) for x_, n_ in zip(sc.qc_cnt, sc.delivered_cnt)]
sc["wilson_lo"], sc["wilson_hi"] = [a for a, _ in lo_hi], [b for _, b in lo_hi]
sc["sig_above"] = sc.wilson_lo > pr
raw2x = sc.qc_rate >= 2 * pr
R["seller_ci"] = {
    "high_risk_n": int((sc.risk_level == "高风险").sum()),
    "high_risk_sig": int(((sc.risk_level == "高风险") & sc.sig_above).sum()),
    "attention_sig": int(((sc.risk_level == "需关注") & sc.sig_above).sum()),
    "attention_n": int((sc.risk_level == "需关注").sum()),
    "raw2x_n": int(raw2x.sum()), "raw2x_not_sig": int((raw2x & ~sc.sig_above).sum()),
    "normal_sig": int(((sc.risk_level == "正常") & sc.sig_above).sum()),
}
T["商家Wilson区间"] = sc[["seller_id", "risk_level", "delivered_cnt", "qc_cnt", "qc_rate", "qc_rate_smooth", "wilson_lo", "wilson_hi", "sig_above"]] \
    .sort_values("qc_rate_smooth", ascending=False)

# ======================================================================== C. 唯品会视角：穿戴类
WEAR = "(main_category_l1 = '服饰鞋包' OR main_category_cn IN ('钟表礼品', '童装'))"
wear = num(query(f"""
    SELECT CASE WHEN {WEAR} THEN '穿戴类' ELSE '非穿戴' END g,
           CASE WHEN purchase_month <= '2017-12' THEN '2017' ELSE '2018' END p,
           COUNT(*) n, SUM(is_quality_complaint) x, SUM(qc_fake) xf, SUM(qc_mismatch) xm, SUM(qc_defect) xd, SUM(qc_missing) xmiss
    FROM dwd_qc_order WHERE in_scope = 1 AND is_delivered = 1 AND main_product_id IS NOT NULL
    GROUP BY 1, 2 ORDER BY 1, 2"""))
wear["qc"] = wear.x / wear.n
wear["fake10k"] = wear.xf / wear.n * 1e4
wear["mismatch"] = wear.xm / wear.n
wear["missing"] = wear.xmiss / wear.n
T["穿戴类对比"] = wear
w = wear.set_index(["g", "p"])
zw, pw = ztest(w.x[("穿戴类", "2017")], w.n[("穿戴类", "2017")], w.x[("穿戴类", "2018")], w.n[("穿戴类", "2018")])
tot = wear.groupby("g")[["n", "x", "xf", "xm", "xmiss"]].sum()
olist_share = float(tot.n["穿戴类"] / tot.n.sum())
r18 = {g: {k_: float(w.loc[(g, "2018"), k_]) for k_ in ["qc", "fake10k", "mismatch", "missing"]} for g in ["穿戴类", "非穿戴"]}
vip_mix = {k_: 0.75 * r18["穿戴类"][k_] + 0.25 * r18["非穿戴"][k_] for k_ in r18["穿戴类"]}
olist_mix = {k_: olist_share * r18["穿戴类"][k_] + (1 - olist_share) * r18["非穿戴"][k_] for k_ in r18["穿戴类"]}
apparel = num(query("""
    SELECT main_category_cn c, COUNT(*) n, SUM(is_quality_complaint) x, SUM(qc_mismatch) xm
    FROM dwd_qc_order WHERE in_scope = 1 AND is_delivered = 1 AND main_category_cn IN ('男装', '女装', '鞋靴', '内衣泳装', '运动服饰')
    GROUP BY 1"""))
apparel_tot = apparel[["n", "x", "xm"]].sum()
ap_ci = wilson(apparel_tot.xm, apparel_tot.n)
R["vip_view"] = {
    "olist_wear_share": olist_share, "vip_wear_share": 0.75,
    "wear": {p: {"n": int(w.n[("穿戴类", p)]), "qc": float(w.qc[("穿戴类", p)]), "fake10k": float(w.fake10k[("穿戴类", p)]),
                 "mismatch": float(w.mismatch[("穿戴类", p)])} for p in ["2017", "2018"]},
    "nonwear": {p: {"qc": float(w.qc[("非穿戴", p)]), "fake10k": float(w.fake10k[("非穿戴", p)])} for p in ["2017", "2018"]},
    "wear_z": zw, "wear_p": pw,
    "reweight_2018": {"olist_mix": olist_mix, "vip_mix": vip_mix},
    "apparel": {"n": int(apparel_tot.n), "mismatch": float(apparel_tot.xm / apparel_tot.n), "mismatch_ci": ap_ci,
                "qc": float(apparel_tot.x / apparel_tot.n)},
}

fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), gridspec_kw={"wspace": 0.3})
for ax, col, title, fmt in [(axes[0], "qc", "品质客诉率", PCT1), (axes[1], "fake10k", "假货投诉（每万单）", None)]:
    xi = np.arange(2)
    for j, (p, color) in enumerate([("2017", GRAY), ("2018", BLUE)]):
        vals = [float(w.loc[(g, p), col]) for g in ["穿戴类", "非穿戴"]]
        ax.bar(xi + (j - 0.5) * 0.3, vals, width=0.28, color=color, label=f"{p}{'' if p == '2017' else ' 年 1-8 月'}")
        for i_, v in enumerate(vals):
            ax.text(i_ + (j - 0.5) * 0.3, v * 1.02, f"{v:.1%}" if fmt else f"{v:.0f}", ha="center", va="bottom", fontsize=9, color=INK)
    ax.set_xticks(xi, [f"穿戴类\n（Olist 占 {olist_share:.0%}，唯品会占 75%）", "非穿戴"], fontsize=10)
    if fmt:
        ax.yaxis.set_major_formatter(fmt)
    ax.set_title(title)
    ax.grid(axis="x", visible=False)
fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.06))
save(fig, "fig09_wearables")

# ======================================================================== D. 差异化抽检（样本外）
d = num(query("""
    SELECT purchase_month m, main_seller_id s, main_category_cn c, item_cnt,
           CASE WHEN qc_defect + qc_mismatch + qc_fake > 0 THEN 1 ELSE 0 END y_in,
           qc_missing y_out
    FROM dwd_qc_order WHERE in_scope = 1 AND is_delivered = 1 AND main_seller_id IS NOT NULL"""))
tr = d[(d.m >= "2017-09") & (d.m <= "2018-02")]
te = d[(d.m >= "2018-03") & (d.m <= "2018-08")].copy()
pin = tr.y_in.mean()
s_ = tr.groupby("s").y_in.agg(["sum", "count"])
s_["sm"] = (s_["sum"] + 50 * pin) / (s_["count"] + 50)
c_ = tr.groupby("c").y_in.agg(["sum", "count"])
c_["sm"] = (c_["sum"] + 200 * pin) / (c_["count"] + 200)
te["r_seller"] = te.s.map(s_.sm).fillna(pin)
te["r_cat"] = te.c.map(c_.sm).fillna(pin)
te["r_both"] = te.r_seller * te.r_cat / pin
rng = np.random.default_rng(2026)
te["rand"] = rng.random(len(te))
te["multi"] = (te.item_cnt > 1).astype(int) + te.rand * 1e-6        # 多件订单优先，其余随机
Y_in, Y_out, N = te.y_in.sum(), te.y_out.sum(), len(te)


def gain(col, target):
    s = te.sort_values(col, ascending=False)[target].cumsum().values / te[target].sum()
    return np.concatenate([[0], s])


grid = np.linspace(0, 1, len(te) + 1)
curves = {"随机抽检": gain("rand", "y_in"), "商家风险分": gain("r_seller", "y_in"), "商家 × 品类风险分": gain("r_both", "y_in"),
          "出库复核：多件订单优先（少件问题）": gain("multi", "y_out")}
at = lambda cur, b: float(cur[int(b * N)])
R["sampling"] = {
    "train": "2017-09 ~ 2018-02", "test": "2018-03 ~ 2018-08", "test_orders": int(N),
    "inbound_target": int(Y_in), "outbound_target": int(Y_out),
    "capture_at_10": {k_: at(v, 0.10) for k_, v in curves.items()},
    "capture_at_20": {k_: at(v, 0.20) for k_, v in curves.items()},
    "multi_share": float((te.item_cnt > 1).mean()),
}
GRID = [round(x_, 2) for x_ in np.arange(0, 1.0001, 0.05)]
T["抽检增益曲线"] = pd.DataFrame({"抽检比例": GRID, **{k_: [at(v, min(b, 1.0)) for b in GRID] for k_, v in curves.items()}})

fig, ax = plt.subplots(figsize=(10, 4.6))
styles = {"随机抽检": (GRAY, 1.5), "商家风险分": ("#86b6ef", 2), "商家 × 品类风险分": (BLUE, 2.5),
          "出库复核：多件订单优先（少件问题）": (ORANGE, 2.5)}
step = max(1, N // 400)
for name, cur in curves.items():
    ax.plot(grid[::step], cur[::step], color=styles[name][0], lw=styles[name][1], label=name)
ax.axvline(0.10, color=AXIS, lw=1)
for name in ["商家 × 品类风险分", "出库复核：多件订单优先（少件问题）"]:
    v = at(curves[name], 0.10)
    ax.scatter([0.10], [v], s=40, color=styles[name][0], edgecolor=SURFACE, linewidth=2, zorder=5)
    ax.text(0.115, v, f"{v:.0%}", va="center", fontsize=10, color=INK)
ax.text(0.105, 0.03, "抽检 10%", fontsize=9, color=MUTED)
ax.xaxis.set_major_formatter(PCT)
ax.yaxis.set_major_formatter(PCT)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1.02)
ax.set_xlabel("抽检 / 复核的订单比例（按风险分从高到低）")
ax.set_ylabel("覆盖的问题订单比例")
ax.legend(loc="lower right")
ax.set_title("差异化抽检的增益曲线（样本外：用 2017.09-2018.02 打分，在 2018.03-08 检验）")
save(fig, "fig10_sampling_gain")

# ======================================================================== E. 商家风险模型回测
sm = num(query("SELECT * FROM dws_seller_month"))


def score(s, e):
    w_ = sm[(sm.purchase_month >= s) & (sm.purchase_month <= e)].groupby("seller_id")[
        ["delivered_cnt", "qc_cnt", "review_cnt", "bad_cnt"]].sum()
    p = w_.qc_cnt.sum() / w_.delivered_cnt.sum()
    pb = w_.bad_cnt.sum() / w_.review_cnt.sum()
    w_["raw"] = w_.qc_cnt / w_.delivered_cnt.replace(0, np.nan)
    w_["sm"] = (w_.qc_cnt + 50 * p) / (w_.delivered_cnt + 50)
    w_["bad"] = w_.bad_cnt / w_.review_cnt.replace(0, np.nan)
    el = w_.delivered_cnt >= 30
    w_["tier"] = np.where(~el, "未参评", np.where((w_.sm >= 2 * p) & (w_.qc_cnt >= 3), "高风险",
                          np.where((w_.sm >= 1.5 * p) | (w_.bad >= 1.5 * pb), "需关注", "正常")))
    w_["raw_flag"] = (w_.raw >= 2 * p) & (w_.qc_cnt >= 1)
    return w_, p


splits = [("2017-01", "2017-06", "2017-07", "2017-12"), ("2017-07", "2017-12", "2018-01", "2018-06"),
          ("2017-09", "2018-02", "2018-03", "2018-08")]
rows = []
for a, b, c, e in splits:
    trn, _ = score(a, b)
    tst, p2 = score(c, e)
    j = trn.join(tst[["delivered_cnt", "qc_cnt", "raw", "tier"]], rsuffix="_te", how="inner")
    j = j[j.delivered_cnt_te >= 30]
    both = j[j.delivered_cnt >= 30]
    rho = stats.spearmanr(both.sm, both.raw_te).correlation
    groups = [("高风险", j.tier == "高风险"), ("需关注", j.tier == "需关注"), ("正常", j.tier == "正常"),
              ("不平滑：原始客诉率 ≥ 2 倍", j.raw_flag)]
    for name, mask in groups:
        g = j[mask]
        if not len(g):
            continue
        rows.append({"训练窗口": f"{a}~{b}", "检验窗口": f"{c}~{e}", "分组": name, "商家数": len(g),
                     "训练期客诉率": g.qc_cnt.sum() / g.delivered_cnt.sum(),
                     "检验期客诉率": g.qc_cnt_te.sum() / g.delivered_cnt_te.sum(), "检验期平台": p2,
                     "检验期倍数": g.qc_cnt_te.sum() / g.delivered_cnt_te.sum() / p2,
                     "检验期仍为高风险或需关注": g.tier_te.isin(["高风险", "需关注"]).mean(), "spearman": rho})
bt = pd.DataFrame(rows)
T["风险模型回测"] = bt
pool = bt.groupby("分组").apply(lambda g: pd.Series({"窗口商家数": g["商家数"].sum(),
                                                   "平均倍数": np.average(g["检验期倍数"], weights=g["商家数"])}),
                                include_groups=False)
R["backtest"] = {"rows": bt.to_dict(orient="records"), "pooled": pool.to_dict(orient="index"),
                 "spearman": bt.groupby("检验窗口").spearman.first().to_dict(),
                 "ordering_holds": bool(all(
                     (g.set_index("分组")["检验期倍数"].get("高风险", 9) >= g.set_index("分组")["检验期倍数"].get("需关注", 0) >=
                      g.set_index("分组")["检验期倍数"].get("正常", 0)) for _, g in bt.groupby("检验窗口")))}

fig, ax = plt.subplots(figsize=(10, 3.9))
wins = bt["检验窗口"].unique()
cols = [("高风险", CRIT), ("需关注", WARN), ("正常", GRAY)]
xi = np.arange(len(wins))
for j_, (name, color) in enumerate(cols):
    vals = [float(bt[(bt["检验窗口"] == w_) & (bt["分组"] == name)]["检验期倍数"].iloc[0]) for w_ in wins]
    ns = [int(bt[(bt["检验窗口"] == w_) & (bt["分组"] == name)]["商家数"].iloc[0]) for w_ in wins]
    ax.bar(xi + (j_ - 1) * 0.26, vals, width=0.24, color=color, label=name)
    for i_, (v, n_) in enumerate(zip(vals, ns)):
        ax.text(i_ + (j_ - 1) * 0.26, v + 0.04, f"{v:.1f}×\n({n_}家)", ha="center", va="bottom", fontsize=8.5, color=INK)
ax.axhline(1, color=INK2, lw=1)
ax.text(len(wins) - 0.45, 1.03, "平台 = 1×", fontsize=9, color=INK2)
ax.set_xticks(xi, [f"检验期 {w_.replace('~', ' ~ ')}" for w_ in wins], fontsize=10)
ax.set_ylabel("检验期品质客诉率 ÷ 平台")
ax.set_ylim(0, 3.2)
ax.grid(axis="x", visible=False)
ax.legend(loc="upper left", ncol=3)
ax.set_title("商家风险分层回测：用前 6 个月的分层，预测后 6 个月的品质客诉率")
save(fig, "fig11_backtest")

# ======================================================================== F. 情景测算
base_ = num(query("""
    SELECT q.item_cnt, q.qc_missing, q.qc_fake, q.qc_mismatch, q.main_category_l1, q.is_quality_complaint, s.risk_level
    FROM dwd_qc_order q LEFT JOIN ads_seller_scorecard s ON q.main_seller_id = s.seller_id
    WHERE q.in_scope = 1 AND q.is_delivered = 1 AND q.purchase_month >= '2018-01'"""))
Nb = len(base_)
qc = base_[base_.is_quality_complaint == 1]
mA = ((qc.item_cnt > 1) & (qc.qc_missing == 1)).values
mB = qc.risk_level.isin(["高风险", "需关注"]).values
mC = (qc.main_category_l1.isin(["3C数码", "钟表礼品"]) & ((qc.qc_fake == 1) | (qc.qc_mismatch == 1))).values


def after(pa, pb, pc):
    surv = (1 - pa * mA) * (1 - pb * mB) * (1 - pc * mC)
    return float(surv.sum() / Nb)


base_rate = len(qc) / Nb
SCEN = {"悲观": (0.30, 0.15, 0.15), "中性": (0.50, 0.30, 0.30), "乐观": (0.70, 0.45, 0.45)}
scen = {k_: {"params": v, "rate": after(*v)} for k_, v in SCEN.items()}
tornado = []
for i_, name in enumerate(["A 多件订单少件客诉降幅", "B 风险商家客诉降幅", "C 3C/钟表假货与货不对板降幅"]):
    lo, mid, hi = SCEN["悲观"][i_], SCEN["中性"][i_], SCEN["乐观"][i_]
    p_lo, p_hi = list(SCEN["中性"]), list(SCEN["中性"])
    p_lo[i_], p_hi[i_] = lo, hi
    tornado.append({"参数": name, "悲观取值": lo, "中性取值": mid, "乐观取值": hi,
                    "悲观时品质客诉率": after(*p_lo), "乐观时品质客诉率": after(*p_hi)})
tornado = pd.DataFrame(tornado)
tornado["影响幅度"] = tornado["悲观时品质客诉率"] - tornado["乐观时品质客诉率"]
T["情景测算"] = pd.DataFrame([{"情景": k_, "A": v["params"][0], "B": v["params"][1], "C": v["params"][2],
                           "治理后品质客诉率": v["rate"], "降幅pp": (base_rate - v["rate"]) * 100} for k_, v in scen.items()])
T["敏感性"] = tornado.sort_values("影响幅度", ascending=False)
R["scenarios"] = {"baseline": base_rate, "scenarios": scen, "tornado": tornado.sort_values("影响幅度", ascending=False).to_dict(orient="records")}

fig, ax = plt.subplots(figsize=(10, 3.4))
names = ["现状", "悲观", "中性", "乐观"]
vals = [base_rate] + [scen[n]["rate"] for n in names[1:]]
colors = [GRAY, "#86b6ef", BLUE, "#184f95"]
yi = np.arange(len(names))[::-1]
ax.barh(yi, vals, height=0.5, color=colors)
for y_, v, n in zip(yi, vals, names):
    lab = f"{v:.2%}" if n == "现状" else f"{v:.2%}（A {SCEN[n][0]:.0%} / B {SCEN[n][1]:.0%} / C {SCEN[n][2]:.0%}）"
    ax.text(base_rate * 1.03, y_, lab, va="center", fontsize=10, color=INK)
ax.axvline(0.04, color=CRIT, lw=1)
ax.text(0.0401, -0.55, "目标 4.0%", fontsize=9, color=CRIT, va="bottom")
ax.set_yticks(yi, names)
ax.xaxis.set_major_formatter(PCT1)
ax.set_xlim(0, base_rate * 1.75)
ax.set_ylim(-0.6, len(names) - 0.5)
ax.grid(axis="y", visible=False)
ax.set_title("治理测算三档情景（括号内为各举措对相应客诉的假设降幅）")
save(fig, "fig12_scenarios")


# ---------------------------------------------------------------- 输出
def to_py(o):
    if isinstance(o, dict):
        return {str(k_): to_py(v) for k_, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_py(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if np.isnan(o) else round(float(o), 6)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


(OUT_DIR / "advanced_results.json").write_text(json.dumps(to_py(R), ensure_ascii=False, indent=1), encoding="utf-8")
with pd.ExcelWriter(OUT_DIR / "advanced_tables.xlsx") as xw:
    for name, df in T.items():
        df.to_excel(xw, sheet_name=name[:31], index=False)
print("  → outputs/advanced_results.json, outputs/advanced_tables.xlsx")
for k_ in ["spc", "significance", "seller_ci", "vip_view", "sampling", "scenarios"]:
    print(k_, json.dumps(to_py(R[k_]), ensure_ascii=False)[:500])
print("backtest pooled", R["backtest"]["pooled"], "ordering", R["backtest"]["ordering_holds"])
