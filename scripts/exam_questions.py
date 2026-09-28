"""SQL 笔试模拟卷（45 分钟，100 分）：6 道新题，不与题库 Q01-Q19 重复。

字段：id / title / level / minutes / score / ask（业务原话）/ tables（用到的表）/ output（输出要求）
      rubric [(分值, 评分点)] / sql（参考答案）/ check（自检，返回 ok、note）/ wrong / wrong_note（常见扣分写法）
      conclusion（开放题的参考结论）
全部在 MySQL 面试库 qc_interview 上由 scripts/17_mock_exam.py 实跑。
"""
from interview_questions import QC, RV

DELIVERED = "o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL"

E = []


def _same_yoy(ans, chk):
    a = ans[ans.month == "2018-03"].set_index("category_l1")
    c = chk.set_index("category_l1")
    ok = all(abs(float(a.qc_rate[k]) - float(c.r18[k])) < 1e-9
             and (c.r17[k] is None and a.qc_rate_ly[k] is None or abs(float(a.qc_rate_ly[k]) - float(c.r17[k])) < 1e-9)
             for k in c.index)
    return ok, f"独立验算 2018-03 与 2017-03 的 {len(c)} 个一级类目（直接按日期过滤，不用月份关联），与答案逐项一致"


def _same_roll(ans, chk):
    row = ans[ans.d.astype(str) == "2018-07-31"].iloc[0]
    n, x = int(chk.n.iloc[0]), int(chk.x.iloc[0])
    ok = int(row.delivered_30d) == n and int(row.qc_30d) == x
    return ok, f"独立验算 2018-07-31：直接过滤 07-02 ~ 07-31 下单的签收订单 {n:,} 单、品质客诉 {x} 单，与滚动结果一致"

E.append(dict(
    id="E1", level="基础", minutes=5, score=10, title="商家平均评分排行",
    ask="拉一下 2018 年 3-8 月各商家的签收订单数和平均评分，签收不到 50 单的不要，按平均分从低到高给我前 10 个，商家运营要约谈。",
    tables="orders、order_items、order_reviews",
    output="seller_id, delivered_cnt, reviewed_cnt, avg_score（保留 2 位）",
    rubric=[(3, "评价按订单去重（每单只取最后一次评价）"),
            (3, "订单 × 商家先去重再计数：一单买同一商家 3 件只算 1 单，平均分不能按商品行加权"),
            (2, "签收口径 + 下单时间半开区间"),
            (2, "没评价的订单计入签收订单、不计入平均分（LEFT JOIN + AVG 忽略 NULL）；HAVING 门槛与排序正确")],
    sql=f"""WITH {RV},
so AS (   -- 签收订单 × 商家（同单同商家多件去重）
    SELECT DISTINCT o.order_id, oi.seller_id
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE {DELIVERED}
      AND o.order_purchase_timestamp >= '2018-03-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
)
SELECT so.seller_id,
       COUNT(*)                       AS delivered_cnt,
       COUNT(rv.review_score)         AS reviewed_cnt,
       ROUND(AVG(rv.review_score), 2) AS avg_score
FROM so
LEFT JOIN rv ON rv.order_id = so.order_id
GROUP BY so.seller_id
HAVING COUNT(*) >= 50
ORDER BY avg_score, delivered_cnt DESC
LIMIT 10""",
    check="""SELECT COUNT(*) = COUNT(DISTINCT order_id, seller_id) AS ok,
       CONCAT('订单 × 商家粒度唯一：', COUNT(*), ' 行') AS note
FROM (SELECT DISTINCT o.order_id, oi.seller_id FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
      WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
        AND o.order_purchase_timestamp >= '2018-03-01' AND o.order_purchase_timestamp < '2018-09-01') t""",
    wrong="""SELECT oi.seller_id, COUNT(*) AS delivered_cnt, ROUND(AVG(r.review_score), 2) AS avg_score
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN order_reviews r ON r.order_id = o.order_id
WHERE o.order_status = 'delivered'
  AND o.order_purchase_timestamp BETWEEN '2018-03-01' AND '2018-08-31'
GROUP BY oi.seller_id
HAVING COUNT(*) >= 50
ORDER BY avg_score
LIMIT 10""",
    wrong_note="三处扣分：直接 JOIN 商品行和评价表，多件订单、重复评价都会放大 COUNT(*)，平均分被多件订单加权；"
               "`BETWEEN ... '2018-08-31'` 漏掉 8 月 31 日白天的订单；INNER JOIN 评价表把没评价的订单从签收订单里丢掉了。",
))

