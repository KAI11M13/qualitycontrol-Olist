"""SQL 面试题库（场景：响应品控业务方的临时取数需求）。

每道题的字段
  id / title / level      编号、标题、难度（基础 / 进阶 / 高阶 / 开放）
  points                  考点
  ask                     业务方原话（"业务语言"）
  caliber                 口径拆解（翻译成"数据需求"）
  assume                  默认假设（交付时写明，业务方可纠正）
  logic                   思路
  sql                     参考答案（MySQL 8.0，面试库 qc_interview 上可直接执行）
  check                   自检 SQL，返回 ok 列（1 = 通过）和说明列
  cross                   可选：与项目数仓已有报表对账（跨库），返回 ok 列
  wrong / wrong_note      可选：常见错误写法及其错误结果
  pitfalls                易错点
  followups               面试官追问
所有 SQL 都由 scripts/11_build_interview.py 实际执行，结果写入 docs/05_SQL面试题库.md。
"""

# ------------------------------------------------------------------ 复用的 CTE 片段
RV = """rv AS (   -- 每单只留用户最后一次提交的评价
    SELECT order_id, review_id, review_score, review_answer_timestamp,
           review_comment_title, review_comment_message
    FROM (
        SELECT r.*,
               ROW_NUMBER() OVER (PARTITION BY order_id
                                  ORDER BY review_answer_timestamp DESC, review_id DESC) AS rn
        FROM order_reviews r
    ) t
    WHERE rn = 1
)"""

QC = """qc AS (   -- 最后一次评价 1-3 星且命中任一品质问题标签的订单（再限定签收订单，就是品质客诉订单）
    SELECT rv.order_id, rv.review_answer_timestamp
    FROM rv
    JOIN review_tags tg ON tg.review_id = rv.review_id AND tg.order_id = rv.order_id
    WHERE rv.review_score <= 3
      AND tg.is_fake + tg.is_defect + tg.is_mismatch + tg.is_missing + tg.is_package > 0
)"""

DELIVERED = "o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL"

Q = []

# =================================================================== 基础
Q.append(dict(
    id="Q01", level="基础", title="月度订单概览：下单、签收、准时签收率",
    points=["条件聚合 SUM(条件)", "半开区间取数", "NULLIF 防除零"],
    ask="帮我拉一下 2018 年每个月的下单订单数、签收订单数、签收率和准时签收率，周会要用。",
    caliber=["下单订单数 = 按下单时间落月的订单数", "签收订单 = 状态为 delivered 且签收时间不为空的订单",
             "签收率 = 签收订单数 ÷ 下单订单数", "准时签收率 = 签收日期不晚于承诺送达日期的签收订单数 ÷ 签收订单数",
             "时间 = 下单时间 ∈ [2018-01-01, 2018-09-01)"],
    assume=["\"2018 年\"按数据截止取到 8 月（9 月以后只有零星订单）", "承诺送达时间只有日期部分，按自然日比较"],
    logic=["按月分组", "用 SUM(布尔表达式) 一次算出多个计数", "比率分母加 NULLIF"],
    sql="""SELECT
    DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m')                              AS month,
    COUNT(*)                                                                      AS order_cnt,
    SUM(o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL) AS delivered_cnt,
    ROUND(SUM(o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL)
          / COUNT(*), 4)                                                          AS delivered_rate,
    ROUND(SUM(o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
              AND DATE(o.order_delivered_customer_date) <= DATE(o.order_estimated_delivery_date))
          / NULLIF(SUM(o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL), 0), 4)
                                                                                  AS on_time_rate
FROM orders o
WHERE o.order_purchase_timestamp >= '2018-01-01'
  AND o.order_purchase_timestamp <  '2018-09-01'
GROUP BY month
ORDER BY month;""",
    check="""SELECT
    (SELECT SUM(cnt) FROM (SELECT COUNT(*) cnt FROM orders
        WHERE order_purchase_timestamp >= '2018-01-01' AND order_purchase_timestamp < '2018-09-01'
        GROUP BY DATE_FORMAT(order_purchase_timestamp, '%Y-%m')) t)
  = (SELECT COUNT(*) FROM orders
        WHERE order_purchase_timestamp >= '2018-01-01' AND order_purchase_timestamp < '2018-09-01') AS ok,
    '各月订单数之和 = 区间总订单数' AS note;""",
    cross="""SELECT MAX(ABS(a.on_time_rate - k.on_time_rate)) < 0.0001 AS ok, '准时签收率与数仓 ads_qc_kpi_month 逐月一致' AS note
FROM (
    SELECT DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS m,
           1 - SUM(order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL
                   AND DATE(order_delivered_customer_date) > DATE(order_estimated_delivery_date))
             / SUM(order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL) AS on_time_rate
    FROM qc_interview.orders
    WHERE order_purchase_timestamp >= '2018-01-01' AND order_purchase_timestamp < '2018-09-01'
    GROUP BY m) a
JOIN qc_dw.ads_qc_kpi_month k ON k.purchase_month = a.m;""",
    wrong="""-- ❌ 用 BETWEEN 写日期：'2018-08-31' 会被当成 2018-08-31 00:00:00，当天的订单全部丢失
SELECT COUNT(*) AS order_cnt_between,
       (SELECT COUNT(*) FROM orders
         WHERE order_purchase_timestamp >= '2018-01-01' AND order_purchase_timestamp < '2018-09-01') AS order_cnt_correct
FROM orders
WHERE order_purchase_timestamp BETWEEN '2018-01-01' AND '2018-08-31';""",
    wrong_note="这份数据 8 月 31 日只有 1 单，所以只差 1 单；换成日报或者大促当天，就是整天的数据丢失。",
    pitfalls=["DATETIME 字段用 BETWEEN 截止日会漏掉最后一天 00:00:00 之后的数据，一律用半开区间",
              "准时签收率的分母是签收订单，不是下单量",
              "状态为 delivered 但签收时间为空的 8 单，要么剔除要么单独说明，不能默认当作准时"],
    followups=["如果周会要看\"周\"而不是\"月\"，周一作为一周开始怎么写？（YEARWEEK(dt, 3) 或 dt - INTERVAL WEEKDAY(dt) DAY）",
               "签收率在最近一个月偏低，是业务变差了吗？（右删失：最近下单的订单还没来得及签收）"],
))

Q.append(dict(
    id="Q02", level="基础", title="评价去重：每单只保留最后一次评价",
    points=["ROW_NUMBER() 组内排序取第一", "排序键加唯一键兜底", "COUNT() OVER 统计重复"],
    ask="评价表好像有重复，同一个订单有好几条评价。帮我每单只留一条，留用户最后提交的那条；顺便告诉我有多少单是重复的。",
    caliber=["去重粒度 = 订单", "保留规则 = review_answer_timestamp 最新；时间相同时按 review_id 倒序兜底",
             "输出 = 有评价订单数、重复订单数、被删掉的行数"],
    assume=["\"最后提交\"指用户提交评价的时间（review_answer_timestamp），不是问卷发送时间"],
    logic=["ROW_NUMBER 按订单分组、按提交时间倒序", "COUNT(*) OVER 同时拿到每单评价条数", "外层取 rn = 1 并汇总"],
    sql="""WITH ranked AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (PARTITION BY order_id
                           ORDER BY review_answer_timestamp DESC, review_id DESC) AS rn,
        COUNT(*)     OVER (PARTITION BY order_id)                                 AS review_cnt
    FROM order_reviews r
)
SELECT
    COUNT(*)                       AS orders_with_review,
    SUM(review_cnt > 1)            AS dup_orders,
    SUM(review_cnt) - COUNT(*)     AS removed_rows,
    (SELECT COUNT(*) FROM order_reviews) AS raw_rows
FROM ranked
WHERE rn = 1;""",
    check="""SELECT COUNT(*) = COUNT(DISTINCT order_id) AS ok, '去重后 order_id 唯一' AS note
FROM (SELECT order_id, ROW_NUMBER() OVER (PARTITION BY order_id
      ORDER BY review_answer_timestamp DESC, review_id DESC) rn FROM order_reviews) t
WHERE rn = 1;""",
    cross="""SELECT (SELECT COUNT(*) FROM qc_dw.dwd_review) = 98673 AS ok, '与数仓 dwd_review 行数一致（98,673）' AS note;""",
    pitfalls=["ORDER BY 只写时间不加唯一键时，同一时间的两条评价谁排第一不确定，每次跑结果可能不同",
              "不能用 GROUP BY order_id + MAX(review_score)——那样拿到的是\"最高分\"，不是\"最后一次\"的分",
              "review_id 本身也不唯一（789 个 review_id 对应多个订单），不能按 review_id 去重"],
    followups=["如果是 MySQL 5.7 没有窗口函数，怎么写？（NOT EXISTS 找不到比它更晚的评价）",
               "去重规则应该由谁定？（写进指标字典的口径约定，并通知所有用这张表的人）"],
))

