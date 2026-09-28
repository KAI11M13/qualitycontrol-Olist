"""Step 7：数据质量校验（每次跑数后执行，任何一条 FAIL 都要先查清楚再出数）。

校验分四类：
  1. 完整性：跨层行数对账（ODS → DWD 不丢单、不重复）
  2. 唯一性：主键无重复
  3. 一致性：同一指标在不同层汇总结果相等（DWD 宽表 = DWS = ADS = 看板）
  4. 合理性：比率落在 [0,1]、时间不倒挂、分子 ≤ 分母
结果写入 outputs/qa/dq_report.md
"""
from datetime import datetime

from common import OUT_DIR, query

CHECKS = [
    # (类别, 检查项, SQL（返回单值）, 期望)
    ("完整性", "ODS订单数 = DWD订单宽表行数",
     "SELECT (SELECT COUNT(*) FROM ods_orders) - (SELECT COUNT(*) FROM dwd_order)", 0),
    ("完整性", "DWD订单宽表 = 品控宽表行数",
     "SELECT (SELECT COUNT(*) FROM dwd_order) - (SELECT COUNT(*) FROM dwd_qc_order)", 0),
    ("完整性", "ODS商品行 = DWD商品行",
     "SELECT (SELECT COUNT(*) FROM ods_order_items) - (SELECT COUNT(*) FROM dwd_order_item)", 0),
    ("完整性", "评价去重后订单数 = ODS评价去重订单数",
     "SELECT (SELECT COUNT(DISTINCT order_id) FROM ods_order_reviews) - (SELECT COUNT(*) FROM dwd_review)", 0),
    ("完整性", "打标表覆盖全部评价",
     "SELECT (SELECT COUNT(*) FROM dwd_review) - (SELECT COUNT(*) FROM dwd_review_tag)", 0),
    ("完整性", "商品品类全部映射到中文维表（未知品类除外）",
     "SELECT COUNT(*) FROM dwd_order_item WHERE category_pt <> 'unknown' AND category_cn = '未知品类'", 0),
    ("唯一性", "dwd_qc_order 主键 order_id 无重复",
     "SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM dwd_qc_order", 0),
    ("唯一性", "dwd_review 一单一条",
     "SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM dwd_review", 0),
    ("一致性", "GMV：商品行合计 = 订单宽表合计（差额 < 0.01）",
     "SELECT ROUND(ABS((SELECT SUM(price) FROM dwd_order_item) - (SELECT SUM(gmv) FROM dwd_order)), 2) >= 0.01", 0),
    ("一致性", "签收单：宽表(in_scope) = 看板cube",
     "SELECT (SELECT SUM(is_delivered) FROM dwd_qc_order WHERE in_scope = 1) - (SELECT SUM(delivered_cnt) FROM ads_qc_cube_month)", 0),
    ("一致性", "品质客诉单：宽表(in_scope,签收) = 看板cube = 月KPI",
     "SELECT ABS((SELECT SUM(is_delivered * is_quality_complaint) FROM dwd_qc_order WHERE in_scope = 1) "
     "- (SELECT SUM(qc_cnt) FROM ads_qc_cube_month)) "
     "+ ABS((SELECT SUM(qc_cnt) FROM ads_qc_cube_month) - (SELECT SUM(qc_cnt) FROM ads_qc_kpi_month))", 0),
    ("一致性", "HTML看板数据集 与 看板cube：订单/签收/品质客诉三项合计一致",
     "SELECT ABS((SELECT SUM(order_cnt) FROM ads_qc_dashboard_cube) - (SELECT SUM(order_cnt) FROM ads_qc_cube_month)) "
     "+ ABS((SELECT SUM(delivered_cnt) FROM ads_qc_dashboard_cube) - (SELECT SUM(delivered_cnt) FROM ads_qc_cube_month)) "
     "+ ABS((SELECT SUM(qc_cnt) FROM ads_qc_dashboard_cube) - (SELECT SUM(qc_cnt) FROM ads_qc_cube_month))", 0),
    ("一致性", "品类DWS签收单 = cube中有商品明细订单的签收单",
     "SELECT (SELECT SUM(delivered_cnt) FROM dws_category_month) "
     "- (SELECT SUM(is_delivered) FROM dwd_qc_order WHERE in_scope = 1 AND main_seller_id IS NOT NULL)", 0),
    ("一致性", "商家DWS订单数 = 订单×商家粒度行数(in_scope)",
     "SELECT (SELECT SUM(order_cnt) FROM dws_seller_month) - (SELECT COUNT(*) FROM dwd_order_seller os "
     "JOIN dwd_order o ON os.order_id = o.order_id WHERE o.in_scope = 1)", 0),
    ("合理性", "品质客诉单只来自 1-3 星评价",
     "SELECT COUNT(*) FROM dwd_qc_order WHERE is_quality_complaint = 1 AND review_score > 3", 0),
    ("合理性", "月度比率指标均在 [0,1]",
     "SELECT COUNT(*) FROM ads_qc_kpi_month WHERE qc_rate NOT BETWEEN 0 AND 1 OR bad_rate NOT BETWEEN 0 AND 1 "
     "OR on_time_rate NOT BETWEEN 0 AND 1 OR cancel_rate NOT BETWEEN 0 AND 1", 0),
    ("合理性", "分子 ≤ 分母：品质客诉单 ≤ 签收单（商家月）",
     "SELECT COUNT(*) FROM dws_seller_month WHERE qc_cnt > delivered_cnt OR bad_cnt > review_cnt", 0),
    ("合理性", "评分取值在 1-5",
     "SELECT COUNT(*) FROM dwd_review WHERE review_score NOT BETWEEN 1 AND 5", 0),
]