E.append(dict(
    id="E2", level="基础", minutes=5, score=10, title="商品主数据完整性核查",
    ask="商品主数据质量怎么样？统计缺品类、缺重量、缺图片的商品各有多少个、占多少，以及 2018 年 1-8 月的签收订单里有多少单涉及这些商品。",
    tables="products、orders、order_items",
    output="issue（缺品类 / 缺重量 / 缺图片 / 任一缺失）, product_cnt, product_share, delivered_orders",
    rubric=[(3, "缺图片 = 图片数为 NULL 或 0（只写 `= 0` 会漏掉 NULL）"),
            (3, "一个商品可能同时缺多项，\"任一缺失\"要去重，不能三项相加"),
            (2, "涉及订单数用 COUNT(DISTINCT order_id)"),
            (2, "占比分母是全部商品数；输出行完整")],
    sql=f"""WITH p AS (
    SELECT product_id,
           product_category_name IS NULL          AS no_cat,
           product_weight_g IS NULL               AS no_weight,
           COALESCE(product_photos_qty, 0) = 0    AS no_photo
    FROM products
),
x AS (   -- 一个商品缺几项就出现几行；\"任一缺失\"单独一行
    SELECT '1 缺品类' AS issue, product_id FROM p WHERE no_cat
    UNION ALL SELECT '2 缺重量', product_id FROM p WHERE no_weight
    UNION ALL SELECT '3 缺图片', product_id FROM p WHERE no_photo
    UNION ALL SELECT '4 任一缺失', product_id FROM p WHERE no_cat OR no_weight OR no_photo
),
d AS (   -- 2018 年 1-8 月签收订单涉及的商品
    SELECT DISTINCT oi.order_id, oi.product_id
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE {DELIVERED}
      AND o.order_purchase_timestamp >= '2018-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
)
SELECT x.issue,
       COUNT(DISTINCT x.product_id)                                            AS product_cnt,
       ROUND(COUNT(DISTINCT x.product_id) / (SELECT COUNT(*) FROM products), 4) AS product_share,
       COUNT(DISTINCT d.order_id)                                              AS delivered_orders
FROM x
LEFT JOIN d ON d.product_id = x.product_id
GROUP BY x.issue
ORDER BY x.issue""",
    check="""SELECT SUM(product_photos_qty IS NULL) = SUM(COALESCE(product_photos_qty, 0) = 0) AS ok,
       CONCAT('图片数为 NULL 的 ', SUM(product_photos_qty IS NULL), ' 个，为 0 的 ', SUM(product_photos_qty = 0),
              ' 个：只写 = 0 会一个都查不到') AS note
FROM products""",
    wrong="""SELECT '缺图片' AS issue, COUNT(*) AS product_cnt
FROM products
WHERE product_photos_qty = 0""",
    wrong_note="这份数据里缺图片的商品全部是 NULL，没有 0。`= 0` 对 NULL 返回 NULL，被 WHERE 过滤掉，结果是 0 个，看起来\"数据很干净\"。",
))

