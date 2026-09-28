"""Step 12：导出 PPT / 报告要用的全部数字 → outputs/deck_data.json。

PPT 与报告里的每个数都从这里取，不手抄。
"""
import importlib
import json

import pandas as pd

from common import OUT_DIR, query
from interview_questions import Q

res = json.loads((OUT_DIR / "analysis_results.json").read_text(encoding="utf-8"))
tables = pd.read_excel(OUT_DIR / "analysis_tables.xlsx", sheet_name=None)


def f(v):
    try:
        return round(float(v), 6)
    except (TypeError, ValueError):
        return v


kpi = query("SELECT purchase_month, qc_rate, bad_rate, on_time_rate, delivered_cnt, qc_cnt FROM ads_qc_kpi_month ORDER BY 1")
mix = tables["差评原因结构_季度"]
parts = ["quality", "fulfill", "other", "notext"]
mix_share = mix[parts].div(mix[parts].sum(axis=1), axis=0)
cat = query("""SELECT category_cn, delivered_cnt, qc_rate, missing_rate, defect_rate, mismatch_rate
               FROM ads_category_quality ORDER BY qc_rate DESC LIMIT 10""")
dq = open(OUT_DIR / "qa" / "dq_report.md", encoding="utf-8").read()
qa = pd.read_csv(OUT_DIR / "qa" / "tag_validation_sample.csv")

counts = query("""SELECT (SELECT COUNT(*) FROM ods_orders) orders, (SELECT COUNT(*) FROM ods_order_items) items,
    (SELECT COUNT(*) FROM ods_order_reviews) reviews_raw, (SELECT COUNT(*) FROM dwd_review) reviews,
    (SELECT COUNT(*) FROM ods_sellers) sellers, (SELECT COUNT(*) FROM ods_products) products,
    (SELECT COUNT(*) FROM dim_category) categories,
    (SELECT SUM(in_scope) FROM dwd_order) scope_orders,
    (SELECT SUM(is_delivered) FROM dwd_order WHERE in_scope = 1) scope_delivered""").iloc[0]

GE = json.loads((OUT_DIR / "qa" / "tag_gold_eval.json").read_text(encoding="utf-8"))
MD = importlib.import_module("09_metric_dictionary")
DQ = importlib.import_module("07_data_quality_check")
known = {name: int(query(sql).iloc[0, 0] or 0) for name, sql, _ in DQ.KNOWN_ISSUES}   # 已知数据问题的订单数
# 口径对比（SQL 题库 Q18）：下单月 2018-03 按下单月归属 vs 分子按评价月、分母按签收月
cal = query("""
    SELECT (SELECT SUM(is_delivered * is_quality_complaint) FROM dwd_qc_order
             WHERE in_scope = 1 AND purchase_month = '2018-03') AS a_qc,
           (SELECT SUM(is_delivered) FROM dwd_qc_order WHERE in_scope = 1 AND purchase_month = '2018-03') AS a_del,
           (SELECT SUM(is_delivered * is_quality_complaint) FROM dwd_qc_order
             WHERE review_date >= '2018-03-01' AND review_date < '2018-04-01') AS b_qc,
           (SELECT SUM(is_delivered) FROM dwd_qc_order
             WHERE delivered_ts >= '2018-03-01' AND delivered_ts < '2018-04-01') AS b_del""").iloc[0].astype(float)
data = {
    "counts": {k: int(v) for k, v in counts.items()},
    "overview": res["overview"],
    "months": list(kpi.purchase_month),
    "qc_rate": [f(v) for v in kpi.qc_rate],
    "bad_rate": [f(v) for v in kpi.bad_rate],
    "on_time_rate": [f(v) for v in kpi.on_time_rate],
    "period": res["period"],
    "quarters": list(mix.q),
    "mix": {p: [f(v) for v in mix_share[p]] for p in parts},
    "type_by_year": res["type_by_year"],
    "decomp_category": res["decomp_category"],
    "decomp_order_type": res["decomp_order_type"],
    "decomp_category_top": res["decomp_category_top"],
    "multi_item": res["multi_item"],
    "order_type": res["order_type"],
    "seller_tier": res["seller_tier"],
    "seller_tier_share": res["seller_tier_share"],
    "seller_eligible": res["seller_eligible"],
    "seller_cover": res["seller_eligible_order_cover"],
    "seller_benchmark": res["seller_benchmark_qc_rate"],
    "pareto_top10pct_orders_qc_share": res["pareto_top10pct_orders_qc_share"],
    "pareto_top10pct_orders_sellers": res["pareto_top10pct_orders_sellers"],
    "category_top": cat.assign(**{c: cat[c].astype(float) for c in cat.columns if c != "category_cn"}).to_dict(orient="records"),
    "heavy": res["heavy"],
    "info": res["info"],
    "fake_top": res["fake_top"],
    "fake_platform": res["fake_platform"],
    # 假货客诉率的精确分子分母（下单月 2017-01 至 2018-08 的签收订单；fake_platform 经 MySQL 除法保留 4 位小数，只作展示）
    "fake_counts": {k: int(v) for k, v in query("""
        SELECT SUM(qc_fake) AS fake, COUNT(*) AS n FROM dwd_qc_order WHERE in_scope = 1 AND is_delivered = 1""").iloc[0].items()},
    "falsify": res["falsify"],
    "sizing": res["sizing"],
    "tag_accuracy": float(qa["判定（AI 逐条阅读原文）"].mean()),
    "tag_accuracy_by_type": qa.groupby("primary_tag")["判定（AI 逐条阅读原文）"].mean().round(3).to_dict(),
    "tag_samples": int(len(qa)),
    "dq_checks": dq.count("✅ PASS"),
    "dq_fail": dq.count("❌ FAIL"),
    "sql_levels": {lv: sum(q["level"] == lv for q in Q) for lv in ["基础", "进阶", "高阶", "开放"]},
    "adv": json.loads((OUT_DIR / "advanced_results.json").read_text(encoding="utf-8")),
    "gold": GE["any"],
    "gold_by_type": GE["by_type"],
    "gold_by_year": GE["by_year"],
    "gold_cf": GE["correction_factor"],
    "gold_population": GE["population"],
    "samr": pd.read_csv(OUT_DIR.parent / "data" / "external" / "samr_spot_checks.csv").fillna("").to_dict(orient="records"),
    "p_chart": pd.read_excel(OUT_DIR / "advanced_tables.xlsx", sheet_name="p控制图")[["m", "p", "ucl", "lcl"]].round(6).to_dict(orient="list"),
    "gain": pd.read_excel(OUT_DIR / "advanced_tables.xlsx", sheet_name="增益曲线").round(4).to_dict(orient="list"),
    "sql_total": len(Q),
    "metric_count": len(MD.M),
    "metric_live": sum(m[MD.I_AVAIL] == "已上线" for m in MD.M),
    "known_issues": known,
    "caliber_2018_03": {"a": cal.a_qc / cal.a_del, "b": cal.b_qc / cal.b_del},
}
(OUT_DIR / "deck_data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("  → outputs/deck_data.json")
