"""Step 12：导出 PPT / 报告要用的全部数字 → outputs/deck_data.json。

PPT 与报告里的每个数都从这里取，不手抄。
"""
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
parts = ["quality", "fulfill", "service", "other", "notext"]
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
data = {
    "counts": {k: int(v) for k, v in counts.items()},
    "overview": res["overview"],
    "months": [m[2:].replace("-", ".") for m in kpi.purchase_month],
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
    "pareto_top10pct_orders_qc_share": res["pareto_top10pct_orders_qc_share"],
    "pareto_top10pct_orders_sellers": res["pareto_top10pct_orders_sellers"],
    "category_top": cat.assign(**{c: cat[c].astype(float) for c in cat.columns if c != "category_cn"}).to_dict(orient="records"),
    "heavy": res["heavy"],
    "info": res["info"],
    "fake_top": res["fake_top"],
    "fake_platform": res["fake_platform"],
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
    "gain": pd.read_excel(OUT_DIR / "advanced_tables.xlsx", sheet_name="抽检增益曲线").round(4).to_dict(orient="list"),
    "sql_total": len(Q),
}
(OUT_DIR / "deck_data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("  → outputs/deck_data.json")