E.append(dict(
    id="E3", level="进阶", minutes=10, score=20, title="一级类目品质客诉率同比",
    ask="各一级类目 2018 年 1-8 月每个月的品质客诉率，和去年同月比变化了多少？变差超过 1 个百分点的标出来。",
    tables="orders、order_items、products、category_dim、order_reviews、review_tags",
    output="category_l1, month, delivered_cnt, qc_rate, qc_rate_ly（去年同月）, yoy_pp（百分点）, flag",
    rubric=[(4, "品质客诉口径正确：评价去重、1-3 星、命中 5 类品质标签任一"),
            (4, "订单 × 一级类目去重（一单跨两个类目各算一次，同类目多件只算一次）"),
            (5, "同比按\"月份 − 12 个月\"精确关联；用 `LAG(..., 12)` 只有在每个类目每个月都有数据时才对"),
            (4, "比率先在各自月份算好再相减；百分点与百分比分清"),
            (3, "标记逻辑正确；提示小样本月份（加分项：给出签收订单数供判断）")],
    sql=f"""WITH {RV},
{QC},
ol AS (   -- 签收订单 × 一级类目
    SELECT DISTINCT o.order_id, c.category_l1, DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS month
    FROM orders o
    JOIN order_items  oi ON oi.order_id = o.order_id
    JOIN products     p  ON p.product_id = oi.product_id
    JOIN category_dim c  ON c.product_category_name = p.product_category_name
    WHERE {DELIVERED}
      AND o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
),
m AS (
    SELECT ol.category_l1, ol.month, COUNT(*) AS delivered_cnt, COUNT(q.order_id) / COUNT(*) AS qc_rate
    FROM ol
    LEFT JOIN qc q ON q.order_id = ol.order_id
    GROUP BY ol.category_l1, ol.month
)
SELECT cur.category_l1, cur.month, cur.delivered_cnt,
       ROUND(cur.qc_rate, 4)                     AS qc_rate,
       ROUND(ly.qc_rate, 4)                      AS qc_rate_ly,
       ROUND((cur.qc_rate - ly.qc_rate) * 100, 2) AS yoy_pp,
       CASE WHEN cur.qc_rate - ly.qc_rate > 0.01 THEN '变差' ELSE '' END AS flag
FROM m cur
LEFT JOIN m ly
  ON ly.category_l1 = cur.category_l1
 AND ly.month = DATE_FORMAT(STR_TO_DATE(CONCAT(cur.month, '-01'), '%Y-%m-%d') - INTERVAL 1 YEAR, '%Y-%m')
WHERE cur.month >= '2018-01'
ORDER BY cur.category_l1, cur.month""",
    check=f"""WITH {RV},
{QC},
ol AS (   -- 独立验算：不用月份关联，直接过滤 2017-03 与 2018-03
    SELECT DISTINCT o.order_id, c.category_l1, YEAR(o.order_purchase_timestamp) AS y
    FROM orders o
    JOIN order_items  oi ON oi.order_id = o.order_id
    JOIN products     p  ON p.product_id = oi.product_id
    JOIN category_dim c  ON c.product_category_name = p.product_category_name
    WHERE {DELIVERED}
      AND ((o.order_purchase_timestamp >= '2017-03-01' AND o.order_purchase_timestamp < '2017-04-01')
        OR (o.order_purchase_timestamp >= '2018-03-01' AND o.order_purchase_timestamp < '2018-04-01'))
)
SELECT ol.category_l1,
       ROUND(SUM(ol.y = 2018 AND q.order_id IS NOT NULL) / SUM(ol.y = 2018), 4) AS r18,
       ROUND(SUM(ol.y = 2017 AND q.order_id IS NOT NULL) / SUM(ol.y = 2017), 4) AS r17
FROM ol
LEFT JOIN qc q ON q.order_id = ol.order_id
GROUP BY ol.category_l1""",
    answer_assert=lambda ans, chk: _same_yoy(ans, chk),
    wrong=f"""WITH oc AS (   -- 同样的 LAG(12) 写法，换到品类（category_cn）粒度
    SELECT DISTINCT o.order_id, c.category_cn, DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS month
    FROM orders o
    JOIN order_items  oi ON oi.order_id = o.order_id
    JOIN products     p  ON p.product_id = oi.product_id
    JOIN category_dim c  ON c.product_category_name = p.product_category_name
    WHERE {DELIVERED}
      AND o.order_purchase_timestamp >= '2017-01-01' AND o.order_purchase_timestamp < '2018-09-01'
),
m AS (
    SELECT category_cn, month, COUNT(*) AS delivered_cnt FROM oc GROUP BY category_cn, month
),
w AS (
    SELECT m.*, LAG(month, 12) OVER (PARTITION BY category_cn ORDER BY month) AS lag12_month
    FROM m
)
SELECT category_cn, month, lag12_month, delivered_cnt
FROM w
WHERE month >= '2018-01'
  AND lag12_month IS NOT NULL
  AND lag12_month <> DATE_FORMAT(STR_TO_DATE(CONCAT(month, '-01'), '%Y-%m-%d') - INTERVAL 1 YEAR, '%Y-%m')
ORDER BY category_cn, month""",
    wrong_note="用 `LAG(qc_rate, 12)` 取去年同月，前提是每个分组每个月都有数据。一级类目粒度上这份数据恰好每月都有签收订单，所以 LAG 碰巧取对了；"
               "换到品类粒度，小品类有缺月，往前数 12 行就不是去年同月了。上表是品类粒度上实跑出来的错位行：`lag12_month` 是 LAG 取到的月份，"
               "本应是 `month` 减一年。这类错误不报错，数字看起来也合理，只能靠按月份精确关联来避免。",
))

