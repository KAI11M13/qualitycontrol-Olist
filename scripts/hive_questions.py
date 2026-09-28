"""SQL 题库的 Hive / Spark SQL 版本（5 道），与 MySQL 版逐行对账。

每道题的字段
  id                 对应 MySQL 题库编号（interview_questions.Q）
  why                选这道题的原因：迁移到 Hive 时要改什么
  changes            与 MySQL 版的差异清单
  hql                Hive 版参考答案（在 qc_hive 库上执行，${hivevar:snap_dt} = 维表最新快照）
  tol                与 MySQL 结果对账时数值列的容差
  wrong / wrong_note 可选：迁移时最容易犯的错误写法
  extra / extra_note 可选：补充对比查询
  followups          面试官追问
所有 HQL 都由 scripts/16_hive_sql.py 在本地 Spark（Hive Metastore）上实际执行。
"""


def rv(lower, upper=None, with_dt=False):
    """每单只留最后一次评价。评价表按提交日分区：下界可以裁剪，上界一般不能跟着订单窗口收紧（评价晚于下单）。"""
    cond = f"dt >= '{lower}'" + (f" AND dt < '{upper}'" if upper else "")
    dt_col = ", dt" if with_dt else ""
    return f"""rv AS (   -- 每单只留最后一次评价
    SELECT order_id, review_id, review_score{dt_col}
    FROM (
        SELECT order_id, review_id, review_score, dt,
               ROW_NUMBER() OVER (PARTITION BY order_id
                                  ORDER BY review_answer_timestamp DESC, review_id DESC) AS rn
        FROM ods_order_reviews_di
        WHERE {cond}
    ) t
    WHERE rn = 1
)"""


def qc(lower, upper=None, with_dt=False):
    cond = f"tg.dt >= '{lower}'" + (f" AND tg.dt < '{upper}'" if upper else "")
    return f"""qc AS (   -- 最后一次评价 1-3 星且命中任一品质问题标签的订单（标签表与评价同分区；再限定签收订单即为品质客诉订单）
    SELECT rv.order_id{", rv.dt AS d" if with_dt else ""}
    FROM rv
    JOIN ods_review_tags_di tg
      ON tg.review_id = rv.review_id AND tg.order_id = rv.order_id AND {cond}
    WHERE rv.review_score <= 3
      AND tg.is_fake + tg.is_defect + tg.is_mismatch + tg.is_missing + tg.is_package > 0
)"""


Q04_BODY = """dlv AS (   -- 分区裁剪：只读下单窗口内的分区；dt 本身就是下单日期，截前 7 位就是下单月
    SELECT order_id, substr(dt, 1, 7) AS month
    FROM ods_orders_di
    WHERE dt >= '2017-01-01' AND dt < '2018-09-01'
      AND order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL
)
SELECT
    d.month,
    COUNT(*)                                AS delivered_cnt,
    COUNT(q.order_id)                       AS qc_cnt,
    ROUND(COUNT(q.order_id) / COUNT(*), 4)  AS qc_rate
FROM dlv d
LEFT JOIN qc q ON q.order_id = d.order_id
GROUP BY d.month
ORDER BY d.month"""

HQ = []