Q.append(dict(
    id="Q03", level="基础", title="差评率最高的 10 个品类",
    points=["多表关联", "一对多关联前先去重", "HAVING 过滤小样本"],
    ask="哪些品类差评最多？给我差评率最高的 10 个品类，太小的品类就别放了。",
    caliber=["差评 = 1-2 星", "差评率 = 差评订单数 ÷ 有评价订单数", "品类归属 = 订单里出现的每个品类各计一次（订单 × 品类去重）",
             "最小样本 = 有评价订单 ≥ 500", "时间 = 全量"],
    assume=["一单多品类时，该订单在每个品类各计一次（也可以按\"主品类\"只计一次，口径需说明）", "品类缺失的商品不参与排名"],
    logic=["评价去重到订单", "订单 × 品类先 DISTINCT", "关联后按品类聚合，HAVING 过滤后排序取 10"],
    sql=f"""WITH {RV},
oc AS (   -- 订单 × 品类（去重：同一订单买了 3 件同品类商品只算 1 次）
    SELECT DISTINCT oi.order_id, c.category_cn
    FROM order_items oi
    JOIN products     p ON p.product_id = oi.product_id
    JOIN category_dim c ON c.product_category_name = p.product_category_name
)
SELECT
    oc.category_cn,
    COUNT(*)                                   AS reviewed_orders,
    SUM(rv.review_score <= 2)                  AS bad_orders,
    ROUND(SUM(rv.review_score <= 2) / COUNT(*), 4) AS bad_rate
FROM oc
JOIN rv ON rv.order_id = oc.order_id
GROUP BY oc.category_cn
HAVING COUNT(*) >= 500
ORDER BY bad_rate DESC
LIMIT 10;""",
    check="""SELECT COUNT(*) = COUNT(DISTINCT order_id, category_cn) AS ok, '订单×品类粒度无重复' AS note
FROM (SELECT DISTINCT oi.order_id, c.category_cn FROM order_items oi
      JOIN products p ON p.product_id = oi.product_id
      JOIN category_dim c ON c.product_category_name = p.product_category_name) t;""",
    wrong=f"""-- ❌ 直接 JOIN 商品行：一单买 N 件，这一单的评价就被数 N 次
WITH {RV}
SELECT c.category_cn, COUNT(*) AS reviewed_rows, SUM(rv.review_score <= 2) AS bad_rows,
       ROUND(SUM(rv.review_score <= 2) / COUNT(*), 4) AS bad_rate
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
JOIN category_dim c ON c.product_category_name = p.product_category_name
JOIN rv ON rv.order_id = oi.order_id
GROUP BY c.category_cn
HAVING COUNT(*) >= 500
ORDER BY bad_rate DESC
LIMIT 10;""",
    wrong_note="计数被商品行放大，差评率也会被\"多件订单\"加权（多件订单差评率本来就高），排名和数值都会变。",
    pitfalls=["orders → order_items 是一对多，按品类统计订单前必须先 DISTINCT 到订单 × 品类",
              "不过滤小样本时，只有 3 单的品类可能以 66% 差评率排第一，没有意义",
              "评价表要先去重，否则重复评价的订单被多算"],
    followups=["如果业务方想按\"主品类\"（订单里最贵的那件商品）只算一次，SQL 怎么改？",
               "阈值 500 是怎么定的？（看品类订单量分布，或者用贝叶斯平滑代替硬阈值，见 Q12）"],
))

# =================================================================== 进阶
Q.append(dict(
    id="Q04", level="进阶", title="月度品质客诉率（核心指标）",
    points=["多个 CTE 分层", "评价去重 + 打标表关联", "LEFT JOIN 保留分母", "按下单月 cohort 归属"],
    ask="品控这边想看每个月的品质客诉率，就是签收订单里，用户因为商品本身的问题给差评的比例。",
    caliber=["分母 = 当月下单的签收订单", "分子 = 分母中，最后一次评价为 1-3 星且命中任一品质问题标签（假货、质量缺陷、货不对板、少件漏发、包装破损）的订单，即品质客诉订单",
             "时间 = 按下单月归属，[2017-01-01, 2018-09-01)"],
    assume=["\"商品本身的问题\"用关键词规则识别出的标签表 review_tags 判断", "4-5 星的评价即使提到缺陷词也不算（多为\"没有瑕疵\"之类的正面表述）"],
    logic=["rv：评价去重", "qc：去重后的评价关联标签，筛出品质客诉订单", "dlv：签收订单作为分母，LEFT JOIN qc 后按月聚合"],
    sql=f"""WITH {RV},
{QC},
dlv AS (
    SELECT o.order_id, DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS month
    FROM orders o
    WHERE {DELIVERED}
      AND o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
)
SELECT
    d.month,
    COUNT(*)                                AS delivered_cnt,
    COUNT(q.order_id)                       AS qc_cnt,
    ROUND(COUNT(q.order_id) / COUNT(*), 4)  AS qc_rate
FROM dlv d
LEFT JOIN qc q ON q.order_id = d.order_id
GROUP BY d.month
ORDER BY d.month;""",
    check="""SELECT COUNT(*) = 0 AS ok, '打标表能关联上所有去重后的评价' AS note
FROM (SELECT order_id, review_id FROM (SELECT r.*, ROW_NUMBER() OVER (PARTITION BY order_id
      ORDER BY review_answer_timestamp DESC, review_id DESC) rn FROM order_reviews r) t WHERE rn = 1) v
WHERE NOT EXISTS (SELECT 1 FROM review_tags tg WHERE tg.review_id = v.review_id AND tg.order_id = v.order_id);""",
    cross=f"""WITH {RV.replace('FROM order_reviews', 'FROM qc_interview.order_reviews')},
{QC.replace('JOIN review_tags', 'JOIN qc_interview.review_tags')},
a AS (
    SELECT DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS m, COUNT(*) AS d, COUNT(q.order_id) AS qc
    FROM qc_interview.orders o LEFT JOIN qc q ON q.order_id = o.order_id
    WHERE {DELIVERED} AND o.order_purchase_timestamp >= '2017-01-01' AND o.order_purchase_timestamp < '2018-09-01'
    GROUP BY m)
SELECT SUM(a.qc <> k.qc_cnt OR a.d <> k.delivered_cnt) = 0 AS ok, '20 个月的分子、分母与数仓 ads_qc_kpi_month 完全一致' AS note
FROM a JOIN qc_dw.ads_qc_kpi_month k ON k.purchase_month = a.m;""",
    pitfalls=["分母必须用 LEFT JOIN 保留，不是品质客诉订单的签收订单也要计入分母",
              "review_id 不唯一，关联打标表要用 (review_id, order_id) 两个字段",
              "分子分母必须是同一批订单（都按下单月），不能用\"本月评价数 ÷ 本月签收订单数\"（见 Q18）"],
    followups=["如果要按周看，并且要剔除\"订单时间倒挂\"的脏数据，改哪里？",
               "品质客诉率上升了 0.69pp（2017 年 → 2018 年 1-8 月），你怎么判断是结构效应（卖了更多高品质客诉率的类目）还是组内效应（同一类目自身变差）？（因素分解）"],
))

Q.append(dict(
    id="Q05", level="进阶", title="每个一级类目里，品质客诉率最高的 3 个品类",
    points=["分组 TopN：DENSE_RANK() OVER (PARTITION BY …)", "HAVING 过滤小样本", "订单 × 品类粒度"],
    ask="每个大类里挑出品质问题最严重的 3 个品类，下周类目运营要逐个过。样本太小的不算。",
    caliber=["范围 = 2018-01 ~ 2018-08 下单且已签收", "品质客诉率 = 品质客诉订单 ÷ 签收订单（同 Q04）",
             "品类归属 = 订单 × 品类去重", "最小样本 = 签收订单 ≥ 100", "排名 = 一级类目内按品质客诉率倒序，并列同名次"],
    assume=["并列时都保留（DENSE_RANK），所以一个大类可能返回多于 3 行", "品类缺失的商品不参与"],
    logic=["复用 Q04 的 rv / qc", "订单 × 品类去重并限定时间", "品类聚合 → 类目内排名 → 取前 3"],
    sql=f"""WITH {RV},
{QC},
oc AS (   -- 2018 年 1-8 月下单且已签收的 订单 × 品类
    SELECT DISTINCT o.order_id, c.category_l1, c.category_cn
    FROM orders o
    JOIN order_items  oi ON oi.order_id = o.order_id
    JOIN products     p  ON p.product_id = oi.product_id
    JOIN category_dim c  ON c.product_category_name = p.product_category_name
    WHERE {DELIVERED}
      AND o.order_purchase_timestamp >= '2018-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
),
cat AS (
    SELECT oc.category_l1, oc.category_cn,
           COUNT(*)                  AS delivered_cnt,
           COUNT(q.order_id)         AS qc_cnt,
           COUNT(q.order_id) / COUNT(*) AS qc_rate
    FROM oc
    LEFT JOIN qc q ON q.order_id = oc.order_id
    GROUP BY oc.category_l1, oc.category_cn
    HAVING COUNT(*) >= 100
),
ranked AS (
    SELECT cat.*, DENSE_RANK() OVER (PARTITION BY category_l1 ORDER BY qc_rate DESC) AS rk
    FROM cat
)
SELECT category_l1, rk, category_cn, delivered_cnt, qc_cnt, ROUND(qc_rate, 4) AS qc_rate
FROM ranked
WHERE rk <= 3
ORDER BY category_l1, rk;""",
    check=f"""WITH {RV}, {QC},
oc AS (SELECT DISTINCT o.order_id, c.category_cn FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
       JOIN products p ON p.product_id = oi.product_id JOIN category_dim c ON c.product_category_name = p.product_category_name
       WHERE {DELIVERED} AND o.order_purchase_timestamp >= '2018-01-01' AND o.order_purchase_timestamp < '2018-09-01')
SELECT SUM(qc_cnt <= delivered_cnt) = COUNT(*) AS ok, '每个品类分子 ≤ 分母' AS note
FROM (SELECT oc.category_cn, COUNT(*) delivered_cnt, COUNT(q.order_id) qc_cnt FROM oc LEFT JOIN qc q ON q.order_id = oc.order_id
      GROUP BY oc.category_cn) t;""",
    pitfalls=["ROW_NUMBER / RANK / DENSE_RANK 的区别：并列时 ROW_NUMBER 随机取一个，RANK 会跳号，DENSE_RANK 不跳号",
              "HAVING 要在排名之前过滤，否则小样本品类占掉名次",
              "窗口函数不能直接写在 WHERE 里，要包一层子查询 / CTE"],
    followups=["如果要求\"严格只返回 3 行\"怎么改？", "如果改成\"主品类\"口径，排名会变吗？为什么？"],
))

