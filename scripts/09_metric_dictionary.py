"""Step 9：生成品控指标字典（Excel + Markdown）。

指标名称、层级、定义与 docs/00_术语与口径.md 完全一致。
每个指标的"口径 SQL"都会被实际执行一遍，得到 2018 年 1-8 月的基准值写进字典：
字典里的 SQL 不是示意，而是能跑、跑出来就是看板/报告上的那个数。
"""
import json
from datetime import date

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from common import OUT_DIR, ROOT, query

W = "in_scope = 1 AND purchase_month BETWEEN '2018-01' AND '2018-08'"   # 基准值窗口
SC = "（商家评估窗口：下单月 2018-03 至 2018-08）"
CL = "预警：当月高于上控制限（中心线 = 2017 年该指标，控制限 = 中心线 ± 3σ）"
CL_LOW = "预警：当月低于下控制限（中心线 = 2017 年该指标，控制限 = 中心线 ± 3σ）"
SAME = "同品质客诉率"

# 字段：编码, 名称, 层级, 业务域, 父指标, 业务定义, 计算公式, 统计范围/过滤, 下钻维度, 来源表, 口径SQL, 单位, 方向, 目标/预警, 更新频率, 可得性, 易错点
M = [
    # ------------------------------------------------------------------ 核心指标
    ("QC001", "品质客诉率", "核心指标", "品质", "—",
     "签收订单中，用户因商品本身的问题给出 1-3 星、并在评价文字里描述了该问题的订单所占的比例。",
     "品质客诉订单数 ÷ 签收订单数",
     "签收订单（订单状态为已签收且签收时间不为空）；按下单月归属；只取最后一次评价",
     "下单月、一级类目、主品类、主商家、用户省份、订单结构、标签",
     "dwd_qc_order",
     f"SELECT SUM(is_delivered * is_quality_complaint) / SUM(is_delivered) FROM dwd_qc_order WHERE {W}",
     "%", "越低越好", "目标：不高于中心线（2017 年品质客诉率）；" + CL.replace("2017 年该指标", "2017 年品质客诉率"),
     "日更（T+1）", "已上线",
     "① 分子分母必须是同一批订单（都按下单月归属），不能用\"本月评价数 ÷ 本月签收订单数\"；② 一个订单只计一次，不按标签重复计数；③ 4-5 星评价即使命中关键词也不计入"),
    # ------------------------------------------------------------------ 结果指标
    ("QC101", "少件漏发客诉率", "结果指标", "品质", "QC001",
     "少件漏发客诉订单（命中少件漏发标签的品质客诉订单）占签收订单的比例。",
     "少件漏发客诉订单数 ÷ 签收订单数", SAME, SAME + " + 单件订单 / 多件订单", "dwd_qc_order",
     f"SELECT SUM(is_delivered * qc_missing) / SUM(is_delivered) FROM dwd_qc_order WHERE {W}",
     "%", "越低越好", CL, "日更", "已上线",
     "一个订单可同时命中多个标签，5 个结果指标之和大于品质客诉率，不能相加"),
    ("QC102", "质量缺陷客诉率", "结果指标", "品质", "QC001",
     "质量缺陷客诉订单（命中质量缺陷标签的品质客诉订单）占签收订单的比例。",
     "质量缺陷客诉订单数 ÷ 签收订单数", SAME, SAME, "dwd_qc_order",
     f"SELECT SUM(is_delivered * qc_defect) / SUM(is_delivered) FROM dwd_qc_order WHERE {W}",
     "%", "越低越好", CL, "日更", "已上线", "外包装压扁但商品完好 → 只计包装破损，不计质量缺陷"),
    ("QC103", "货不对板客诉率", "结果指标", "品质", "QC001",
     "货不对板客诉订单（命中货不对板标签的品质客诉订单）占签收订单的比例。",
     "货不对板客诉订单数 ÷ 签收订单数", SAME, SAME, "dwd_qc_order",
     f"SELECT SUM(is_delivered * qc_mismatch) / SUM(is_delivered) FROM dwd_qc_order WHERE {W}",
     "%", "越低越好", CL, "日更", "已上线", "\"endereço errado（地址错）\"属于履约问题，规则已排除"),
    ("QC104", "假货客诉率", "结果指标", "品质", "QC001",
     "假货客诉订单（命中假货标签的品质客诉订单）占签收订单的比例，以\"单/万单\"表示。",
     "假货客诉订单数 ÷ 签收订单数 × 10,000", SAME, SAME, "dwd_qc_order",
     f"SELECT SUM(is_delivered * qc_fake) / SUM(is_delivered) * 10000 FROM dwd_qc_order WHERE {W}",
     "单/万单", "越低越好", CL, "日更", "已上线",
     "分子小、按月波动大，看趋势时同时看下单月 2017-01 至今的累计值；单个商家出现 1 单即人工核实"),
    ("QC105", "包装破损客诉率", "结果指标", "品质", "QC001",
     "包装破损客诉订单（命中包装破损标签的品质客诉订单）占签收订单的比例。",
     "包装破损客诉订单数 ÷ 签收订单数", SAME, SAME, "dwd_qc_order",
     f"SELECT SUM(is_delivered * qc_package) / SUM(is_delivered) FROM dwd_qc_order WHERE {W}",
     "%", "越低越好", CL, "日更", "已上线", "—"),
    ("IN604", "品质退货率", "结果指标", "品质", "QC001",
     "因品质原因（质量缺陷、货不对板、少件漏发、假货）退货的商品件数占签收商品件数的比例；与品质客诉率互相印证。",
     "品质原因退货件数 ÷ 签收件数", "退货原因属于品质原因", SAME, "售后退货表", None, "%", "越低越好", "—", "日更",
     "公开数据没有，待接入", "退货原因由用户勾选，存在\"不想要了选质量问题\"的情况，需要结合质检复核结果修正"),
    # ------------------------------------------------------------------ 体验指标
    ("EX201", "差评率", "体验指标", "体验", "—",
     "有评价的订单中，最后一次评价为 1-2 星（差评）的订单所占的比例。同时受商品、物流和服务影响，不用于考核品控。",
     "差评订单数 ÷ 有评价的订单数", "全部订单状态（含未签收）；只取最后一次评价", SAME, "dwd_qc_order",
     f"SELECT SUM(is_bad) / SUM(has_review) FROM dwd_qc_order WHERE {W}",
     "%", "越低越好", "只观察，不设考核目标", "日更", "已上线",
     "受物流影响大：下单月 2018-03 准时签收率降到 81.0%，差评率升到 22.8%"),
    ("EX202", "平均评分", "体验指标", "体验", "—", "有评价的订单的最后一次评价星级的平均值。",
     "最后一次评价星级之和 ÷ 有评价的订单数", "同差评率", SAME, "dwd_qc_order",
     f"SELECT AVG(review_score) FROM dwd_qc_order WHERE {W}",
     "分", "越高越好", "只观察，不设考核目标", "日更", "已上线", "平均值受极端值影响，与差评率一起看"),
    ("EX203", "5 星好评率", "体验指标", "体验", "—", "有评价的订单中，最后一次评价为 5 星的订单所占的比例。",
     "最后一次评价为 5 星的订单数 ÷ 有评价的订单数", "同差评率", SAME, "dwd_qc_order",
     f"SELECT SUM(is_five) / SUM(has_review) FROM dwd_qc_order WHERE {W}",
     "%", "越高越好", "只观察，不设考核目标", "日更", "已上线", "—"),
    ("EX204", "差评品质原因占比", "体验指标", "体验", "EX201",
     "差评订单中，主标签属于品质问题标签的订单所占的比例（分母含无文字的差评）。回答\"差评里有多少是品控能管的\"。",
     "主标签属于品质问题标签的差评订单数 ÷ 差评订单数", "最后一次评价为 1-2 星的订单", "下单月、一级类目、主商家",
     "dwd_qc_order",
     f"SELECT SUM(is_bad * (complaint_group = '品质问题')) / SUM(is_bad) FROM dwd_qc_order WHERE {W}",
     "%", "看结构", "只观察，不设考核目标", "周更", "已上线",
     "品质问题标签的优先级高于履约服务标签，所以\"命中任一品质问题标签\"与\"主标签属于品质问题标签\"是同一批订单"),
    # ------------------------------------------------------------------ 过程指标：商品准入
    ("PD301", "动销商品信息完整率", "过程指标-商品准入", "商品", "QC103/QC104",
     "有订单的商品中，品类、图片、描述三项信息都完整的商品所占的比例。",
     "信息完整的动销商品数 ÷ 动销商品数", "窗口内有订单的商品（按商品去重）", "品类、商家", "ods_products + dwd_order_item",
     "SELECT AVG(p.product_category_name IS NOT NULL AND p.product_photos_qty IS NOT NULL "
     "AND p.product_description_lenght IS NOT NULL) FROM ods_products p WHERE p.product_id IN "
     "(SELECT DISTINCT i.product_id FROM dwd_order_item i JOIN dwd_order o ON i.order_id = o.order_id "
     "WHERE o.in_scope = 1 AND o.purchase_month BETWEEN '2018-01' AND '2018-08')",
     "%", "越高越好", "目标 100%（三项信息缺一项就不允许上架）", "周更", "已上线", "按商品去重计算，不是按订单"),
    ("PD302", "信息缺失商品订单占比", "过程指标-商品准入", "商品", "PD301",
     "主商品缺少品类信息（一级类目记为\"未知\"）的订单所占的比例。", "主商品缺少品类信息的订单数 ÷ 订单数",
     "主商品 = 订单中单价最高的商品", "下单月、主商家", "dwd_qc_order",
     f"SELECT AVG(main_category_cn = '未知品类') FROM dwd_qc_order WHERE {W} AND main_product_id IS NOT NULL",
     "%", "越低越好", CL, "周更", "已上线", "—"),
    ("PD303", "高风险品类订单占比", "过程指标-商品准入", "商品", "QC001",
     "主品类的品质客诉率 ≥ 全部签收订单品质客诉率 × 1.2 的订单所占的比例，衡量品类结构带来的风险。",
     "主品类属于高风险品类的订单数 ÷ 订单数", "高风险品类名单按下单月 2017-01 至 2018-08 的数据确定，每季度刷新",
     "下单月", "dwd_qc_order + ads_category_quality",
     "SELECT AVG(main_category_cn IN (SELECT category_cn FROM ads_category_quality WHERE qc_rate >= 1.2 * "
     "(SELECT SUM(qc_cnt) / SUM(delivered_cnt) FROM ads_category_quality))) "
     f"FROM dwd_qc_order WHERE {W} AND main_product_id IS NOT NULL",
     "%", "看结构", "只观察结构", "月更", "已上线", "1.2 倍的比较基准是全部签收订单的品质客诉率（品类表内按签收订单数加权）"),
    # ------------------------------------------------------------------ 过程指标：商家管理
    ("SP401", "发货超时率", "过程指标-商家管理", "商家", "QC001/FF501",
     "商家把商品交给物流的时间晚于平台规定发货时限（shipping_limit_date）的订单所占的比例。",
     "发货超时订单数 ÷ 已发货订单数", "已发货订单；按商家汇总时用该商家自己的发货时限", "下单月、主商家、主品类",
     "dwd_qc_order / dws_seller_month",
     f"SELECT SUM(is_ship_overdue) / SUM(is_shipped) FROM dwd_qc_order WHERE {W}",
     "%", "越低越好", CL, "日更", "已上线", "平台汇总用订单中最晚的发货时限，商家汇总用商家自己的发货时限，两者分母不同"),
    ("SP402", "平均发货时长", "过程指标-商家管理", "商家", "SP401", "从下单到商家把商品交给物流的平均天数。",
     "Σ(发货时间 − 下单时间) ÷ 已发货订单数", "剔除时间倒挂的订单（dq_time_anomaly = 1）", "下单月、主商家",
     "dwd_qc_order",
     f"SELECT AVG(ship_days) FROM dwd_qc_order WHERE {W} AND is_shipped = 1 AND dq_time_anomaly = 0",
     "天", "越低越好", "—", "日更", "已上线", "—"),
    ("SP403", "高风险商家数", "过程指标-商家管理", "商家", "QC001",
     "参评商家中，平滑品质客诉率 ≥ 商家基准品质客诉率 × 2，且商家品质客诉订单不少于 3 单的商家个数。" + SC,
     "高风险商家的个数", "参评商家（商家签收订单不少于 30 单）", "—", "ads_seller_scorecard",
     "SELECT COUNT(*) FROM ads_seller_scorecard WHERE risk_level = '高风险'",
     "家", "越低越好", "目标：进入名单的商家 30 天内完成整改", "月更", "已上线",
     "用平滑品质客诉率（向商家基准品质客诉率靠拢 50 单）判定，避免单量少的商家\"1 个品质客诉订单就是高风险\""),
    ("SP404", "高风险商家品质客诉订单占比", "过程指标-商家管理", "商家", "SP403",
     "高风险商家的商家品质客诉订单占参评商家全部商家品质客诉订单的比例。" + SC,
     "高风险商家的商家品质客诉订单数 ÷ 参评商家的商家品质客诉订单数", "同高风险商家数", "—", "ads_seller_scorecard",
     "SELECT SUM(CASE WHEN risk_level = '高风险' THEN qc_cnt ELSE 0 END) / SUM(qc_cnt) FROM ads_seller_scorecard",
     "%", "越低越好", "—", "月更", "已上线", "与高风险商家的商家签收订单占比对照看"),
    ("SP405", "商家品质分", "过程指标-商家管理", "商家", "SP403",
     "参评商家的 0-100 分综合得分：品质客诉率占 50%、差评率 20%、发货超时率 15%、准时签收率 15%，每项按该商家在参评商家中的百分位排名打分。" + SC,
     "Σ 权重 × 100 × 百分位得分", "同高风险商家数", "主商家", "ads_seller_scorecard",
     "SELECT AVG(quality_score) FROM ads_seller_scorecard",
     "分", "越高越好", "只用于商家之间排序", "月更", "已上线",
     "按百分位打分，全部参评商家的平均分固定在 50 分左右，不能用来看整体趋势"),
    ("SP406", "参评商家订单覆盖率", "过程指标-商家管理", "商家", "SP405",
     "参评商家的商家签收订单占全部商家的商家签收订单的比例，衡量商家分层覆盖了多少订单。" + SC,
     "参评商家的商家签收订单数 ÷ 全部商家的商家签收订单数", "同高风险商家数", "—", "ads_seller_scorecard + dws_seller_month",
     "SELECT (SELECT SUM(delivered_cnt) FROM ads_seller_scorecard) / SUM(delivered_cnt) FROM dws_seller_month "
     "WHERE purchase_month BETWEEN '2018-03' AND '2018-08'",
     "%", "越高越好", "—", "月更", "已上线", "—"),
    # ------------------------------------------------------------------ 过程指标：仓配履约
    ("FF501", "准时签收率", "过程指标-仓配履约", "履约", "EX201",
     "签收日期不晚于承诺送达日期的签收订单所占的比例。", "签收日期不晚于承诺送达日期的签收订单数 ÷ 签收订单数",
     "签收订单；按日期比较", "下单月、用户省份、主商家", "dwd_qc_order",
     f"SELECT 1 - SUM(is_delivered * is_late) / SUM(is_delivered) FROM dwd_qc_order WHERE {W}",
     "%", "越高越好", CL_LOW, "日更", "已上线", "承诺送达日期只有日期部分，必须按日期比较，否则当天送达会被误判为晚到"),
    ("FF502", "平均送达时长", "过程指标-仓配履约", "履约", "FF501", "从下单到用户签收的平均天数。",
     "Σ(签收时间 − 下单时间) ÷ 签收订单数", "剔除时间倒挂的订单", "下单月、用户省份", "dwd_qc_order",
     f"SELECT AVG(delivery_days) FROM dwd_qc_order WHERE {W} AND is_delivered = 1 AND dq_time_anomaly = 0",
     "天", "越低越好", "—", "日更", "已上线", "最近月份还有订单没签收、没计入，数值会偏低"),
    ("FF503", "多件订单占比", "过程指标-仓配履约", "履约", "QC101", "多件订单（件数不少于 2）占签收订单的比例。",
     "多件订单数 ÷ 签收订单数", "签收订单", "下单月、主商家、主品类", "dwd_qc_order",
     f"SELECT AVG(item_cnt > 1) FROM dwd_qc_order WHERE {W} AND is_delivered = 1",
     "%", "看结构", "只观察结构", "周更", "已上线", "—"),
    ("FF504", "多件订单少件漏发客诉率", "过程指标-仓配履约", "履约", "QC101",
     "多件订单中，少件漏发客诉订单所占的比例。",
     "多件订单中的少件漏发客诉订单数 ÷ 多件订单数", "签收订单且件数不少于 2", "下单月、主商家、是否多商家",
     "dwd_qc_order",
     f"SELECT SUM(qc_missing) / COUNT(*) FROM dwd_qc_order WHERE {W} AND is_delivered = 1 AND item_cnt > 1",
     "%", "越低越好", "目标：比基期（2018 年 1-8 月）下降 50%（举措 A 中性情景）", "周更", "已上线", "—"),
    ("FF505", "订单取消率", "过程指标-仓配履约", "履约", "—", "被取消或因缺货无法履约的订单所占的比例。",
     "(已取消 + 无法履约) 订单数 ÷ 订单数", "全部订单", "下单月、主品类", "dwd_qc_order",
     f"SELECT SUM(is_canceled + is_unavailable) / COUNT(*) FROM dwd_qc_order WHERE {W}",
     "%", "越低越好", CL, "日更", "已上线", "—"),
    ("FF506", "未收到货客诉率", "过程指标-仓配履约", "履约", "EX201",
     "最后一次评价 1-3 星且命中未收到货标签的订单所占的比例（不限是否签收）；不计入品质客诉率。",
     "最后一次评价 1-3 星且命中未收到货标签的订单数 ÷ 订单数", "全部订单", "下单月、用户省份", "dwd_qc_order",
     f"SELECT SUM(fc_not_received) / COUNT(*) FROM dwd_qc_order WHERE {W}",
     "%", "越低越好", CL, "日更", "已上线", "—"),
    # ------------------------------------------------------------------ 过程指标：待接入
    ("IN601", "入仓质检合格率", "过程指标-待接入", "质检", "QC102",
     "商品入仓时，质检合格的批次（或件数）所占的比例。", "质检合格批次数 ÷ 质检批次数", "入仓质检记录",
     "供应商、品类、质检项", "内部质检系统", None, "%", "越高越好", "—", "日更", "公开数据没有，待接入",
     "区分\"批次合格率\"与\"件数合格率\"，汇报时写清楚用的是哪一个"),
    ("IN602", "入仓抽检比例", "过程指标-待接入", "质检", "IN601", "入仓批次中被抽检的批次所占的比例（高风险商家应为 100%）。",
     "抽检批次数 ÷ 入仓批次数", "—", "供应商、品类", "内部质检系统", None, "%", "越高越好", "—", "日更", "公开数据没有，待接入", "—"),
    ("IN603", "问题商品拦截率", "过程指标-待接入", "质检", "QC001",
     "质检拦截的问题件数占全部问题件数（质检拦截 + 签收后成为品质客诉订单）的比例，衡量质检的有效性。",
     "质检拦截的问题件数 ÷ (质检拦截的问题件数 + 品质客诉订单中的问题件数)", "—", "供应商、标签", "内部质检系统 + dwd_qc_order",
     None, "%", "越高越好", "—", "周更", "公开数据没有，待接入", "分子和分母要对齐到同一套标签"),
    ("IN605", "品质客诉首次响应时长", "过程指标-待接入", "服务", "EX201", "品质问题相关的客服工单从创建到首次响应的时长中位数。",
     "MEDIAN(首次响应时间 − 工单创建时间)", "品质问题相关的客服工单", "客服组、标签", "客服工单系统", None, "小时", "越低越好",
     "—", "日更", "公开数据没有，待接入", "用中位数和 90 分位数，不用平均值"),
    ("IN606", "高风险商家整改完成率", "过程指标-待接入", "商家", "SP403",
     "进入高风险商家名单的商家中，30 天内完成整改、且下一次评估不再是高风险商家的商家所占的比例。",
     "整改完成的商家数 ÷ 应整改的商家数", "—", "下单月",
     "商家治理记录 + ads_seller_scorecard", None, "%", "越高越好", "—", "月更", "公开数据没有，待接入", "—"),
]