HQ.append(dict(
    id="Q04",
    why="核心指标，最常跑的一条。迁移到 Hive 后，关键是两张按不同日期分区的表怎么裁剪。",
    changes=[
        "订单表按下单日分区：`WHERE dt >= '2017-01-01' AND dt < '2018-09-01'` 直接裁剪；下单月用 `substr(dt, 1, 7)`，不用再对时间戳做 `date_format`",
        "评价表按**提交日**分区：下界可以收（比下单窗口再早一个月，兜住 63 条评价时间早于下单时间的脏数据），**上界不能跟着订单窗口收**，因为评价晚于下单",
        "打标表与评价同分区，关联条件里带上 `tg.dt` 一起裁剪",
        "MySQL 的 `DATE_FORMAT(ts, '%Y-%m')` 在 Hive 里是 `date_format(ts, 'yyyy-MM')`（Java 日期格式）",
    ],
    hql="WITH " + rv("2016-12-01") + ",\n" + qc("2016-12-01") + ",\n" + Q04_BODY,
    tol=1e-4,
    wrong="WITH " + rv("2017-01-01", "2018-09-01") + ",\n" + qc("2017-01-01", "2018-09-01") + ",\n" + Q04_BODY,
    wrong_note="评价表的分区上界跟着订单窗口收到了 2018-09-01：8 月下单、9 月以后才评价的订单被漏掉，最近几个月的品质客诉率被系统性低估。"
               "按下单月归属（cohort）时，评价、退货这类\"后发生\"的表，分区范围要放宽到数据截止日。",
    followups=[
        "如果每天调度，这条 SQL 怎么改？（订单窗口改成 `${hivevar:bizdate}` 往前 N 天；评价表只需要上界 = bizdate；已出的月份会被新评价修正，所以最近 1-2 个月要每天重算、按分区 INSERT OVERWRITE）",
        "只按 `order_purchase_timestamp` 过滤、不写 `dt` 会怎样？（能算对，但全表扫描，见第 3 节的执行计划对比）",
        "评价表为什么按提交日而不是按下单日分区？（同步是增量的，评价每天新增；按下单日分区会不停改历史分区）",
    ],
))

HQ.append(dict(
    id="Q07",
    why="预警类需求，用到 LAG 和\"月份是否连续\"的判断；MySQL 的 PERIOD_DIFF 在 Hive 里没有。",
    changes=[
        "`PERIOD_DIFF(201803, 201712) = 3` → `months_between('2018-03-01', '2017-12-01') = 3`",
        "维表按天全量快照，关联时必须写 `p.dt = '${hivevar:snap_dt}'`，否则一行商品会匹配到 N 个快照",
        "商品行表与订单表同样按下单日分区，关联条件里带上 `oi.dt` 的范围，两边都裁剪",
        "MySQL 里 `COUNT(...) / COUNT(*)` 的结果是保留 4 位小数的 DECIMAL，Hive 里是 DOUBLE；"
        "\"连续上升\"要比较大小，两边精度不同时相邻两月可能一边判相等、一边判上升，所以这里显式 `ROUND(..., 4)` 与 MySQL 口径对齐（去掉 ROUND 的实跑结果见下方反例）",
        "`WINDOW w AS (...)` 子句 Hive 和 Spark 都支持，写法不变",
    ],
    hql="WITH " + rv("2016-12-01") + ",\n" + qc("2016-12-01") + """,
oc AS (   -- 订单 × 品类（同单同品类去重）
    SELECT DISTINCT o.order_id, c.category_cn, substr(o.dt, 1, 7) AS month
    FROM ods_orders_di o
    JOIN ods_order_items_di oi
      ON oi.order_id = o.order_id AND oi.dt >= '2017-01-01' AND oi.dt < '2018-09-01'
    JOIN dim_products_df p
      ON p.product_id = oi.product_id AND p.dt = '${hivevar:snap_dt}'            -- 维表只取最新快照
    JOIN dim_category_df c
      ON c.product_category_name = p.product_category_name AND c.dt = '${hivevar:snap_dt}'
    WHERE o.dt >= '2017-01-01' AND o.dt < '2018-09-01'
      AND o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
),
m AS (
    SELECT oc.category_cn, oc.month, COUNT(*) AS delivered_cnt,
           ROUND(COUNT(q.order_id) / COUNT(*), 4) AS qc_rate   -- 与 MySQL 的 4 位小数 DECIMAL 对齐
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
  AND months_between(concat(month, '-01'), concat(month_l3, '-01')) = 3   -- 四个月是连续的
ORDER BY alert_month DESC, category_cn""",
    tol=1e-4,
    wrong_note="去掉 `ROUND` 后多出了上面几条预警：这些品类在 MySQL 里有相邻两月的比率保留 4 位小数后相等，不算\"上升\"；Hive 的 DOUBLE 能分出大小，"
               "就判成了连续上升（表里的比率是输出时四舍五入的，所以看起来相等）。两种结果都能自圆其说，关键是迁移前后口径要一致，否则业务会问\"为什么新系统多报了预警\"。",
    followups=[
        "品类维表如果是拉链表（SCD2）而不是每日快照，关联条件怎么写？（`start_dt <= 下单日 AND end_dt > 下单日`，拿下单当时的品类）",
        "为什么 `months_between` 要拼成每月 1 号？（它按日期算，月末日期不同会出现小数）",
    ],
))