E.append(dict(
    id="E4", level="进阶", minutes=10, score=20, title="品质客诉订单最多的商家，各自的问题商品",
    ask="2018 年 3-8 月品质客诉订单最多的 5 家商家（并列的一起给），每家把品质客诉订单最多的 2 个商品列出来，并列的都要，附上商品的签收订单数和品质客诉订单数，我拿去跟商家对。",
    tables="orders、order_items、order_reviews、review_tags",
    output="seller_rank, seller_id, seller_qc, product_id, product_qc, product_delivered, product_qc_rate, product_rank",
    rubric=[(4, "品质客诉口径正确（同 E3）"),
            (5, "商家的品质客诉订单数按订单去重计算，不能把商品粒度的品质客诉订单数相加（一个订单含多个商品时会重复）"),
            (5, "两次排名都用 DENSE_RANK / RANK 处理并列，ROW_NUMBER 会随机丢掉并列项"),
            (3, "商品粒度：签收订单 × 商品去重（同单同商品多件只算 1 单）"),
            (3, "输出排序清晰，附上分母（签收订单数）")],
    sql=f"""WITH {RV},
{QC},
sp AS (   -- 签收订单 × 商家 × 商品（同单同商品多件去重）
    SELECT DISTINCT o.order_id, oi.seller_id, oi.product_id
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE {DELIVERED}
      AND o.order_purchase_timestamp >= '2018-03-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
),
ps AS (   -- 商品粒度
    SELECT sp.seller_id, sp.product_id, COUNT(*) AS product_delivered, COUNT(q.order_id) AS product_qc
    FROM sp
    LEFT JOIN qc q ON q.order_id = sp.order_id
    GROUP BY sp.seller_id, sp.product_id
),
ss AS (   -- 商家粒度：按订单去重，不能用商品粒度相加
    SELECT sp.seller_id, COUNT(DISTINCT q.order_id) AS seller_qc
    FROM sp
    JOIN qc q ON q.order_id = sp.order_id
    GROUP BY sp.seller_id
),
ts AS (
    SELECT seller_id, seller_qc, DENSE_RANK() OVER (ORDER BY seller_qc DESC) AS seller_rank
    FROM ss
),
tp AS (
    SELECT ps.*, DENSE_RANK() OVER (PARTITION BY ps.seller_id ORDER BY ps.product_qc DESC) AS product_rank
    FROM ps
    WHERE ps.product_qc > 0
)
SELECT ts.seller_rank, ts.seller_id, ts.seller_qc,
       tp.product_id, tp.product_qc, tp.product_delivered,
       ROUND(tp.product_qc / tp.product_delivered, 4) AS product_qc_rate,
       tp.product_rank
FROM ts
JOIN tp ON tp.seller_id = ts.seller_id
WHERE ts.seller_rank <= 5 AND tp.product_rank <= 2
ORDER BY ts.seller_rank, tp.product_rank, tp.product_delivered DESC, tp.product_id""",
    check=f"""WITH {RV},
{QC},
sp AS (
    SELECT DISTINCT o.order_id, oi.seller_id, oi.product_id
    FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
    WHERE {DELIVERED} AND o.order_purchase_timestamp >= '2018-03-01' AND o.order_purchase_timestamp < '2018-09-01'
),
a AS (SELECT sp.seller_id, COUNT(DISTINCT q.order_id) AS by_order, COUNT(*) AS by_product
      FROM sp JOIN qc q ON q.order_id = sp.order_id GROUP BY sp.seller_id)
SELECT SUM(by_product > by_order) > 0 AS ok,
       CONCAT(SUM(by_product > by_order), ' 家商家如果把商品粒度的品质客诉订单数相加会多算（最多多算 ',
              MAX(by_product - by_order), ' 单）：商家的品质客诉订单数必须按订单去重') AS note
FROM a""",
))