Q.append(dict(
    id="Q06", level="进阶", title="近 3 个月品质明显变差的商家",
    points=["条件聚合做两期对比", "HAVING 引用聚合别名", "订单 × 商家粒度"],
    ask="有没有哪些商家最近品质明显变差了？拿最近三个月和之前三个月比，给我恶化最多的 10 家。",
    caliber=["近 3 月 = 2018-06 ~ 2018-08 下单；前 3 月 = 2018-03 ~ 2018-05 下单", "品质客诉率同 Q04，按订单 × 商家归属",
             "两期签收订单都 ≥ 20", "恶化幅度 = 近 3 月品质客诉率 − 前 3 月品质客诉率（百分点）"],
    assume=["一个订单含多个商家时，该订单的评价同时计入每个商家"],
    logic=["订单 × 商家去重并打上期别", "一次 GROUP BY 用条件聚合算出两期分子分母", "算差值排序"],
    sql=f"""WITH {RV},
{QC},
os AS (
    SELECT DISTINCT o.order_id, oi.seller_id,
           CASE WHEN o.order_purchase_timestamp >= '2018-06-01' THEN 'recent' ELSE 'before' END AS period
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE {DELIVERED}
      AND o.order_purchase_timestamp >= '2018-03-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
),
s AS (
    SELECT
        os.seller_id,
        SUM(os.period = 'before')                         AS d_before,
        SUM(os.period = 'before' AND q.order_id IS NOT NULL) AS qc_before,
        SUM(os.period = 'recent')                         AS d_recent,
        SUM(os.period = 'recent' AND q.order_id IS NOT NULL) AS qc_recent
    FROM os
    LEFT JOIN qc q ON q.order_id = os.order_id
    GROUP BY os.seller_id
    HAVING d_before >= 20 AND d_recent >= 20
)
SELECT
    seller_id,
    d_before, qc_before, ROUND(qc_before / d_before, 4) AS rate_before,
    d_recent, qc_recent, ROUND(qc_recent / d_recent, 4) AS rate_recent,
    ROUND((qc_recent / d_recent - qc_before / d_before) * 100, 2) AS change_pp
FROM s
ORDER BY change_pp DESC
LIMIT 10;""",
    check=f"""SELECT COUNT(*) = COUNT(DISTINCT order_id, seller_id) AS ok, '订单×商家粒度无重复' AS note
FROM (SELECT DISTINCT o.order_id, oi.seller_id FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
      WHERE {DELIVERED} AND o.order_purchase_timestamp >= '2018-03-01' AND o.order_purchase_timestamp < '2018-09-01') t;""",
    pitfalls=["不做订单 × 商家去重，买了同一商家 3 件商品的订单会被算 3 次",
              "两期都要设最小样本，否则前期 20 单 0 个品质客诉订单、后期 20 单 2 个就排第一，全是噪音",
              "只看百分点差值会偏向小商家，可以同时输出品质客诉订单的增量，或用显著性检验（追问）"],
    followups=["怎么判断变化是不是显著的？（两比例 z 检验：z = (p2 − p1) / sqrt(p(1−p)(1/n1 + 1/n2))）",
               "近 3 个月里最后一个月评价还没回收完整，会不会低估近期的品质客诉率？怎么处理？"],
))

Q.append(dict(
    id="Q07", level="进阶", title="品质客诉率连续 3 个月上升的品类（预警）",
    points=["LAG() 取前 N 期", "WINDOW 子句复用窗口", "PERIOD_DIFF 校验月份连续"],
    ask="帮我找出品质客诉率连续 3 个月上升的品类，做个预警。",
    caliber=["月度品类品质客诉率：订单 × 品类，签收订单 ≥ 30 的月份才参与", "连续 3 个月上升 = 连续 3 次环比上升（r(m) > r(m−1) > r(m−2) > r(m−3)）",
             "四个月必须是连续的自然月", "时间 = 2017-01 ~ 2018-08"],
    assume=["样本不足 30 单的月份视为\"无数据\"，会打断连续性"],
    logic=["品类 × 月聚合", "LAG 取前 1/2/3 期的品质客诉率和前 3 期的月份", "判断三次上升且月份连续"],
    sql=f"""WITH {RV},
{QC},
oc AS (
    SELECT DISTINCT o.order_id, c.category_cn, DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS month
    FROM orders o
    JOIN order_items  oi ON oi.order_id = o.order_id
    JOIN products     p  ON p.product_id = oi.product_id
    JOIN category_dim c  ON c.product_category_name = p.product_category_name
    WHERE {DELIVERED}
      AND o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
),
m AS (
    SELECT oc.category_cn, oc.month, COUNT(*) AS delivered_cnt, COUNT(q.order_id) / COUNT(*) AS qc_rate
    FROM oc
    LEFT JOIN qc q ON q.order_id = oc.order_id
    GROUP BY oc.category_cn, oc.month
    HAVING COUNT(*) >= 30
),
l AS (
    SELECT m.*,
           LAG(month, 3)   OVER w AS month_l3,
           LAG(qc_rate, 1) OVER w AS r1,
           LAG(qc_rate, 2) OVER w AS r2,
           LAG(qc_rate, 3) OVER w AS r3
    FROM m
    WINDOW w AS (PARTITION BY category_cn ORDER BY month)
)
SELECT category_cn, month AS alert_month,
       ROUND(r3, 4) AS rate_m3, ROUND(r2, 4) AS rate_m2, ROUND(r1, 4) AS rate_m1, ROUND(qc_rate, 4) AS rate_m0,
       delivered_cnt
FROM l
WHERE qc_rate > r1 AND r1 > r2 AND r2 > r3
  AND PERIOD_DIFF(REPLACE(month, '-', ''), REPLACE(month_l3, '-', '')) = 3   -- 四个月是连续的
ORDER BY alert_month DESC, category_cn;""",
    check=f"""WITH {RV}, {QC},
oc AS (SELECT DISTINCT o.order_id, c.category_cn, DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS month
       FROM orders o JOIN order_items oi ON oi.order_id = o.order_id JOIN products p ON p.product_id = oi.product_id
       JOIN category_dim c ON c.product_category_name = p.product_category_name
       WHERE {DELIVERED} AND o.order_purchase_timestamp >= '2017-01-01' AND o.order_purchase_timestamp < '2018-09-01'),
m AS (SELECT category_cn, month FROM oc GROUP BY category_cn, month HAVING COUNT(*) >= 30),
g AS (SELECT month, LAG(month, 3) OVER (PARTITION BY category_cn ORDER BY month) l3 FROM m)
SELECT SUM(PERIOD_DIFF(REPLACE(month, '-', ''), REPLACE(l3, '-', '')) > 3) > 0 AS ok,
       CONCAT('存在 ', SUM(PERIOD_DIFF(REPLACE(month, '-', ''), REPLACE(l3, '-', '')) > 3), ' 处月份断档，说明\"月份连续\"这个条件是必要的') AS note
FROM g WHERE l3 IS NOT NULL;""",
    pitfalls=["LAG 取的是\"上一行\"，不是\"上个月\"：某个月样本不足被过滤后，LAG 会跨月取数，必须校验月份连续",
              "\"连续 3 个月上升\"要先和业务确认是 3 次上升（看 4 个月）还是 2 次上升（看 3 个月）",
              "小品类月度波动大，预警前最好加最小样本，或者用 3 个月滚动品质客诉率"],
    followups=["改成\"3 个月滚动品质客诉率\"连续上升怎么写？（先用 SUM() OVER (ROWS 2 PRECEDING) 算滚动分子分母）",
               "预警上线后，怎么评估这条规则有没有用？（触发的品类下个月是否真的更差）"],
))