HQ.append(dict(
    id="Q12",
    why="高风险商家圈选。商家基准品质客诉率是一行的小表，和商家表做笛卡尔积；在 Hive 里要让它走 map join。",
    changes=[
        "`CROSS JOIN` 一行的商家基准品质客诉率表时加 `/*+ MAPJOIN(p) */`：小表广播到每个 map 端，不产生 shuffle；Spark 等价于 `BROADCAST` 提示，执行计划里是 `BroadcastNestedLoopJoin`",
        "Hive 严格模式（`hive.mapred.mode=strict`）会拦截笛卡尔积，所以这类写法要么显式 map join，要么把基准值先算好作为参数传入",
        "评价表下界收到窗口前一个月（2018-02-01），只读 9 个月左右的评价分区",
        "MySQL 的 `SUM(qc_cnt) / SUM(delivered_cnt)` 隐式保留 4 位小数，平滑品质客诉率用的是这个四舍五入后的商家基准品质客诉率；Hive 用 DOUBLE，所以平滑品质客诉率在第 4 位小数上可能差 1，名单一致",
    ],
    hql="WITH " + rv("2018-02-01") + ",\n" + qc("2018-02-01") + """,
os AS (   -- 订单 × 商家（多件订单同商家去重）
    SELECT DISTINCT o.order_id, oi.seller_id
    FROM ods_orders_di o
    JOIN ods_order_items_di oi
      ON oi.order_id = o.order_id AND oi.dt >= '2018-03-01' AND oi.dt < '2018-09-01'
    WHERE o.dt >= '2018-03-01' AND o.dt < '2018-09-01'
      AND o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
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
SELECT /*+ MAPJOIN(p) */
    s.seller_id, s.delivered_cnt, s.qc_cnt,
    ROUND(s.qc_cnt / s.delivered_cnt, 4)                         AS raw_rate,
    ROUND((s.qc_cnt + 50 * p.p_rate) / (s.delivered_cnt + 50), 4) AS smooth_rate,
    ROUND(p.p_rate, 4)                                           AS benchmark_rate
FROM s
CROSS JOIN p
WHERE s.delivered_cnt >= 30
  AND s.qc_cnt >= 3
  AND (s.qc_cnt + 50 * p.p_rate) / (s.delivered_cnt + 50) >= 2 * p.p_rate
ORDER BY smooth_rate DESC""",
    tol=1.01e-4,
    followups=[
        "如果商家表很大、基准表也不止一行（比如每个一级类目各有一个商家基准品质客诉率），还能 map join 吗？（能，类目基准表只有十几行，按类目等值关联 + 广播）",
        "`hive.auto.convert.join` 打开后还需要写 MAPJOIN 提示吗？（小表在 `hive.mapjoin.smalltable.filesize` 阈值内会自动转换；提示用于明确意图和阈值外的强制）",
    ],
))