COLS = ["指标编码", "指标名称", "指标层级", "业务域", "父指标", "业务定义", "计算公式", "统计范围 / 过滤条件",
        "可下钻维度", "来源表", "口径 SQL（MySQL 8，可直接执行）", "单位", "方向", "目标 / 预警", "更新频率", "数据可得性",
        "易错点 / 注意事项"]
# 列序号（M 里每一行的字段位置）
I_SQL, I_UNIT, I_DIR, I_TARGET, I_AVAIL = 10, 11, 12, 13, 15


def compute_baselines():
    vals = []
    for m in M:
        sql = m[I_SQL]
        if sql is None:
            vals.append(None)
            continue
        v = query(sql).iloc[0, 0]
        vals.append(float(v) if v is not None else None)
    return vals


def fmt_value(v, unit):
    if v is None:
        return "—"
    if unit == "%":   # 数字格式见 docs/00_术语与口径.md 第 5 节
        return f"{v:.2%}"
    if unit in ("天", "分"):
        return f"{v:.2f}"
    if unit == "单/万单":
        return f"{v:.1f}"
    return f"{v:,.0f}"


DIMENSIONS = [
    ("下单月", "purchase_month / purchase_date", "下单月 / 下单日", "所有指标统一按下单时间归属，分子分母是同一批订单", "dwd_qc_order"),
    ("一级类目", "main_category_l1", "3C数码、家居家纺等 13 个，缺少品类信息的记为\"未知\"", "主品类所属的一级类目", "dim_category"),
    ("主品类", "main_category_cn", "73 个品类，缺少品类信息的记为\"未知品类\"", "主商品（订单中单价最高的商品）所属的品类", "dim_category"),
    ("主商家", "main_seller_id", "3,095 家", "主商品所属的商家；商家分层用商家签收订单（一个订单含多个商家时每个商家各计 1 单）",
     "dwd_qc_order / dwd_order_seller"),
    ("用户省份", "customer_state", "巴西 27 个州", "用户收货地址所在的州", "ods_customers"),
    ("订单结构", "item_cnt / sku_cnt / seller_cnt", "单件订单 / 同 SKU 多件 / 单商家多 SKU / 多商家", "由商品行汇总得到", "dwd_order"),
    ("主标签", "complaint_type", "假货、质量缺陷、货不对板、少件漏发、包装破损、未收到货、物流延迟、服务售后，以及未命中标签差评、无文字差评",
     "1-3 星评价按优先级取一个标签；只有 1-3 星才可能成为品质客诉订单", "dwd_review_tag + dim_complaint_rule"),
    ("商家分层", "risk_level", "正常 / 需关注 / 高风险", "按平滑品质客诉率与差评率判定（见高风险商家数）", "ads_seller_scorecard"),
]