Q.append(dict(
    id="Q08", level="进阶", title="单件订单 vs 多件订单的少件漏发客诉率",
    points=["一对多关联前先聚合（防止数据放大）", "错误写法对比"],
    ask="听说买多件的订单老是少发，帮我对比一下单件订单和多件订单的少件漏发客诉率。",
    caliber=["单件 = 订单只有 1 个商品行；多件 = 商品行 ≥ 2", "少件漏发客诉率 = 少件漏发客诉订单（1-3 星且 is_missing = 1）÷ 签收订单",
             "范围 = 2018-01 ~ 2018-08 下单且已签收"],
    assume=["\"多件\"按商品行数判断，同一商品买 2 件在源表里是 2 行"],
    logic=["商品行先聚合到订单粒度得到件数", "订单表关联件数和少件漏发客诉订单", "按单件 / 多件分组"],
    sql=f"""WITH {RV},
miss AS (   -- 少件漏发客诉订单
    SELECT rv.order_id
    FROM rv
    JOIN review_tags tg ON tg.review_id = rv.review_id AND tg.order_id = rv.order_id
    WHERE rv.review_score <= 3 AND tg.is_missing = 1
),
item_cnt AS (   -- 关键：先把商品行聚合到订单粒度
    SELECT order_id, COUNT(*) AS items
    FROM order_items
    GROUP BY order_id
)
SELECT
    CASE WHEN ic.items = 1 THEN '单件' ELSE '多件' END AS order_type,
    COUNT(*)                                   AS delivered_cnt,
    COUNT(miss.order_id)                       AS missing_cnt,
    ROUND(COUNT(miss.order_id) / COUNT(*), 4)  AS missing_rate
FROM orders o
JOIN item_cnt  ic   ON ic.order_id = o.order_id
LEFT JOIN miss      ON miss.order_id = o.order_id
WHERE {DELIVERED}
  AND o.order_purchase_timestamp >= '2018-01-01'
  AND o.order_purchase_timestamp <  '2018-09-01'
GROUP BY order_type
ORDER BY order_type;""",
    check=f"""SELECT COUNT(*) AS ok_base, '2018 年 1-8 月有商品明细的签收订单（答案两行之和应等于它）' AS note
FROM orders o WHERE {DELIVERED}
  AND o.order_purchase_timestamp >= '2018-01-01' AND o.order_purchase_timestamp < '2018-09-01'
  AND EXISTS (SELECT 1 FROM order_items oi WHERE oi.order_id = o.order_id);""",
    answer_assert=lambda df, chk: (int(df.delivered_cnt.sum()) == int(chk.ok_base.iloc[0]),
                                   f"答案两行签收订单之和 {int(df.delivered_cnt.sum()):,} = 基数 {int(chk.ok_base.iloc[0]):,}"),
    wrong=f"""-- ❌ 直接 JOIN 商品行：多件订单按件数被重复计入分子和分母
WITH {RV},
miss AS (SELECT rv.order_id FROM rv JOIN review_tags tg ON tg.review_id = rv.review_id AND tg.order_id = rv.order_id
         WHERE rv.review_score <= 3 AND tg.is_missing = 1),
item_cnt AS (SELECT order_id, COUNT(*) AS items FROM order_items GROUP BY order_id)
SELECT CASE WHEN ic.items = 1 THEN '单件' ELSE '多件' END AS order_type,
       COUNT(*) AS delivered_cnt, COUNT(miss.order_id) AS missing_cnt,
       ROUND(COUNT(miss.order_id) / COUNT(*), 4) AS missing_rate
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id          -- 多余的一对多关联
JOIN item_cnt ic    ON ic.order_id = o.order_id
LEFT JOIN miss      ON miss.order_id = o.order_id
WHERE {DELIVERED} AND o.order_purchase_timestamp >= '2018-01-01' AND o.order_purchase_timestamp < '2018-09-01'
GROUP BY order_type ORDER BY order_type;""",
    wrong_note="多件订单的签收订单数和少件漏发客诉订单数都被放大成\"商品行数\"，件数越多的订单权重越大，少件漏发客诉率被高估。",
    pitfalls=["orders JOIN order_items 后 COUNT(*) 数的是商品行，不是订单",
              "写完先做粒度检查：COUNT(*) 是否等于 COUNT(DISTINCT order_id)",
              "\"多件\"还可以细分成同 SKU 多件 / 多 SKU / 多商家，多商家订单的少件漏发客诉率最高（分包裹发货）"],
    followups=["多件订单少件漏发客诉率高，一定是仓库漏发吗？还可能是什么原因？（分包裹未同时到达、用户提前评价）怎么用数据区分？",
               "如果要给仓配团队定目标，你会用哪个指标？"],
))

Q.append(dict(
    id="Q09", level="进阶", title="商家发货超时率（每个商家用自己的发货时限）",
    points=["订单 × 商家粒度", "按商家的 SLA 判断", "条件聚合 + 条件平均"],
    ask="算一下每个商家的发货超时率，超时就是商家交给物流的时间晚于平台要求的最晚发货时间。只看订单量大于 100 的商家，按超时率倒序。",
    caliber=["发货时限（SLA）= 该商家在该订单中商品行的 shipping_limit_date（取最晚）", "超时 = 交付物流时间 > SLA",
             "发货超时率 = 超时订单 ÷ 已出库订单（按订单 × 商家计）", "范围 = 2018-01 ~ 2018-08 下单、已出库；已出库订单 > 100 的商家"],
    assume=["出库时间 order_delivered_carrier_date 是订单级字段，一单多商家时共用同一个出库时间（源数据限制，需要说明）"],
    logic=["商品行先聚合到订单 × 商家，SLA 取 MAX", "关联订单出库时间", "按商家聚合、过滤、排序"],
    sql="""WITH os AS (   -- 订单 × 商家：同一商家在同一订单里有多个商品行时，SLA 取最晚的
    SELECT order_id, seller_id, MAX(shipping_limit_date) AS sla
    FROM order_items
    GROUP BY order_id, seller_id
)
SELECT
    os.seller_id,
    COUNT(*)                                               AS shipped_orders,
    SUM(o.order_delivered_carrier_date > os.sla)           AS overdue_orders,
    ROUND(SUM(o.order_delivered_carrier_date > os.sla) / COUNT(*), 4) AS overdue_rate,
    ROUND(AVG(CASE WHEN o.order_delivered_carrier_date > os.sla
                   THEN TIMESTAMPDIFF(HOUR, os.sla, o.order_delivered_carrier_date) END), 1) AS avg_overdue_hours
FROM os
JOIN orders o ON o.order_id = os.order_id
WHERE o.order_delivered_carrier_date IS NOT NULL
  AND o.order_purchase_timestamp >= '2018-01-01'
  AND o.order_purchase_timestamp <  '2018-09-01'
GROUP BY os.seller_id
HAVING COUNT(*) > 100
ORDER BY overdue_rate DESC
LIMIT 10;""",
    check="""SELECT COUNT(*) = COUNT(DISTINCT order_id, seller_id) AS ok, '订单×商家粒度无重复' AS note
FROM (SELECT order_id, seller_id FROM order_items GROUP BY order_id, seller_id) t;""",
    pitfalls=["直接在商品行上算超时率，买 5 件的订单就算了 5 次",
              "未出库的订单（出库时间为空）不能进分母，否则超时率被稀释",
              "AVG(CASE WHEN … THEN … END) 不写 ELSE，才能只对超时订单求平均（ELSE 0 会把平均值拉低）"],
    followups=["源数据里有出库时间早于下单时间的订单，会影响这个指标吗？要不要剔除？",
               "发货超时和最终的品质客诉有关系吗？你会怎么验证？"],
))