HQ.append(dict(
    id="Q15",
    why="连续 N 天问题（Gaps & Islands），日期函数在 MySQL 和 Hive 里写法完全不同。品质客诉订单要限定签收订单，与 MySQL 版相同。",
    changes=[
        "`DATE_SUB(d, INTERVAL n DAY)` → `date_sub(d, n)`；`ROW_NUMBER()` 返回 BIGINT，`date_sub` 要 INT，需要 `CAST`",
        "评价表的分区字段 `dt` 就是评价提交日期，直接当评价日期用，不用再 `to_date(review_answer_timestamp)`",
        "打标表用 `tg.dt = rv.dt` 关联，同分区对齐",
        "日常调度时应只看近 N 天：评价表加 `dt > date_sub('${hivevar:bizdate}', 30)`；这里为了和 MySQL 版对账，扫全部历史",
    ],
    hql="WITH " + rv("2016-01-01", with_dt=True).replace("WHERE dt >= '2016-01-01'", "-- 全量；日常调度加 WHERE dt > date_sub('${hivevar:bizdate}', 30)") + """,
qc AS (
    SELECT rv.order_id, rv.dt AS d
    FROM rv
    JOIN ods_review_tags_di tg
      ON tg.review_id = rv.review_id AND tg.order_id = rv.order_id AND tg.dt = rv.dt   -- 同分区对齐
    WHERE rv.review_score <= 3
      AND tg.is_fake + tg.is_defect + tg.is_mismatch + tg.is_missing + tg.is_package > 0
),
sd AS (   -- 商家 × 评价日期（去重到天），只保留签收订单
    SELECT DISTINCT oi.seller_id, q.d
    FROM qc q
    JOIN ods_orders_di o
      ON o.order_id = q.order_id AND o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
    JOIN ods_order_items_di oi ON oi.order_id = q.order_id
),
g AS (
    SELECT seller_id, d,
           date_sub(d, CAST(ROW_NUMBER() OVER (PARTITION BY seller_id ORDER BY d) AS INT)) AS grp
    FROM sd
)
SELECT seller_id, MIN(d) AS start_day, MAX(d) AS end_day, COUNT(*) AS streak_days
FROM g
GROUP BY seller_id, grp
HAVING COUNT(*) >= 3
ORDER BY streak_days DESC, start_day""",
    tol=0,
    followups=[
        "如果要\"连续 3 天且每天至少 2 个品质客诉订单\"？（先按商家 × 天聚合、HAVING ≥ 2，再做同样的分组）",
        "商品行表没按评价日分区，这里 `JOIN ods_order_items_di` 会全表扫描，怎么优化？（先把近 30 天的品质客诉订单算出来，订单号去重后作为小表 map join；或者在 DWD 建一张按评价日期分区的订单宽表）",
    ],
))