CHANGELOG = [
    ("v0.1", "初版：评价文字命中品质关键词即记为品质客诉订单（不限星级）",
     "抽查发现 4-5 星评价里的\"sem defeito（没有瑕疵）\"\"não veio quebrado（没坏）\"被误判"),
    ("v0.2", "品质客诉订单限定 1-3 星；识别前剔除否定式表述（sem/nenhum/não veio + 缺陷词）",
     "4-5 星误判消除；1-3 星评价中命中质量缺陷标签的条数由 1,603 条变为 1,546 条"),
    ("v0.3", "\"外包装压扁、破损\"从质量缺陷中剥离，单独归为包装破损",
     "\"箱子破了但商品完好\"不再计入质量缺陷，避免高估商品质量问题"),
    ("v0.4", "按规则结果分层抽取 140 条评价（7 个标签 × 20 条）逐条复核，据判错的样本修正 8 条规则",
     "\"只收到部分商品\"原来被判为未收到货 → 增加规则，归入少件漏发"),
    ("v1.0", "口径冻结：按下单月归属、只统计签收订单、只取最后一次评价、主标签按优先级互斥",
     "看板、报告、专题分析都从订单宽表 dwd_qc_order 计算；数据校验全部通过。定版后用标注样本（随机 200 条）评估，"
     "同时得到标签精确率与标签召回率，见\"标签字典\"工作表"),
]