# =================================================================== 高阶
Q.append(dict(
    id="Q10", level="高阶", title="首单遇到品质问题的用户，还会回来复购吗",
    points=["用户 ID 选择：customer_unique_id vs customer_id", "首单识别（全历史 ROW_NUMBER）", "观察期截断"],
    ask="首单就遇到质量问题的用户，后面还会回来买吗？跟首单没问题的用户比一下复购率。",
    caliber=["用户 = customer_unique_id（自然人）", "首单 = 该用户全部历史中最早的订单，且已签收、有评价",
             "首单体验分组：品质客诉 / 其他差评（1-2 星非品质）/ 无问题", "复购 = 首单之后 180 天内再次下单",
             "观察期 = 首单在 2018-03-01 之前（保证每个用户都有完整 180 天观察期）"],
    assume=["与首单同一时刻下的其他订单（拆单）不算复购", "数据截止 2018-08，首单晚于 2018-03 的用户观察期不满，不纳入"],
    logic=["用 customer_unique_id 给所有订单排序", "取首单并打体验标签", "看首单后 180 天内有无新订单"],
    sql=f"""WITH {RV},
{QC},
co AS (   -- 自然人维度的订单序列
    SELECT c.customer_unique_id, o.order_id, o.order_purchase_timestamp, o.order_status,
           o.order_delivered_customer_date,
           ROW_NUMBER() OVER (PARTITION BY c.customer_unique_id
                              ORDER BY o.order_purchase_timestamp, o.order_id) AS seq
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
),
first_order AS (
    SELECT co.customer_unique_id, co.order_purchase_timestamp, rv.review_score,
           (q.order_id IS NOT NULL) AS is_qc
    FROM co
    JOIN rv      ON rv.order_id = co.order_id
    LEFT JOIN qc q ON q.order_id = co.order_id
    WHERE co.seq = 1
      AND co.order_status = 'delivered' AND co.order_delivered_customer_date IS NOT NULL
      AND co.order_purchase_timestamp >= '2017-01-01'
      AND co.order_purchase_timestamp <  '2018-03-01'
),
back AS (
    SELECT f.customer_unique_id,
           MAX(co.order_purchase_timestamp > f.order_purchase_timestamp
               AND co.order_purchase_timestamp < f.order_purchase_timestamp + INTERVAL 180 DAY) AS repurchased
    FROM first_order f
    JOIN co ON co.customer_unique_id = f.customer_unique_id
    GROUP BY f.customer_unique_id
)
SELECT
    CASE WHEN f.is_qc = 1          THEN '1 首单品质客诉'
         WHEN f.review_score <= 2  THEN '2 首单其他差评'
         ELSE                           '3 首单无问题' END AS first_experience,
    COUNT(*)                        AS customers,
    SUM(b.repurchased)              AS repurchased,
    ROUND(AVG(b.repurchased), 4)    AS repurchase_rate_180d
FROM first_order f
JOIN back b ON b.customer_unique_id = f.customer_unique_id
GROUP BY first_experience
ORDER BY first_experience;""",
    check="""SELECT COUNT(DISTINCT customer_id) = COUNT(*) AND COUNT(DISTINCT customer_unique_id) < COUNT(*) AS ok,
       CONCAT('customer_id 一单一个（', COUNT(*), ' 个），自然人 customer_unique_id 只有 ', COUNT(DISTINCT customer_unique_id), ' 个') AS note
FROM customers;""",
    wrong=f"""-- ❌ 用 customer_id 当用户：customer_id 是"一单一个"的，所有人看起来都没复购
WITH co AS (
    SELECT o.customer_id, o.order_id, o.order_purchase_timestamp,
           COUNT(*) OVER (PARTITION BY o.customer_id) AS n_orders
    FROM orders o
    WHERE o.order_purchase_timestamp >= '2017-01-01' AND o.order_purchase_timestamp < '2018-09-01')
SELECT COUNT(DISTINCT customer_id) AS customers, ROUND(AVG(n_orders > 1), 4) AS repurchase_rate
FROM co;""",
    wrong_note="复购率算出来是 0——不是用户不复购，是 ID 选错了。拿到新表先看每个 ID 字段的粒度。",
    pitfalls=["customer_id 是订单维度的客户 ID（每单一个），算复购、首单、用户数必须用 customer_unique_id",
              "首单要在全部历史里找，不能只在分析区间内找，否则区间前买过的老客被当成新客",
              "观察期不满的用户要剔除或置空，不能当成\"没复购\"",
              "这份数据 180 天复购率整体不到 3%，三组几乎没有差异，不能据此下\"品质问题影响复购\"的结论（见追问）"],
    followups=["三组复购率都在 2.8% 左右，如果差异是 0.3 个百分点，要多大样本才能检测出来？",
               "如果差异不显著，能不能说\"品质问题不影响复购\"？还缺什么数据？（平台整体复购低、用户跨平台、观察期短）"],
))

Q.append(dict(
    id="Q11", level="高阶", title="品质客诉订单的帕累托：多少商家贡献了 80% 的品质客诉订单",
    points=["累计窗口 SUM() OVER (ORDER BY … ROWS UNBOUNDED PRECEDING)", "总量开窗求占比", "取第一个达标行"],
    ask="品质问题是不是集中在少数商家身上？多少家商家贡献了 80% 的品质客诉订单？",
    caliber=["范围 = 2018-01 ~ 2018-08 下单且已签收，订单 × 商家归属", "商家按品质客诉订单数从高到低排序",
             "输出 = 累计品质客诉订单占比达到 80% 所需的商家数、商家占比、对应签收订单占比"],
    assume=["品质客诉订单数相同的商家按 seller_id 排序，保证结果确定"],
    logic=["商家聚合品质客诉订单数和签收订单数", "累计求和 ÷ 总和得到累计占比", "取累计占比首次 ≥ 80% 的那一行"],
    sql=f"""WITH {RV},
{QC},
os AS (
    SELECT DISTINCT o.order_id, oi.seller_id
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE {DELIVERED}
      AND o.order_purchase_timestamp >= '2018-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
),
s AS (
    SELECT os.seller_id, COUNT(*) AS delivered_cnt, COUNT(q.order_id) AS qc_cnt
    FROM os
    LEFT JOIN qc q ON q.order_id = os.order_id
    GROUP BY os.seller_id
),
c AS (
    SELECT s.*,
           ROW_NUMBER() OVER (ORDER BY qc_cnt DESC, seller_id)                                  AS rk,
           COUNT(*)     OVER ()                                                                 AS n_sellers,
           SUM(qc_cnt)  OVER (ORDER BY qc_cnt DESC, seller_id ROWS UNBOUNDED PRECEDING)
             / SUM(qc_cnt) OVER ()                                                              AS cum_qc_share,
           SUM(delivered_cnt) OVER (ORDER BY qc_cnt DESC, seller_id ROWS UNBOUNDED PRECEDING)
             / SUM(delivered_cnt) OVER ()                                                       AS cum_order_share
    FROM s
)
SELECT rk AS sellers_needed, n_sellers,
       ROUND(rk / n_sellers, 4)   AS seller_share,
       ROUND(cum_qc_share, 4)     AS qc_share,
       ROUND(cum_order_share, 4)  AS order_share
FROM c
WHERE cum_qc_share >= 0.8
ORDER BY rk
LIMIT 1;""",
    check=f"""WITH {RV}, {QC},
os AS (SELECT DISTINCT o.order_id, oi.seller_id FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
       WHERE {DELIVERED} AND o.order_purchase_timestamp >= '2018-01-01' AND o.order_purchase_timestamp < '2018-09-01'),
s AS (SELECT os.seller_id, COUNT(q.order_id) qc_cnt FROM os LEFT JOIN qc q ON q.order_id = os.order_id GROUP BY os.seller_id)
SELECT ABS(MAX(cum) - 1) < 1e-9 AS ok, '累计占比最后一行 = 100%' AS note
FROM (SELECT SUM(qc_cnt) OVER (ORDER BY qc_cnt DESC, seller_id ROWS UNBOUNDED PRECEDING) / SUM(qc_cnt) OVER () AS cum FROM s) t;""",
    pitfalls=["累计窗口不写 ROWS 时默认是 RANGE：品质客诉订单数相同的商家会被一起累加，累计占比出现\"跳台阶\"",
              "按品质客诉订单数排序天然偏向大商家：头部商家的品质客诉订单多，可能只是因为卖得多，要同时看签收订单占比",
              "80% 的品质客诉订单来自 X% 的商家，还要对比这些商家占多少订单，否则结论只是\"商家越大，品质客诉订单越多\""],
    followups=["改成按\"品质客诉率\"排序，结论会怎么变？为什么要配合最小样本？", "如果只能整治 20 家商家，你怎么选？"],
))

