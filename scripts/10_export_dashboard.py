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

RULES = [
    ("时间归属：按下单月", "所有指标的分子、分母都按下单月归到同一批订单，避免\"本月的客诉来自上月的订单\"。"),
    ("签收口径", "订单状态为已签收且有签收时间，才进入品质客诉率的分母。"),
    ("一单一评", "同一订单多次评价时，只保留用户最后一次提交的评价。"),
    ("品质客诉只认 1-3 星", "4-5 星评价里的\"sem defeito（没有瑕疵）\"等表述不计入，避免关键词误判。"),
    ("问题类型可多选", "一条评价可能同时命中少件和缺陷，各类型发生率之和大于品质客诉率，不能相加。"),
    ("比率最后再算", "底表只存计数，筛选后再相除；不对各品类的客诉率求简单平均。"),
]


def main() -> None:
    cube = query("SELECT * FROM ads_qc_dashboard_cube ORDER BY purchase_month, category_l1, category_cn, order_type")
    cols = list(cube.columns)
    rows = []
    for r in cube.itertuples(index=False):
        rows.append([float(v) if hasattr(v, "as_tuple") else v for v in r])     # Decimal → float

    sellers = query("SELECT * FROM ads_seller_scorecard")
    issue_cols = {"qc_defect_cnt": "质量缺陷", "qc_mismatch_cnt": "货不对板", "qc_missing_cnt": "少件/漏发", "qc_fake_cnt": "假货"}
    recs = []
    for s in sellers.to_dict(orient="records"):
        s = {k: (float(v) if hasattr(v, "as_tuple") else v) for k, v in s.items()}
        top = max(issue_cols, key=lambda c: s[c])
        s["main_issue"] = f"{issue_cols[top]}（{int(s[top])}）" if s["qc_cnt"] else "—"
        recs.append(s)

    vals = md.compute_baselines()
    metrics = [{
        "code": m[0], "name": m[1], "level": m[2], "definition": m[6], "formula": m[7],
        "baseline": md.fmt_value(v, m[12]) + ("" if v is None or m[12] in ("%",) else f" {m[12]}"),
        "target": m[14], "available": m[16],
    } for m, v in zip(md.M, vals)]

    res = json.loads((OUT_DIR / "analysis_results.json").read_text(encoding="utf-8"))
    data = {
        "meta": {"generated": str(date.today()), "seller_platform_qc_rate": float(sellers.platform_qc_rate.iloc[0]),
                 "seller_cover": res["seller_eligible_order_cover"]},
        "cube": {"cols": cols, "rows": rows},
        "sellers": recs,
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
    print(f"  → dashboard/index.html（{len(local) / 1024:.0f} KB，cube {len(rows)} 行，商家 {len(recs)} 家）")

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