def write_excel(vals):
    wb = Workbook()
    font = "Microsoft YaHei"
    hfill = PatternFill("solid", fgColor="161418")        # 95 度黑
    hfont = Font(name=font, bold=True, color="FFFFFF", size=10)
    bfont = Font(name=font, size=10)
    thin = Side(style="thin", color="E9E6EA")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    wrap = Alignment(wrap_text=True, vertical="top")
    level_fill = {"核心指标": "FBD3E5", "结果指标": "FCE6F0", "体验指标": "F6F4F6", "过程指标": "FFFFFF"}

    def lv_fill(level):
        return PatternFill("solid", fgColor=level_fill.get(level.split("-")[0], "FFFFFF"))

    def header(ws, cols, widths):
        ws.append(cols)
        for i, w in enumerate(widths, 1):
            c = ws.cell(row=1, column=i)
            c.fill, c.font, c.border = hfill, hfont, border
            c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = "C2" if len(cols) > 6 else "A2"
        ws.row_dimensions[1].height = 30

    def body(ws):
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.font, c.alignment, c.border = bfont, wrap, border

    # ---- 说明
    ws = wb.active
    ws.title = "说明"
    notes = [
        ("品控数据分析项目 · 品控指标字典", None),
        ("版本", "v1.0（口径冻结）"),
        ("术语", "指标名称、定义、数字格式与 docs/00_术语与口径.md 完全一致"),
        ("生成日期", str(date.today())),
        ("数据来源", "Olist Brazilian E-Commerce Public Dataset（巴西真实电商平台脱敏数据，2016-09 ~ 2018-10，约 10 万订单）"),
        ("分析窗口", "下单月 2017-01 至 2018-08（首尾月份订单过少，已剔除）；本字典\"基准值\"= 下单月 2018-01 至 2018-08"),
        ("基准值来源", "由 scripts/09_metric_dictionary.py 逐条执行\"口径 SQL\"列得到，不是手填"),
        ("口径规则 1", "按下单月归属：一个订单的分子、分母都记在它的下单月，保证分子和分母是同一批订单"),
        ("口径规则 2", "签收订单：订单状态为已签收（delivered）且签收时间不为空"),
        ("口径规则 3", "只取最后一次评价：同一订单有多条评价时，只使用提交时间最晚的一条"),
        ("口径规则 4", "品质客诉订单：签收订单中，最后一次评价为 1-3 星且评价文字命中至少一个品质问题标签（假货、质量缺陷、货不对板、少件漏发、包装破损）"),
        ("口径规则 5", "一个订单可同时命中多个标签；需要互斥的结构占比时使用按优先级取的主标签"),
        ("口径规则 6", "汇总表只存订单数，比率只在最后一步计算，不对比率再求平均"),
        ("业务对应", "Olist 商家 ↔ 供应商或品牌方；用户评价 ↔ 客服与售后记录；平台规定发货时限 ↔ 供应商发货时效"),
        ("指标层级", "核心指标 → 结果指标 → 体验指标 → 过程指标（商品准入 / 商家管理 / 仓配履约 / 待接入）"),
        ("\"待接入\"指标", "入仓质检、退货、客服工单等内部数据在公开数据中没有；口径已定义，接入后即可上线"),
    ]
    for k, v in notes:
        ws.append([k, v])
    ws["A1"].font = Font(name=font, bold=True, size=14, color="E1006C")
    for r in range(2, len(notes) + 1):
        ws.cell(row=r, column=1).font = Font(name=font, bold=True, size=10)
        ws.cell(row=r, column=2).font = bfont
        ws.cell(row=r, column=2).alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 16
    ws.column_dimensions["B"].width = 110

    # ---- 指标体系（树）
    ws = wb.create_sheet("指标体系")
    header(ws, ["指标层级", "业务域", "指标编码", "指标名称", "父指标", "业务定义", "基准值（下单月 2018-01 至 2018-08）", "方向", "数据可得性"],
           [18, 10, 10, 22, 14, 70, 16, 10, 18])
    for m, v in zip(M, vals):
        ws.append([m[2], m[3], m[0], m[1], m[4], m[5], fmt_value(v, m[I_UNIT]) if v is not None else "—", m[I_DIR],
                   m[I_AVAIL]])
    body(ws)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.fill = lv_fill(row[0].value)
        if row[8].value != "已上线":
            for c in row:
                c.font = Font(name=font, size=10, color="8E8792", italic=True)
    ws.auto_filter.ref = ws.dimensions

    # ---- 指标字典（明细）
    ws = wb.create_sheet("指标字典")
    cols = COLS[:I_SQL + 1] + ["基准值（下单月 2018-01 至 2018-08）"] + COLS[I_SQL + 1:]
    header(ws, cols, [9, 18, 18, 8, 10, 42, 30, 34, 26, 22, 60, 16, 8, 9, 30, 11, 16, 46])
    for m, v in zip(M, vals):
        ws.append(list(m[:I_SQL + 1]) + [fmt_value(v, m[I_UNIT])] + list(m[I_SQL + 1:]))
    body(ws)
    for row in ws.iter_rows(min_row=2):
        row[I_SQL].font = Font(name="Consolas", size=9)
        for c in row[:2]:
            c.fill = lv_fill(row[2].value)
    ws.auto_filter.ref = ws.dimensions

    # ---- 维度字典
    ws = wb.create_sheet("维度字典")
    header(ws, ["维度", "字段", "取值 / 规模", "口径说明", "来源表"], [12, 30, 50, 46, 30])
    for d in DIMENSIONS:
        ws.append(list(d))
    body(ws)

    # ---- 标签字典（标签精确率 / 召回率来自标注样本：scripts/14_tag_gold_eval.py）
    rules = query("SELECT tag_code, tag_name, tag_group, priority FROM dim_complaint_rule ORDER BY priority")
    ge = json.loads((OUT_DIR / "qa" / "tag_gold_eval.json").read_text(encoding="utf-8"))["by_type"]
    ws = wb.create_sheet("标签字典")
    header(ws, ["标签编码", "标签", "标签分组", "主标签优先级", "是否计入品质客诉订单", "标签精确率（标注样本）",
                "标签召回率（标注样本）", "识别示例（葡语原文 → 含义）"],
           [14, 12, 12, 12, 14, 16, 16, 70])
    examples = {
        "fake": "\"recebi um produto falsificado\" → 收到假货", "defect": "\"veio com defeito, não liga\" → 有缺陷、开不了机",
        "mismatch": "\"recebi a cor errada\" → 颜色发错", "missing": "\"comprei 2 e recebi apenas 1\" → 买 2 件只到 1 件",
        "package": "\"caixa veio amassada e violada\" → 箱子压扁被拆", "not_received": "\"ainda não recebi o produto\" → 还没收到货",
        "delay": "\"entrega atrasada\" → 送货延迟", "service": "\"não consigo contato com a loja\" → 联系不上商家",
    }
    for _, r in rules.iterrows():
        g = ge.get(r.tag_name)   # 标注样本只评估 5 个品质问题标签
        pr = "—" if g is None or g["precision"] is None else f"{g['precision']:.1%}（{g['tp']}/{g['predicted']}）"
        rc = "—" if g is None or g["recall"] is None else f"{g['recall']:.1%}（{g['tp']}/{g['support']}）"
        ws.append([r.tag_code, r.tag_name, r.tag_group + "标签", int(r.priority), "是" if r.tag_group == "品质问题" else "否",
                   pr, rc, examples.get(r.tag_code, "")])
    body(ws)

    # ---- 口径变更记录
    ws = wb.create_sheet("口径变更记录")
    header(ws, ["版本", "变更内容", "变更原因 / 影响"], [8, 70, 70])
    for c in CHANGELOG:
        ws.append(list(c))
    body(ws)

    out = ROOT / "docs" / "品控指标字典.xlsx"
    wb.save(out)
    print(f"  → {out.relative_to(ROOT)}")