Q.append(dict(
    id="Q12", level="高阶", title="高风险商家圈选（商家基准品质客诉率 + 贝叶斯平滑）",
    points=["CROSS JOIN 商家基准品质客诉率", "贝叶斯平滑处理小样本", "规则圈选"],
    ask="按我们的规则圈一下高风险商家：近 6 个月品质客诉率超过全部商家的 2 倍、且至少 3 个品质客诉订单。小商家别被误伤。",
    caliber=["商家评估窗口 = 下单月 2018-03 至 2018-08 的签收订单，订单 × 商家归属（商家签收订单）",
             "商家基准品质客诉率 = 全部商家的商家品质客诉订单之和 ÷ 商家签收订单之和",
             "平滑品质客诉率 = (商家品质客诉订单 + 50 × 商家基准品质客诉率) ÷ (商家签收订单 + 50)",
             "高风险商家 = 商家签收订单 ≥ 30 且 商家品质客诉订单 ≥ 3 且 平滑品质客诉率 ≥ 2 × 商家基准品质客诉率"],
    assume=["平滑强度 m = 50（相当于给每个商家先加 50 单\"商家基准品质客诉率水平\"的虚拟订单），与数仓商家分层一致"],
    logic=["商家聚合", "单独算出商家基准品质客诉率并 CROSS JOIN", "按规则过滤，并输出未平滑与平滑品质客诉率"],
    sql=f"""WITH {RV},
{QC},
os AS (
    SELECT DISTINCT o.order_id, oi.seller_id
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE {DELIVERED}
      AND o.order_purchase_timestamp >= '2018-03-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
),
s AS (
    SELECT os.seller_id, COUNT(*) AS delivered_cnt, COUNT(q.order_id) AS qc_cnt
    FROM os
    LEFT JOIN qc q ON q.order_id = os.order_id
    GROUP BY os.seller_id
),
p AS (
    SELECT SUM(qc_cnt) / SUM(delivered_cnt) AS p_rate FROM s
)
SELECT
    s.seller_id, s.delivered_cnt, s.qc_cnt,
    ROUND(s.qc_cnt / s.delivered_cnt, 4)                         AS raw_rate,
    ROUND((s.qc_cnt + 50 * p.p_rate) / (s.delivered_cnt + 50), 4) AS smooth_rate,
    ROUND(p.p_rate, 4)                                           AS benchmark_rate
FROM s
CROSS JOIN p
WHERE s.delivered_cnt >= 30
  AND s.qc_cnt >= 3
  AND (s.qc_cnt + 50 * p.p_rate) / (s.delivered_cnt + 50) >= 2 * p.p_rate
ORDER BY smooth_rate DESC;""",
    check=f"""WITH {RV}, {QC},
os AS (SELECT DISTINCT o.order_id, oi.seller_id FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
       WHERE {DELIVERED} AND o.order_purchase_timestamp >= '2018-03-01' AND o.order_purchase_timestamp < '2018-09-01'),
s AS (SELECT os.seller_id, COUNT(*) d, COUNT(q.order_id) qc FROM os LEFT JOIN qc q ON q.order_id = os.order_id GROUP BY os.seller_id),
p AS (SELECT SUM(qc) / SUM(d) pr FROM s)
SELECT SUM(s.qc / s.d >= 2 * p.pr AND s.qc >= 1) > SUM(s.d >= 30 AND s.qc >= 3 AND (s.qc + 50 * p.pr) / (s.d + 50) >= 2 * p.pr) AS ok,
       CONCAT('不做平滑和门槛时会圈出 ', SUM(s.qc / s.d >= 2 * p.pr AND s.qc >= 1), ' 家，平滑后只剩 ',
              SUM(s.d >= 30 AND s.qc >= 3 AND (s.qc + 50 * p.pr) / (s.d + 50) >= 2 * p.pr), ' 家') AS note
FROM s CROSS JOIN p;""",
    cross=f"""WITH {RV.replace('FROM order_reviews', 'FROM qc_interview.order_reviews')},
{QC.replace('JOIN review_tags', 'JOIN qc_interview.review_tags')},
os AS (SELECT DISTINCT o.order_id, oi.seller_id FROM qc_interview.orders o JOIN qc_interview.order_items oi ON oi.order_id = o.order_id
       WHERE {DELIVERED} AND o.order_purchase_timestamp >= '2018-03-01' AND o.order_purchase_timestamp < '2018-09-01'),
s AS (SELECT os.seller_id, COUNT(*) d, COUNT(q.order_id) qc FROM os LEFT JOIN qc q ON q.order_id = os.order_id GROUP BY os.seller_id),
p AS (SELECT SUM(qc) / SUM(d) pr FROM s),
mine AS (SELECT s.seller_id FROM s CROSS JOIN p WHERE s.d >= 30 AND s.qc >= 3 AND (s.qc + 50 * p.pr) / (s.d + 50) >= 2 * p.pr)
SELECT (SELECT COUNT(*) FROM mine) = (SELECT COUNT(*) FROM qc_dw.ads_seller_scorecard WHERE risk_level = '高风险')
   AND NOT EXISTS (SELECT 1 FROM qc_dw.ads_seller_scorecard sc WHERE sc.risk_level = '高风险'
                   AND NOT EXISTS (SELECT 1 FROM mine WHERE mine.seller_id = sc.seller_id)) AS ok,
       '圈出的名单与数仓 ads_seller_scorecard 的高风险商家完全一致' AS note;""",
    pitfalls=["直接用未平滑的品质客诉率 ≥ 2 倍会圈进一大批\"10 单里 1 个品质客诉订单\"的小商家，治理资源被浪费",
              "商家基准品质客诉率要在全部商家上算，不能只在参评商家（商家签收订单 ≥ 30）上算（口径要和指标字典一致）",
              "平滑参数 m 要写进口径，调整 m 会改变名单"],
    followups=["m = 50 怎么定？（可以用经验贝叶斯：拟合商家品质客诉率的 Beta 分布，用先验参数之和作为 m）",
               "圈出来的商家整改后，怎么评估整改效果？（整改前后对比 + 对照组，注意均值回归）"],
))

Q.append(dict(
    id="Q13", level="进阶", title="数据核查：订单时间字段有没有脏数据",
    points=["UNION ALL 拼核查清单", "NOT EXISTS 反连接", "数据质量意识"],
    ask="看板上 3 月的平均送达时长有点怪，帮我查查订单的时间字段有没有脏数据。",
    caliber=["逐项核查：时间倒挂、状态与时间矛盾、缺关键时间、订单无明细、送达时长极端值", "输出 = 每类问题的订单数"],
    assume=["送达时长 > 60 天视为疑似异常（阈值可调）"],
    logic=["每种问题写一段 SELECT", "UNION ALL 拼成一张核查清单"],
    sql="""SELECT '出库时间早于下单时间' AS issue, COUNT(*) AS orders
FROM orders WHERE order_delivered_carrier_date < order_purchase_timestamp
UNION ALL
SELECT '签收时间早于出库时间', COUNT(*)
FROM orders WHERE order_delivered_customer_date < order_delivered_carrier_date
UNION ALL
SELECT '状态为已签收但没有签收时间', COUNT(*)
FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NULL
UNION ALL
SELECT '状态不是已签收却有签收时间', COUNT(*)
FROM orders WHERE order_status <> 'delivered' AND order_delivered_customer_date IS NOT NULL
UNION ALL
SELECT '已签收但没有支付审核时间', COUNT(*)
FROM orders WHERE order_status = 'delivered' AND order_approved_at IS NULL
UNION ALL
SELECT '订单没有任何商品明细', COUNT(*)
FROM orders o WHERE NOT EXISTS (SELECT 1 FROM order_items oi WHERE oi.order_id = o.order_id)
UNION ALL
SELECT '送达时长超过 60 天（疑似异常）', COUNT(*)
FROM orders WHERE TIMESTAMPDIFF(DAY, order_purchase_timestamp, order_delivered_customer_date) > 60;""",
    check="""SELECT (SELECT COUNT(*) FROM orders WHERE order_delivered_carrier_date < order_purchase_timestamp
              OR order_delivered_customer_date < order_delivered_carrier_date) = 189 AS ok,
       '时间倒挂合计 189 单，与数仓 dq_time_anomaly 标记一致' AS note;""",
    pitfalls=["\"没有商品明细\"用 NOT IN (子查询) 时，只要子查询出现一个 NULL 就一行都不返回，用 NOT EXISTS",
              "核查完要说清楚处理方式（剔除 / 打标 / 保留），并写进口径，而不是悄悄删掉",
              "单看数量不够，还要看影响：剔除前后 3 月平均送达时长差多少（追问）"],
    followups=["剔除时间倒挂的订单后，2018 年 3 月的平均送达时长变化多少？这个影响大不大？",
               "这些脏数据应该在哪一层处理？（ODS 保留原样，DWD 打标记，ADS 按指标口径决定是否剔除）"],
))

Q.append(dict(
    id="Q14", level="高阶", title="对账：支付金额与商品金额 + 运费对不上的订单",
    points=["两个一对多表必须先各自聚合", "错误写法对比（笛卡尔放大）", "对账思路"],
    ask="财务说有些订单的支付金额和商品金额加运费对不上，帮我找出差额超过 1 块钱的订单。",
    caliber=["商品侧金额 = Σ(price + freight_value)，按订单汇总", "支付侧金额 = Σ payment_value，按订单汇总（组合支付有多行）",
             "差额 = 支付 − 商品侧；|差额| > 1 视为对不上", "输出差额最大的 10 单"],
    assume=["只比较两侧都有记录的订单；只有一侧有记录的单独列出（追问）"],
    logic=["order_items、order_payments 各自先聚合到订单", "再关联比较"],
    sql="""WITH i AS (
    SELECT order_id, SUM(price + freight_value) AS item_amt, COUNT(*) AS item_rows
    FROM order_items GROUP BY order_id
),
p AS (
    SELECT order_id, SUM(payment_value) AS pay_amt, COUNT(*) AS pay_rows
    FROM order_payments GROUP BY order_id
)
SELECT i.order_id, i.item_rows, p.pay_rows,
       ROUND(i.item_amt, 2)            AS item_amt,
       ROUND(p.pay_amt, 2)             AS pay_amt,
       ROUND(p.pay_amt - i.item_amt, 2) AS diff
FROM i
JOIN p ON p.order_id = i.order_id
WHERE ABS(p.pay_amt - i.item_amt) > 1
ORDER BY ABS(p.pay_amt - i.item_amt) DESC
LIMIT 10;""",
    check="""SELECT COUNT(*) = 249 AS ok, CONCAT('差额 > 1 的订单共 ', COUNT(*), ' 单（与数据质量报告一致）') AS note
FROM (SELECT order_id, SUM(price + freight_value) v FROM order_items GROUP BY order_id) i
JOIN (SELECT order_id, SUM(payment_value) v FROM order_payments GROUP BY order_id) p ON p.order_id = i.order_id
WHERE ABS(p.v - i.v) > 1;""",
    wrong="""-- ❌ 两张一对多的表直接 JOIN 再 SUM：商品行数 × 支付行数，两边金额都被放大
SELECT COUNT(*) AS mismatched_orders
FROM (
    SELECT oi.order_id, SUM(oi.price + oi.freight_value) AS item_amt, SUM(op.payment_value) AS pay_amt
    FROM order_items oi
    JOIN order_payments op ON op.order_id = oi.order_id
    GROUP BY oi.order_id
    HAVING ABS(SUM(op.payment_value) - SUM(oi.price + oi.freight_value)) > 1
) t;""",
    wrong_note="一单 2 个商品行 + 3 笔支付，JOIN 后变成 6 行，两侧金额分别被放大 3 倍和 2 倍，\"对不上\"的订单数虚高。",
    pitfalls=["任意两张\"一对多\"的表不能直接 JOIN 后求和，必须先各自聚合到共同粒度",
              "金额比较要设容差（这里 1 元），浮点和分期手续费都会带来小额差异",
              "只 INNER JOIN 会漏掉\"有商品没支付\"或\"有支付没商品\"的订单，对账要单独列出来"],
    followups=["怎么找出只有支付记录、没有商品明细的订单？（LEFT JOIN … WHERE i.order_id IS NULL 或 NOT EXISTS）",
               "差额主要来自分期付款（payment_installments > 1）吗？你会怎么验证？"],
))