# 已知数据问题：不阻断出数，但要在报告中披露并说明处理方式
KNOWN_ISSUES = [
    ("状态=delivered 但签收时间为空", "SELECT COUNT(*) FROM ods_orders WHERE order_status='delivered' "
     "AND order_delivered_customer_date IS NULL", "is_delivered 置 0，不计入签收口径"),
    ("时间倒挂（出库早于下单 / 签收早于出库）", "SELECT SUM(dq_time_anomaly) FROM dwd_order",
     "打 dq_time_anomaly 标记，时效类指标剔除"),
    ("订单无商品明细", "SELECT COUNT(*) FROM dwd_order WHERE main_seller_id IS NULL",
     "767 单为取消/不可用，其余 8 单停留在 created/invoiced/shipped；计入订单与取消口径，不参与品类/商家归因"),
    ("同一订单多条评价", "SELECT COUNT(*) FROM dwd_review WHERE dup_cnt > 1", "保留最后一次提交的评价"),
    ("商品缺失品类", "SELECT COUNT(*) FROM ods_products WHERE product_category_name IS NULL", "归入'未知品类'"),
    ("支付金额与商品+运费不一致(差额>1)", "SELECT COUNT(*) FROM (SELECT i.order_id FROM "
     "(SELECT order_id, SUM(price + freight_value) v FROM ods_order_items GROUP BY order_id) i JOIN "
     "(SELECT order_id, SUM(payment_value) v FROM ods_order_payments GROUP BY order_id) p "
     "ON i.order_id = p.order_id WHERE ABS(i.v - p.v) > 1) t", "GMV 统一取商品售价之和，不用支付金额"),
    ("分析窗口外订单（2016年 / 2018-09以后）", "SELECT COUNT(*) FROM dwd_order WHERE in_scope = 0",
     "in_scope = 0，不进入 DWS/ADS"),
]


def main() -> None:
    lines = [f"# 数据质量校验报告\n\n生成时间：{datetime.now():%Y-%m-%d %H:%M}\n",
             "## 一、校验项（全部通过才允许出数）\n",
             "| 类别 | 检查项 | 实际值 | 期望 | 结果 |", "|---|---|---|---|---|"]
    fails = 0
    for cat, name, sql, expect in CHECKS:
        val = query(sql).iloc[0, 0]
        val = int(val) if val is not None else None
        ok = val == expect
        fails += not ok
        lines.append(f"| {cat} | {name} | {val} | {expect} | {'✅ PASS' if ok else '❌ FAIL'} |")
        print(f"{'PASS' if ok else 'FAIL'}  [{cat}] {name}  (实际 {val})")

    lines += ["\n## 二、已知数据问题与处理方式\n", "| 问题 | 影响行数 | 处理方式 |", "|---|---|---|"]
    for name, sql, how in KNOWN_ISSUES:
        n = int(query(sql).iloc[0, 0])
        lines.append(f"| {name} | {n:,} | {how} |")

    (OUT_DIR / "qa").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "qa" / "dq_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n{len(CHECKS) - fails}/{len(CHECKS)} 通过 → outputs/qa/dq_report.md")
    if fails:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