def facts():
    """模板 docs/_templates/02_指标体系.md.tpl 里除指标基准值以外的数字（全部从数据计算）。"""
    k = query("SELECT purchase_month m, bad_rate, on_time_rate FROM ads_qc_kpi_month").set_index("m").astype(float)
    ge = json.loads((OUT_DIR / "qa" / "tag_gold_eval.json").read_text(encoding="utf-8"))["any"]
    dq = (OUT_DIR / "qa" / "dq_report.md").read_text(encoding="utf-8")
    one = lambda sql: int(query(sql).iloc[0, 0])
    share = lambda v: f"{v * 100:.1f}%"
    qc2017 = float(query("""SELECT SUM(is_delivered * is_quality_complaint) / SUM(is_delivered) FROM dwd_qc_order
                            WHERE in_scope = 1 AND purchase_month <= '2017-12'""").iloc[0, 0])
    no_ts = one("""SELECT COUNT(*) FROM ods_orders WHERE order_status = 'delivered'
                   AND order_delivered_customer_date IS NULL""")
    return {
        "BAD_1803": share(k.loc["2018-03", "bad_rate"]), "OT_1803": share(k.loc["2018-03", "on_time_rate"]),
        "BAD_1804": share(k.loc["2018-04", "bad_rate"]), "OT_1804": share(k.loc["2018-04", "on_time_rate"]),
        "QC2017": f"{qc2017 * 100:.2f}%", "NO_TS": f"{no_ts:,}",
        "MULTI_REVIEW": f"{one('SELECT COUNT(DISTINCT order_id) FROM dwd_review WHERE dup_cnt > 1'):,}",
        "DQ_N": str(dq.count("✅ PASS") + dq.count("❌ FAIL")),
        "GOLD_P": share(ge["precision"]), "GOLD_R": share(ge["recall"]),
        "N_METRIC": str(len(M)), "N_LIVE": str(sum(m[I_AVAIL] == "已上线" for m in M)),
        "N_TODO": str(sum(m[I_AVAIL] != "已上线" for m in M)),
    }


