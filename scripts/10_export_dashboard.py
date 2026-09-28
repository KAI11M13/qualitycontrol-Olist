"""Step 10：导出看板数据 → 生成 HTML 看板 + BI 工具导入用 CSV。

  dashboard/index.html   本地双击即可打开的交互看板（数据内嵌，ECharts 优先走 CDN，离线时用 vendor/）
  dashboard/bi_data/*.csv  Power BI / Tableau / SmartBI 导入用的数据集（与 HTML 看板同源）
"""
import importlib
import json
from datetime import date

from common import OUT_DIR, ROOT, query

md = importlib.import_module("09_metric_dictionary")
DASH = ROOT / "dashboard"

# 六条口径规则（与 docs/02_指标体系.md 第 4 节相同）
RULES = [
    ("按下单月归属", "一个订单的分子、分母都记在它的下单月，保证分子和分母是同一批订单。"),
    ("签收订单", "订单状态为已签收且签收时间不为空，才进入品质客诉率的分母。"),
    ("只取最后一次评价", "同一订单有多条评价时，只使用提交时间最晚的一条。"),
    ("品质客诉订单只认 1-3 星", "4-5 星评价里的\"sem defeito（没有瑕疵）\"等表述不计入，避免关键词误识别。"),
    ("一个订单可命中多个标签", "一条评价可能同时命中少件漏发和质量缺陷，5 个结果指标之和大于品质客诉率，不能相加。"),
    ("比率在最后一步计算", "汇总表只存订单数，筛选后再相除；不对各品类的品质客诉率求简单平均。"),
]


def main() -> None:
    cube = query("SELECT * FROM ads_qc_dashboard_cube ORDER BY purchase_month, category_l1, category_cn, order_type")
    cols = list(cube.columns)
    rows = []
    for r in cube.itertuples(index=False):
        rows.append([float(v) if hasattr(v, "as_tuple") else v for v in r])     # Decimal → float

    sellers = query("SELECT * FROM ads_seller_scorecard")
    issue_cols = {"qc_defect_cnt": "质量缺陷", "qc_mismatch_cnt": "货不对板", "qc_missing_cnt": "少件漏发", "qc_fake_cnt": "假货"}
    recs = []
    for s in sellers.to_dict(orient="records"):
        s = {k: (float(v) if hasattr(v, "as_tuple") else v) for k, v in s.items()}
        top = max(issue_cols, key=lambda c: s[c])
        s["main_issue"] = f"{issue_cols[top]}（{int(s[top])}）" if s["qc_cnt"] else "—"
        recs.append(s)

    vals = md.compute_baselines()
    metrics = [{
        "code": m[0], "name": m[1], "level": m[2], "definition": m[5], "formula": m[6],
        "baseline": md.fmt_value(v, m[md.I_UNIT]) + ("" if v is None or m[md.I_UNIT] == "%" else f" {m[md.I_UNIT]}"),
        "target": m[md.I_TARGET], "available": m[md.I_AVAIL],
    } for m, v in zip(md.M, vals)]

    # 预警：按评价日期连续 3 天及以上每天都有品质客诉订单的商家（与 SQL 题库 Q15 口径相同）
    streaks = query("""
        WITH sd AS (
            SELECT os.seller_id, q.review_date AS d, COUNT(DISTINCT q.order_id) AS n
            FROM dwd_qc_order q
            JOIN dwd_order_seller os ON os.order_id = q.order_id
            WHERE q.is_delivered = 1 AND q.is_quality_complaint = 1
            GROUP BY os.seller_id, q.review_date
        ),
        g AS (
            SELECT seller_id, d, n, DATE_SUB(d, INTERVAL ROW_NUMBER() OVER (PARTITION BY seller_id ORDER BY d) DAY) AS grp
            FROM sd
        )
        SELECT seller_id, MIN(d) AS start_day, MAX(d) AS end_day, COUNT(*) AS days, SUM(n) AS qc_orders
        FROM g
        GROUP BY seller_id, grp
        HAVING COUNT(*) >= 3
        ORDER BY end_day DESC, days DESC""")
    streak_rows = [[r.seller_id, str(r.start_day), str(r.end_day), int(r.days), int(r.qc_orders)] for r in streaks.itertuples()]

    res = json.loads((OUT_DIR / "analysis_results.json").read_text(encoding="utf-8"))
    data = {
        "meta": {"generated": str(date.today()), "seller_benchmark_qc_rate": float(sellers.benchmark_qc_rate.iloc[0]),
                 "seller_cover": res["seller_eligible_order_cover"]},
        "cube": {"cols": cols, "rows": rows},
        "sellers": recs,
        "streaks": streak_rows,
        "metrics": metrics,
        "rules": RULES,
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    body = (DASH / "template.html").read_text(encoding="utf-8").replace("/*__DATA__*/null", payload)

    # 本地版：补齐文档骨架；发布版（Artifact）由平台注入骨架，直接用 body
    local = ("<!doctype html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"utf-8\">\n"
             "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
             "</head>\n<body>\n" + body + "\n</body>\n</html>\n")
    (DASH / "index.html").write_text(local, encoding="utf-8")
    (OUT_DIR / "dashboard_artifact.html").write_text(body, encoding="utf-8")
    print(f"  → dashboard/index.html（{len(local) / 1024:.0f} KB，cube {len(rows)} 行，商家 {len(recs)} 家，商家连续品质客诉预警 {len(streak_rows)} 条）")

    # BI 工具导入数据
    bi = DASH / "bi_data"
    bi.mkdir(exist_ok=True)
    exports = {
        "ads_qc_dashboard_cube.csv": "SELECT * FROM ads_qc_dashboard_cube",
        "ads_qc_kpi_month.csv": "SELECT * FROM ads_qc_kpi_month",
        "ads_seller_scorecard.csv": "SELECT * FROM ads_seller_scorecard",
        "ads_category_quality.csv": "SELECT * FROM ads_category_quality",
        "dim_category.csv": "SELECT * FROM dim_category",
        "dim_complaint_rule.csv": "SELECT tag_code, tag_name, tag_group, priority FROM dim_complaint_rule",
    }
    for fn, sql in exports.items():
        query(sql).to_csv(bi / fn, index=False, encoding="utf-8-sig")
    print(f"  → dashboard/bi_data/ {len(exports)} 个 CSV")


if __name__ == "__main__":
    main()