Q.append(dict(
    id="Q15", level="高阶", title="按评价日期连续 3 天都有品质客诉订单的商家（预警规则回溯）",
    points=["Gaps & Islands：日期 − ROW_NUMBER", "先去重到天", "HAVING 取连续段长度"],
    ask="做个预警规则：某个商家如果连续 3 天每天都有品质客诉订单，就要立刻介入。历史上触发过的商家有哪些？",
    caliber=["评价日期 = 最后一次评价的提交日期（review_answer_timestamp 的日期）", "品质客诉订单 = 同 Q04（签收订单中，最后一次评价 1-3 星且命中品质问题标签）",
             "一个商家同一天有多个品质客诉订单算 1 天", "连续 3 天 = 自然日连续 ≥ 3 天"],
    assume=["一个订单含多个商家时，同时计入每个商家"],
    logic=["商家 × 评价日期去重", "日期减去组内序号，连续日期得到同一个分组值", "按分组聚合求连续天数"],
    sql=f"""WITH {RV},
{QC},
sd AS (   -- 商家 × 评价日期（去重到天）
    SELECT DISTINCT oi.seller_id, DATE(q.review_answer_timestamp) AS d
    FROM qc q
    JOIN orders o       ON o.order_id = q.order_id AND {DELIVERED}
    JOIN order_items oi ON oi.order_id = q.order_id
),
g AS (
    SELECT seller_id, d,
           DATE_SUB(d, INTERVAL ROW_NUMBER() OVER (PARTITION BY seller_id ORDER BY d) DAY) AS grp
    FROM sd
)
SELECT seller_id, MIN(d) AS start_day, MAX(d) AS end_day, COUNT(*) AS streak_days
FROM g
GROUP BY seller_id, grp
HAVING COUNT(*) >= 3
ORDER BY streak_days DESC, start_day;""",
    check=f"""WITH {RV}, {QC},
sd AS (SELECT DISTINCT oi.seller_id, DATE(q.review_answer_timestamp) d FROM qc q JOIN orders o ON o.order_id = q.order_id AND {DELIVERED}
        JOIN order_items oi ON oi.order_id = q.order_id)
SELECT COUNT(*) = COUNT(DISTINCT seller_id, d) AS ok, '商家×日期已去重（否则同一天两单会被当成连续两天）' AS note FROM sd;""",
    pitfalls=["不先去重到天，同一天 2 个品质客诉订单会让 ROW_NUMBER 多 1，连续段被算错",
              "Gaps & Islands 的核心：连续日期减去连续序号得到同一个常数",
              "规则回溯要看触发频率：触发太多运营处理不过来，太少没有预警意义"],
    followups=["如果改成\"7 天内累计 ≥ 3 个品质客诉订单\"，SQL 怎么写？（RANGE BETWEEN INTERVAL 6 DAY PRECEDING AND CURRENT ROW）",
               "这条规则历史上触发的商家，后来真的变成高风险了吗？怎么评估规则的有效性？"],
))

Q.append(dict(
    id="Q16", level="进阶", title="各州送达时长的中位数和 P90",
    points=["MySQL 没有 MEDIAN：ROW_NUMBER + COUNT() OVER 定位", "条件聚合取分位点"],
    ask="各州的送达时长，平均数被极端值拉偏了，给我中位数和 P90，只看订单最多的 10 个州。",
    caliber=["送达时长 = 签收时间 − 下单时间（天，保留小数）", "范围 = 2018-01 ~ 2018-08 下单且已签收，剔除时间倒挂",
             "P50 / P90 = 排序后第 CEIL(n × 0.5) / CEIL(n × 0.9) 个值"],
    assume=["州 = 用户收货所在州（customer_state）"],
    logic=["算每单送达天数", "按州排序编号并拿到总数", "取对应位置的值"],
    sql="""WITH d AS (
    SELECT c.customer_state,
           TIMESTAMPDIFF(SECOND, o.order_purchase_timestamp, o.order_delivered_customer_date) / 86400 AS days
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_delivered_customer_date >= o.order_purchase_timestamp
      AND o.order_purchase_timestamp >= '2018-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
),
r AS (
    SELECT customer_state, days,
           ROW_NUMBER() OVER (PARTITION BY customer_state ORDER BY days) AS rn,
           COUNT(*)     OVER (PARTITION BY customer_state)               AS n
    FROM d
)
SELECT customer_state,
       n                                                     AS orders,
       ROUND(AVG(days), 1)                                   AS avg_days,
       ROUND(MAX(CASE WHEN rn = CEIL(n * 0.5) THEN days END), 1) AS p50_days,
       ROUND(MAX(CASE WHEN rn = CEIL(n * 0.9) THEN days END), 1) AS p90_days
FROM r
GROUP BY customer_state, n
ORDER BY orders DESC
LIMIT 10;""",
    check="""SELECT SUM(p50 <= p90) = COUNT(*) AS ok, '每个州 P50 ≤ P90' AS note FROM (
    SELECT customer_state, MAX(CASE WHEN rn = CEIL(n * 0.5) THEN days END) p50, MAX(CASE WHEN rn = CEIL(n * 0.9) THEN days END) p90
    FROM (SELECT c.customer_state, TIMESTAMPDIFF(SECOND, o.order_purchase_timestamp, o.order_delivered_customer_date) / 86400 days,
                 ROW_NUMBER() OVER (PARTITION BY c.customer_state ORDER BY TIMESTAMPDIFF(SECOND, o.order_purchase_timestamp, o.order_delivered_customer_date)) rn,
                 COUNT(*) OVER (PARTITION BY c.customer_state) n
          FROM orders o JOIN customers c ON c.customer_id = o.customer_id
          WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date >= o.order_purchase_timestamp
            AND o.order_purchase_timestamp >= '2018-01-01' AND o.order_purchase_timestamp < '2018-09-01') t
    GROUP BY customer_state) x;""",
    pitfalls=["MySQL 8 没有 MEDIAN / PERCENTILE_CONT，要用排序编号定位",
              "TIMESTAMPDIFF(DAY, …) 会截断成整天，精确到小数用秒再除以 86400",
              "偶数个样本时中位数严格定义是中间两个数的平均，这里取下中位数，要在口径里说明"],
    followups=["平均数和中位数差很多说明什么？对业务汇报用哪个？", "如果要按品类看 P90 并且品类很多，性能上要注意什么？"],
))