def write_markdown(vals):
    lines = []
    cur_level = None
    for m, v in zip(M, vals):
        if m[2] != cur_level:
            cur_level = m[2]
            lines += [f"\n### {cur_level}\n", "| 编码 | 指标 | 定义 | 公式 | 基准值 | 目标 / 预警 |", "|---|---|---|---|---|---|"]
        lines.append(f"| {m[0]} | **{m[1]}** | {m[5]} | {m[6]} | {fmt_value(v, m[I_UNIT])} | {m[I_TARGET]} |")
    return "\n".join(lines)


if __name__ == "__main__":
    vals = compute_baselines()
    for m, v in zip(M, vals):
        print(f"  {m[0]} {m[1]:<14} {fmt_value(v, m[I_UNIT])}")
    write_excel(vals)
    tpl = (ROOT / "docs" / "_templates" / "02_指标体系.md.tpl").read_text(encoding="utf-8")
    doc = tpl.replace("{{METRIC_TABLE}}", write_markdown(vals))
    for m, v in zip(M, vals):
        doc = doc.replace("{" + m[0] + "}", fmt_value(v, m[I_UNIT]))
    for k, v in facts().items():
        doc = doc.replace("{" + k + "}", v)
    assert "{" not in doc.replace("{{", "").split("```mermaid")[0], "模板里还有未填充的占位符"
    (ROOT / "docs" / "02_指标体系.md").write_text(doc, encoding="utf-8")
    print("  → docs/02_指标体系.md")