HQ.append(dict(
    id="Q16",
    why="分位数。MySQL 没有内置函数只能手写，Hive 有 `percentile` 和 `percentile_approx`，但三者的定义不一样。",
    changes=[
        "`TIMESTAMPDIFF(SECOND, a, b)` → `unix_timestamp(b) - unix_timestamp(a)`",
        "客户维表按天快照，关联时限定 `c.dt = '${hivevar:snap_dt}'`",
        "主答案保留和 MySQL 相同的\"最近秩\"写法（`ROW_NUMBER` + `CEIL(n × p)`），便于对账；下方补充内置函数版",
    ],
    hql="""WITH d AS (
    SELECT c.customer_state,
           (unix_timestamp(o.order_delivered_customer_date) - unix_timestamp(o.order_purchase_timestamp)) / 86400 AS days
    FROM ods_orders_di o
    JOIN dim_customers_df c
      ON c.customer_id = o.customer_id AND c.dt = '${hivevar:snap_dt}'
    WHERE o.dt >= '2018-01-01' AND o.dt < '2018-09-01'
      AND o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_delivered_customer_date >= o.order_purchase_timestamp
),
r AS (
    SELECT customer_state, days,
           ROW_NUMBER() OVER (PARTITION BY customer_state ORDER BY days) AS rn,
           COUNT(*)     OVER (PARTITION BY customer_state)               AS n
    FROM d
)
SELECT customer_state,
       n                                                          AS orders,
       ROUND(AVG(days), 1)                                        AS avg_days,
       ROUND(MAX(CASE WHEN rn = CEIL(n * 0.5) THEN days END), 1)  AS p50_days,
       ROUND(MAX(CASE WHEN rn = CEIL(n * 0.9) THEN days END), 1)  AS p90_days
FROM r
GROUP BY customer_state, n
ORDER BY orders DESC
LIMIT 10""",
    tol=0.1001,
    extra="""WITH d AS (
    SELECT c.customer_state,
           (unix_timestamp(o.order_delivered_customer_date) - unix_timestamp(o.order_purchase_timestamp)) / 86400 AS days
    FROM ods_orders_di o
    JOIN dim_customers_df c
      ON c.customer_id = o.customer_id AND c.dt = '${hivevar:snap_dt}'
    WHERE o.dt >= '2018-01-01' AND o.dt < '2018-09-01'
      AND o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_delivered_customer_date >= o.order_purchase_timestamp
)
SELECT customer_state,
       COUNT(*)                                   AS orders,
       ROUND(percentile(days, 0.9), 2)            AS p90_interp,   -- Spark：精确值，线性插值；Hive 的 percentile 只接受整数列
       ROUND(percentile_approx(days, 0.9), 2)     AS p90_approx,   -- 近似算法，返回样本中的某个值；大数据量下内存可控
       ROUND(percentile(CAST(days AS BIGINT), 0.9), 2) AS p90_int_days  -- Hive 写法：先取整成天再算，精度只到天
FROM d
GROUP BY customer_state
ORDER BY orders DESC
LIMIT 10""",
    extra_note="三种\"P90\"的定义不同：最近秩（主答案）取排序后第 ⌈0.9n⌉ 个值；`percentile` 在相邻两个值之间线性插值；"
               "`percentile_approx` 用近似算法返回样本中的某个值，数据量大时内存可控。Hive 的 `percentile` 只接受整数列，"
               "所以 Hive 上要么先取整（精度只到天），要么用 `percentile_approx`。交付时要写明用的是哪种。",
    wrong="""WITH d AS (
    SELECT c.customer_state,
           (unix_timestamp(o.order_delivered_customer_date) - unix_timestamp(o.order_purchase_timestamp)) / 86400 AS days
    FROM ods_orders_di o
    JOIN dim_customers_df c ON c.customer_id = o.customer_id      -- ❌ 没有限定快照分区
    WHERE o.dt >= '2018-01-01' AND o.dt < '2018-09-01'
      AND o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_delivered_customer_date >= o.order_purchase_timestamp
)
SELECT customer_state, COUNT(*) AS orders, ROUND(AVG(days), 1) AS avg_days
FROM d
GROUP BY customer_state
ORDER BY orders DESC
LIMIT 5""",
    wrong_note="客户维表存了两天的全量快照，不限定 `dt` 时每个订单匹配到 2 行：订单数翻倍，而平均值和分位数看起来完全正常，很难发现。"
               "维表关联一律写 `dt = 最新快照`（或拉链表的有效期条件），并在自检里核对订单数。",
    followups=[
        "10 亿行上算分位数，`percentile` 会有什么问题？（要把每组的全部值放进内存，容易 OOM；用 `percentile_approx`，第三个参数控制精度和内存）",
        "业务问\"中位数\"时，你交付哪个版本？（写明定义；时效类指标常用最近秩或近似值，差异通常在 0.1 天以内）",
    ],
))


# Q07 反例：不对比率做 ROUND，与 MySQL 的 4 位小数 DECIMAL 精度不一致
_q07 = next(q for q in HQ if q["id"] == "Q07")
_q07["wrong"] = _q07["hql"].replace("ROUND(COUNT(q.order_id) / COUNT(*), 4) AS qc_rate   -- 与 MySQL 的 4 位小数 DECIMAL 对齐",
                                    "COUNT(q.order_id) / COUNT(*) AS qc_rate   -- ❌ DOUBLE，与 MySQL 精度不一致")
assert _q07["wrong"] != _q07["hql"]