E.append(dict(
    id="E5", level="高阶", minutes=10, score=25, title="滚动 30 天品质客诉率（日报）",
    ask="品控日报想加一个「近 30 天品质客诉率」，每天看一次。先回溯 2018 年 6 月 1 日到 8 月 31 日每天的值给我看看。",
    tables="orders、order_reviews、review_tags",
    output="d（日期）, delivered_30d, qc_30d, qc_rate_30d；每天一行",
    rubric=[(5, "口径：近 30 天 = 下单日期在 [d − 29, d]，含当天，共 30 天"),
            (6, "先按天聚合出分子、分母，再滚动求和后相除；不能对每天的比率求平均"),
            (6, "用日历表补齐日期（递归 CTE），窗口按行滚动才等于按天滚动；或用 RANGE INTERVAL"),
            (4, "日历要从 5 月 3 日开始，保证 6 月 1 日的窗口是完整的 30 天"),
            (4, "自检：抽一天，用直接过滤 30 天区间的方式算一遍，结果一致")],
    sql=f"""WITH RECURSIVE cal AS (   -- 日历：比输出起点再往前 29 天
    SELECT DATE('2018-05-03') AS d
    UNION ALL
    SELECT d + INTERVAL 1 DAY FROM cal WHERE d < '2018-08-31'
),
{RV},
{QC},
daily AS (   -- 先按天聚合计数
    SELECT DATE(o.order_purchase_timestamp) AS d, COUNT(*) AS delivered_cnt, COUNT(q.order_id) AS qc_cnt
    FROM orders o
    LEFT JOIN qc q ON q.order_id = o.order_id
    WHERE {DELIVERED}
      AND o.order_purchase_timestamp >= '2018-05-03'
      AND o.order_purchase_timestamp <  '2018-09-01'
    GROUP BY DATE(o.order_purchase_timestamp)
),
filled AS (   -- 没有订单的日子补 0，保证\"一行 = 一天\"
    SELECT cal.d, COALESCE(daily.delivered_cnt, 0) AS delivered_cnt, COALESCE(daily.qc_cnt, 0) AS qc_cnt
    FROM cal
    LEFT JOIN daily ON daily.d = cal.d
),
roll AS (
    SELECT d,
           SUM(delivered_cnt) OVER w AS delivered_30d,
           SUM(qc_cnt)        OVER w AS qc_30d
    FROM filled
    WINDOW w AS (ORDER BY d ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)
)
SELECT d, delivered_30d, qc_30d, ROUND(qc_30d / delivered_30d, 4) AS qc_rate_30d
FROM roll
WHERE d >= '2018-06-01'
ORDER BY d""",
    check=f"""WITH {RV},
{QC}
SELECT COUNT(*) AS n, COUNT(q.order_id) AS x   -- 独立验算：直接过滤 2018-07-02 ~ 2018-07-31 下单的签收订单
FROM orders o
LEFT JOIN qc q ON q.order_id = o.order_id
WHERE {DELIVERED}
  AND o.order_purchase_timestamp >= '2018-07-02' AND o.order_purchase_timestamp < '2018-08-01'""",
    answer_assert=lambda ans, chk: _same_roll(ans, chk),
    wrong=f"""WITH {RV},
{QC},
daily AS (
    SELECT DATE(o.order_purchase_timestamp) AS d, COUNT(*) AS n, COUNT(q.order_id) / COUNT(*) AS qc_rate
    FROM orders o
    LEFT JOIN qc q ON q.order_id = o.order_id
    WHERE {DELIVERED}
      AND o.order_purchase_timestamp >= '2018-05-03' AND o.order_purchase_timestamp < '2018-09-01'
    GROUP BY DATE(o.order_purchase_timestamp)
),
w AS (   -- ❌ 对每天的比率求平均
    SELECT d, n, AVG(qc_rate) OVER (ORDER BY d ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS avg_rate
    FROM daily
)
SELECT d, n AS delivered_that_day, ROUND(avg_rate, 4) AS qc_rate_30d_wrong
FROM w
WHERE d >= '2018-08-25'
ORDER BY d""",
    wrong_compare=("d", "qc_rate_30d", "qc_rate_30d_wrong"),
    wrong_note="对每天的比率求平均：单量小的日子和单量大的日子权重一样。数据集在 8 月底接近截止，每天的签收订单从六七十单掉到十几单，"
               "这些小样本日子的比率波动大，却和大样本日子等权平均：上表 8 月 29 日当天只有 11 单，错误写法比正确写法高出约 0.5 个百分点。"
               "另外没有补日历时，`ROWS 29 PRECEDING` 在缺天的地方会跨过 30 天。",
))