Q.append(dict(
    id="Q17", level="基础", title="临时明细导出：某品类某月的中差评明细",
    points=["明细取数的粒度控制", "GROUP_CONCAT 合并多值", "过滤条件放在 ON 还是 WHERE"],
    ask="把 2018 年 8 月'手机通讯'品类所有 1-3 星的评价明细导给我，要订单号、下单日期、商家、星级、评价内容；没写评价内容的也要。",
    caliber=["粒度 = 一单一行", "范围 = 2018-08 下单、订单中含\"手机通讯\"品类商品、最后一次评价 1-3 星", "没有评价文字的也保留"],
    assume=["一单多商家时商家 ID 用逗号拼接", "评价内容为葡语原文，不做翻译"],
    logic=["评价去重", "关联品类筛选订单", "按订单聚合，多值字段用 GROUP_CONCAT"],
    sql=f"""WITH {RV}
SELECT
    o.order_id,
    DATE(o.order_purchase_timestamp)                                    AS purchase_date,
    rv.review_score,
    GROUP_CONCAT(DISTINCT LEFT(oi.seller_id, 8) ORDER BY oi.seller_id SEPARATOR ',') AS sellers,
    COUNT(*)                                                            AS item_rows,
    rv.review_comment_title,
    rv.review_comment_message
FROM orders o
JOIN order_items  oi ON oi.order_id = o.order_id
JOIN products     p  ON p.product_id = oi.product_id
JOIN category_dim c  ON c.product_category_name = p.product_category_name AND c.category_cn = '手机通讯'
JOIN rv              ON rv.order_id = o.order_id AND rv.review_score <= 3
WHERE o.order_purchase_timestamp >= '2018-08-01'
  AND o.order_purchase_timestamp <  '2018-09-01'
GROUP BY o.order_id, purchase_date, rv.review_score, rv.review_comment_title, rv.review_comment_message
ORDER BY rv.review_score, o.order_id;""",
    check=f"""WITH {RV}
SELECT COUNT(*) = COUNT(DISTINCT order_id) AS ok, '导出结果一单一行' AS note FROM (
    SELECT o.order_id FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
    JOIN products p ON p.product_id = oi.product_id
    JOIN category_dim c ON c.product_category_name = p.product_category_name AND c.category_cn = '手机通讯'
    JOIN rv ON rv.order_id = o.order_id AND rv.review_score <= 3
    WHERE o.order_purchase_timestamp >= '2018-08-01' AND o.order_purchase_timestamp < '2018-09-01'
    GROUP BY o.order_id) t;""",
    pitfalls=["不 GROUP BY 订单时，一单买 2 个手机壳就导出 2 行，业务方会以为是 2 条评价",
              "\"没写评价内容的也要\"——不要顺手加 review_comment_message IS NOT NULL",
              "GROUP_CONCAT 默认最长 1024 字节，超出静默截断；拼接长字段前先 SET SESSION group_concat_max_len"],
    followups=["如果业务方要的是\"订单里的手机通讯商品\"那一行，而不是整单，粒度怎么变？",
               "导出给业务的文件，你会额外附上什么说明？（口径、数据截止时间、行数、去重规则）"],
))

Q.append(dict(
    id="Q18", level="开放", title="口径对不上：看板上 2018-03 的品质客诉率 vs 业务方自己算的数",
    points=["口径差异定位", "cohort 口径 vs 事件时间口径", "用 SQL 把两种口径并排算出来"],
    ask="你看板上 2018 年 3 月的品质客诉率，和我按'3 月提交的品质问题评价 ÷ 3 月签收的订单'算出来的不一样，到底谁对？",
    caliber=["口径 A（看板）：3 月下单的签收订单中，品质客诉订单的比例（按下单月归属）", "口径 B（业务方）：分子 = 评价日期在 3 月的品质客诉订单，分母 = 签收日期在 3 月的签收订单"],
    assume=["两种口径都只统计签收订单，差异只来自时间归属"],
    logic=["把两种口径各写一段 SQL", "UNION ALL 并排输出", "解释差异来源并给出建议"],
    sql=f"""WITH {RV},
{QC},
a AS (   -- 口径 A：按下单月（cohort），分子分母是同一批订单
    SELECT COUNT(*) AS delivered, COUNT(q.order_id) AS qc_cnt
    FROM orders o
    LEFT JOIN qc q ON q.order_id = o.order_id
    WHERE {DELIVERED}
      AND o.order_purchase_timestamp >= '2018-03-01' AND o.order_purchase_timestamp < '2018-04-01'
),
b AS (   -- 口径 B：分子按评价月、分母按签收月，分子分母不是同一批订单
    SELECT
        (SELECT COUNT(*) FROM qc q JOIN orders o ON o.order_id = q.order_id
          WHERE {DELIVERED}
            AND q.review_answer_timestamp >= '2018-03-01' AND q.review_answer_timestamp < '2018-04-01') AS qc_cnt,
        (SELECT COUNT(*) FROM orders o
          WHERE {DELIVERED}
            AND o.order_delivered_customer_date >= '2018-03-01' AND o.order_delivered_customer_date < '2018-04-01') AS delivered
)
SELECT 'A 按下单月（看板口径）'          AS caliber, qc_cnt, delivered, ROUND(qc_cnt / delivered, 4) AS qc_rate FROM a
UNION ALL
SELECT 'B 分子按评价月 / 分母按签收月', qc_cnt, delivered, ROUND(qc_cnt / delivered, 4) FROM b;""",
    check="""SELECT 1 AS ok, '开放题：看结果解释差异' AS note;""",
    cross=f"""WITH {RV.replace('FROM order_reviews', 'FROM qc_interview.order_reviews')},
{QC.replace('JOIN review_tags', 'JOIN qc_interview.review_tags')}
SELECT ROUND(COUNT(q.order_id) / COUNT(*), 4) = (SELECT ROUND(qc_rate, 4) FROM qc_dw.ads_qc_kpi_month WHERE purchase_month = '2018-03') AS ok,
       '口径 A 与看板 3 月品质客诉率一致' AS note
FROM qc_interview.orders o LEFT JOIN qc q ON q.order_id = o.order_id
WHERE {DELIVERED} AND o.order_purchase_timestamp >= '2018-03-01' AND o.order_purchase_timestamp < '2018-04-01';""",
    pitfalls=["两个数都\"对\"，只是回答的问题不同：A 回答\"3 月卖出去的货质量怎么样\"，B 回答\"3 月收到了多少品质问题评价\"",
              "B 的分子里有 2 月甚至更早下单的订单，分母里也有 2 月下单、3 月才签收的订单，月初月末数据会失真",
              "口径对不上时先别争谁对，先把两种口径并排算出来，把差异拆到\"时间归属 / 范围 / 去重\"哪一项"],
    followups=["这两种口径分别适合什么场景？（A 适合评价供应商和品类质量；B 适合客服排班和实时监控）",
               "怎么避免以后再出现这种争议？（指标字典写清时间归属，看板上直接展示口径说明）"],
))

Q.append(dict(
    id="Q19", level="进阶", title="小品类月度报表：没有订单的月份也要显示 0",
    points=["递归 CTE 生成月份", "CROSS JOIN 维度骨架 + LEFT JOIN 事实", "COALESCE 补 0"],
    ask="给我'空调冷暖''电脑整机''艺术品'这三个小品类 2018 年每个月的签收订单和品质客诉订单，没有订单的月份填 0，我要直接贴到周报表格里。",
    caliber=["月份 = 2018-01 ~ 2018-08 全部 8 个月", "品类 = 指定 3 个", "签收订单 / 品质客诉订单口径同 Q04，订单 × 品类归属",
             "输出 = 3 × 8 = 24 行，缺失月份补 0"],
    assume=["品类名用中文名匹配"],
    logic=["递归 CTE 生成 8 个月份", "月份 × 品类做骨架", "LEFT JOIN 聚合结果并 COALESCE"],
    sql=f"""WITH RECURSIVE months AS (
    SELECT DATE('2018-01-01') AS m
    UNION ALL
    SELECT m + INTERVAL 1 MONTH FROM months WHERE m < '2018-08-01'
),
{RV},
{QC},
cats AS (
    SELECT category_cn FROM category_dim WHERE category_cn IN ('空调冷暖', '电脑整机', '艺术品')
),
agg AS (
    SELECT c.category_cn, DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m-01') AS m,
           COUNT(DISTINCT o.order_id)  AS delivered_cnt,
           COUNT(DISTINCT q.order_id)  AS qc_cnt
    FROM orders o
    JOIN order_items  oi ON oi.order_id = o.order_id
    JOIN products     p  ON p.product_id = oi.product_id
    JOIN category_dim c  ON c.product_category_name = p.product_category_name
    LEFT JOIN qc      q  ON q.order_id = o.order_id
    WHERE {DELIVERED}
      AND c.category_cn IN ('空调冷暖', '电脑整机', '艺术品')
      AND o.order_purchase_timestamp >= '2018-01-01' AND o.order_purchase_timestamp < '2018-09-01'
    GROUP BY c.category_cn, m
)
SELECT cats.category_cn, DATE_FORMAT(months.m, '%Y-%m') AS month,
       COALESCE(agg.delivered_cnt, 0) AS delivered_cnt,
       COALESCE(agg.qc_cnt, 0)        AS qc_cnt
FROM cats
CROSS JOIN months
LEFT JOIN agg ON agg.category_cn = cats.category_cn AND agg.m = DATE_FORMAT(months.m, '%Y-%m-01')
ORDER BY cats.category_cn, month;""",
    check="""WITH RECURSIVE months AS (SELECT DATE('2018-01-01') AS m UNION ALL SELECT m + INTERVAL 1 MONTH FROM months WHERE m < '2018-08-01')
SELECT COUNT(*) * (SELECT COUNT(*) FROM category_dim WHERE category_cn IN ('空调冷暖', '电脑整机', '艺术品')) = 24 AS ok,
       '骨架 = 8 个月 × 3 个品类 = 24 行' AS note FROM months;""",
    pitfalls=["只 GROUP BY 事实表，没有订单的月份根本不会出现，贴到周报里就错位",
              "递归 CTE 默认最多 1000 层，生成日期序列时注意上限（cte_max_recursion_depth）",
              "这里用 COUNT(DISTINCT order_id)，因为 agg 直接在商品行上关联，一单多件会重复"],
    followups=["如果不能用递归 CTE（MySQL 5.7），月份骨架怎么造？（数字辅助表 / 日历维表）",
               "周报里这 3 个品类样本很小，品质客诉率要不要展示？怎么展示才不误导？"],
))