E.append(dict(
    id="E6", level="开放", minutes=5, score=15, title="8 月降了，是品控见效了吗",
    ask="8 月品质客诉率 4.4%，比 7 月的 5.0% 降了不少，是不是品控措施见效了？你用数据回答我。",
    tables="orders、order_reviews、review_tags",
    output="自定。参考：月份、签收订单、评价回收率、品质客诉率、签收后 7 天内的品质客诉率、与上月比较的 z 值",
    rubric=[(4, "先怀疑数据假象：最近月份的评价是否收全（评价回收率）、是否要用同等观察期比较"),
            (4, "做显著性判断：两个比例的 z 检验，或与控制限比较"),
            (4, "给出结论和边界：回落是真实的但不显著，不能归因于举措（没有对照组、也没有上线时间点）"),
            (3, "提出下一步：再观察 1-2 个月；如果真有举措，用试点 + 对照组评估")],
    sql=f"""WITH {RV},
b AS (
    SELECT DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS month,
           o.order_delivered_customer_date                 AS delivered_at,
           rv.review_id,
           rv.review_answer_timestamp                      AS answered_at,
           COALESCE(rv.review_score <= 3
                    AND tg.is_fake + tg.is_defect + tg.is_mismatch + tg.is_missing + tg.is_package > 0, 0) AS is_qc
    FROM orders o
    LEFT JOIN rv ON rv.order_id = o.order_id
    LEFT JOIN review_tags tg ON tg.review_id = rv.review_id AND tg.order_id = rv.order_id
    WHERE {DELIVERED}
      AND o.order_purchase_timestamp >= '2018-05-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
),
m AS (
    SELECT month,
           COUNT(*)                                                    AS n,
           AVG(review_id IS NOT NULL)                                  AS review_rate,
           SUM(is_qc)                                                  AS x,
           SUM(is_qc = 1 AND answered_at < delivered_at + INTERVAL 7 DAY) AS x7   -- 同等观察期：签收后 7 天内的评价
    FROM b
    GROUP BY month
),
t AS (
    SELECT m.*, LAG(n) OVER (ORDER BY month) AS n0, LAG(x) OVER (ORDER BY month) AS x0
    FROM m
)
SELECT month,
       n                        AS delivered_cnt,
       ROUND(review_rate, 4)    AS review_rate,
       ROUND(x / n, 4)          AS qc_rate,
       ROUND(x7 / n, 4)         AS qc_rate_7d,
       ROUND((CAST(x AS DOUBLE) / n - CAST(x0 AS DOUBLE) / n0)
             / SQRT(CAST(x + x0 AS DOUBLE) / (n + n0) * (1 - CAST(x + x0 AS DOUBLE) / (n + n0)) * (1 / n + 1 / n0)), 2) AS z_vs_prev
FROM t
ORDER BY month""",
    check=f"""WITH {RV}
SELECT ROUND(AVG(rv.review_id IS NOT NULL), 3) >= 0.99 AS ok,
       CONCAT('8 月签收订单的评价回收率 ', ROUND(AVG(rv.review_id IS NOT NULL) * 100, 1), '%：不是\"评价还没收回来\"') AS note
FROM orders o LEFT JOIN rv ON rv.order_id = o.order_id
WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_purchase_timestamp >= '2018-08-01' AND o.order_purchase_timestamp < '2018-09-01'""",
    conclusion=[
        "**先排除数据假象**：8 月签收订单的评价回收率与 7 月相当（都在 99% 以上），只看签收后 7 天内提交的评价，8 月仍低于 7 月。所以回落不是\"评价还没收回来\"造成的，是真实发生的。",
        "**再看是不是波动**：8 月与 7 月比 |z| < 1.96，在 5% 水平上不显著；8 月的值也还在控制图的控制限内（中心线 = 2017 年品质客诉率）。",
        "**不能归因于措施**：这段时间没有任何可以对应的举措上线时间点，也没有对照组。即使有举措，也要看试点组相对对照组的变化（双重差分），而不是前后对比。",
        "**给业务的回答**：\"8 月确实回落了，但幅度还在正常波动范围内，现在说见效为时过早；建议再看 9、10 月，如果有具体举措，告诉我上线时间和范围，我按试点 / 对照来评估。\"",
    ],
))
