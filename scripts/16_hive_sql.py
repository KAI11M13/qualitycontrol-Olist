"""Step 16：SQL 题库的 Hive / Spark SQL 版本，在本地 Spark + Hive Metastore 上实跑，并与 MySQL 版逐行对账。

流程
  1. 从 MySQL 面试库 qc_interview 读出原始表，注册为 Spark 临时视图 src_*（模拟同步工具落地的源表）
  2. 执行 sql/hive/00_ddl.hql（分区表建表）和 01_load.hql（动态分区装载，DISTRIBUTE BY dt 控制文件数）
  3. 逐题执行 Hive 版（scripts/hive_questions.py），与 MySQL 版答案对账；抓执行计划里的分区裁剪信息
  4. 数据倾斜与小文件演示（sql/hive/90_skew_demo.hql）
输出：sql/hive/Qxx_*.hql、docs/08_HiveQL与SparkSQL版本.md
依赖：Java 17+、pip install -r requirements-hive.txt（pyspark、pyarrow）。没有 Spark 时本步骤跳过。
"""
import os
import re
import warnings
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from common import ROOT, connect
from hive_questions import HQ
from interview_questions import Q

warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
HIVE_DIR = ROOT / "sql" / "hive"
SPARK_HOME_DIR = ROOT / ".spark"          # 本地 warehouse 与 metastore（不入库）
SNAP_DT, PREV_DT = "2018-10-30", "2018-10-29"
MYSQL_Q = {q["id"]: q for q in Q}


def spark_session():
    try:
        from pyspark.sql import SparkSession
    except ImportError:
        return None
    SPARK_HOME_DIR.mkdir(exist_ok=True)
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    spark = (SparkSession.builder.master("local[4]").appName("qc_hive")
             .config("spark.ui.enabled", "false")
             .config("spark.ui.showConsoleProgress", "false")
             .config("spark.sql.warehouse.dir", str(SPARK_HOME_DIR / "warehouse"))
             .config("spark.hadoop.javax.jdo.option.ConnectionURL",
                     f"jdbc:derby:;databaseName={SPARK_HOME_DIR / 'metastore_db'};create=true")
             .config("spark.driver.extraJavaOptions", f"-Dderby.system.home={SPARK_HOME_DIR}")
             .config("spark.sql.session.timeZone", "UTC")
             .config("spark.sql.ansi.enabled", "false")          # Spark 4 默认 ANSI；Hive 不是，关掉以贴近 Hive 语义
             .config("spark.sql.shuffle.partitions", "8")
             .config("spark.sql.execution.arrow.pyspark.enabled", "true")
             .enableHiveSupport().getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def statements(text):
    """按行尾分号切分 HQL 脚本（脚本里的注释不含分号换行）。"""
    body = "\n".join(line for line in text.splitlines() if not line.strip().startswith("--"))
    return [s.strip() for s in re.split(r";[ \t]*(?:--[^\n]*)?(?:\n|$)", body) if s.strip()]


def load_sources(spark):
    conn = connect(db="qc_interview")
    tables = ["orders", "order_items", "order_reviews", "review_tags", "products", "sellers", "customers", "category_dim"]
    counts = {}
    for t in tables:
        df = pd.read_sql(f"SELECT * FROM {t}", conn)
        for c in df.columns:
            if df[c].dtype == float and df[c].dropna().apply(float.is_integer).all() and not c.startswith(("price", "freight")):
                df[c] = df[c].astype("Int64")
            if df[c].dtype == object and len(df[c].dropna()) and type(df[c].dropna().iloc[0]).__name__ == "Decimal":
                df[c] = df[c].astype(float)
        spark.createDataFrame(df).createOrReplaceTempView(f"src_{t}")
        counts[t] = len(df)
    conn.close()
    return counts


def mysql_df(sql):
    conn = connect(db="qc_interview")
    with conn.cursor() as cur:
        cur.execute(sql)
        rows, cols = cur.fetchall(), [d[0] for d in cur.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols)


def norm(df):
    out = df.copy()
    for c in out.columns:
        s = out[c]
        num = pd.to_numeric(s, errors="coerce")
        if s.notna().any() and num[s.notna()].notna().all():
            out[c] = num.astype(float)
        else:
            out[c] = s.map(lambda v: None if v is None or (isinstance(v, float) and np.isnan(v)) else str(v)[:19])
    return out


def reconcile(h, m, tol):
    """Hive 结果与 MySQL 结果逐行比较：列名、行数一致；按全部列排序后，数值列误差 ≤ tol，其余列相等。"""
    if list(h.columns) != list(m.columns):
        return False, f"列不一致：{list(h.columns)} vs {list(m.columns)}"
    if len(h) != len(m):
        return False, f"行数不一致：Hive {len(h)} 行，MySQL {len(m)} 行"
    h, m = norm(h), norm(m)
    key = [c for c in h.columns if h[c].dtype == object] or list(h.columns)
    h = h.sort_values(key, na_position="first").reset_index(drop=True)
    m = m.sort_values(key, na_position="first").reset_index(drop=True)
    worst = 0.0
    for c in h.columns:
        if h[c].dtype == float and m[c].dtype == float:
            d = (h[c] - m[c]).abs().max()
            worst = max(worst, 0 if np.isnan(d) else d)
            if d > tol + 1e-9:
                return False, f"列 {c} 最大差 {d:.6f} > 容差 {tol}"
        elif not (h[c].fillna("∅") == m[c].fillna("∅")).all():
            bad = (h[c].fillna("∅") != m[c].fillna("∅")).idxmax()
            return False, f"列 {c} 第 {bad} 行不一致：{h[c][bad]} vs {m[c][bad]}"
    return True, f"{len(h)} 行 × {len(h.columns)} 列逐行一致" + (f"（数值最大差 {worst:.4g}，容差 {tol}）" if worst else "（完全相同）")


def scan_info(spark, sql, parts):
    """从物理计划里取每张分区表实际读取的分区数（InMemoryFileIndex(N paths)）。"""
    plan = spark.sql("EXPLAIN " + sql).collect()[0][0]
    info = []
    pat = r"FileScan \w+ spark_catalog\.qc_hive\.(\w+)\[.*?Location: (InMemoryFileIndex|CatalogFileIndex)\((\d+) paths\).*?PartitionFilters: \[(.*?)\]"
    for m in re.finditer(pat, plan):
        tbl, kind, pf = m.group(1), m.group(2), re.sub(r"#\d+", "", m.group(4))
        n = parts.get(tbl, 0) if kind == "CatalogFileIndex" else int(m.group(3))   # CatalogFileIndex = 没有分区过滤，读全部分区
        info.append((tbl, n, parts.get(tbl, 0), pf))
    joins = sorted(set(re.findall(r"(Broadcast\w*Join|SortMergeJoin|ShuffledHashJoin)", plan)))
    return info, joins


def md_table(df, max_rows=10):
    def fmt(v):
        if isinstance(v, float) and v == v and v.is_integer() and abs(v) >= 1:
            return str(int(v))
        if isinstance(v, float):
            return f"{v:.4f}".rstrip("0").rstrip(".")
        return "" if v is None else str(v)[:36]
    shown = df.head(max_rows)
    lines = ["| " + " | ".join(shown.columns) + " |", "|" + "---|" * len(shown.columns)]
    lines += ["| " + " | ".join(fmt(v) for v in r) + " |" for r in shown.itertuples(index=False)]
    return "\n".join(lines)


def main():
    spark = spark_session()
    if spark is None:
        print("  未安装 pyspark，跳过 Hive 版（pip install -r requirements-hive.txt，需要 Java 17+）")
        return
    t0 = time.time()
    spark.sql(f"SET hivevar:snap_dt={SNAP_DT}")
    spark.sql(f"SET hivevar:prev_dt={PREV_DT}")
    counts = load_sources(spark)
    for f in ["00_ddl.hql", "01_load.hql"]:
        for st in statements((HIVE_DIR / f).read_text(encoding="utf-8")):
            spark.sql(st)
    spark.sql("USE qc_hive")
    tables = [r.tableName for r in spark.sql("SHOW TABLES IN qc_hive").collect() if not r.isTemporary]
    parts = {t: spark.sql(f"SHOW PARTITIONS qc_hive.{t}").count() for t in tables}
    rows = {t: spark.table(f"qc_hive.{t}").count() for t in tables}
    files = {t: sum(1 for _ in (SPARK_HOME_DIR / "warehouse" / "qc_hive.db" / t).rglob("*") if _.is_file() and not _.name.startswith((".", "_")))
             for t in tables}
    print(f"  Hive 库 qc_hive 装载完成（{time.time() - t0:.0f}s）：" + "，".join(f"{t} {parts[t]} 分区" for t in tables))
    assert rows["ods_orders_di"] == counts["orders"] and rows["ods_order_reviews_di"] == counts["order_reviews"]
    assert rows["dim_products_df"] == 2 * counts["products"]

    results = []
    for old in HIVE_DIR.glob("Q[0-9]*.hql"):  # 题目改名后不留旧文件
        old.unlink()
    for hq in HQ:
        mq = MYSQL_Q[hq["id"]]
        hdf = spark.sql(hq["hql"]).toPandas()
        mdf = mysql_df(mq["sql"])
        ok, note = reconcile(hdf, mdf, hq["tol"])
        info, joins = scan_info(spark, hq["hql"], parts)
        r = dict(hq=hq, mq=mq, ans=hdf, ok=ok, note=note, scan=info, joins=joins)
        if hq.get("wrong"):
            r["wrong_ans"] = spark.sql(hq["wrong"]).toPandas()
        if hq.get("extra"):
            r["extra_ans"] = spark.sql(hq["extra"]).toPandas()
        results.append(r)
        print(f"  {'PASS' if ok else 'FAIL'} {hq['id']} {mq['title']}：{note}；"
              + "；".join(f"{t} 读 {n}/{tot} 分区" for t, n, tot, _ in info))
        slug = re.sub(r"[^0-9A-Za-z一-龥]+", "_", mq["title"]).strip("_")[:20]
        (HIVE_DIR / f"{hq['id']}_{slug}.hql").write_text(
            f"-- {hq['id']} {mq['title']}（Hive / Spark SQL 版）\n-- 业务方原话：{mq['ask']}\n"
            f"-- 维表快照：SET hivevar:snap_dt={SNAP_DT};\nUSE qc_hive;\n\n{hq['hql']};\n", encoding="utf-8")

    # Q04 反例：只按时间戳过滤、不写分区条件 → 全表扫描
    no_prune = "SELECT COUNT(*) AS cnt FROM ods_orders_di WHERE order_purchase_timestamp >= '2018-03-01' AND order_purchase_timestamp < '2018-09-01'"
    with_prune = "SELECT COUNT(*) AS cnt FROM ods_orders_di WHERE dt >= '2018-03-01' AND dt < '2018-09-01'"
    prune_demo = dict(
        no=(no_prune, spark.sql(no_prune).collect()[0][0], scan_info(spark, no_prune, parts)[0]),
        yes=(with_prune, spark.sql(with_prune).collect()[0][0], scan_info(spark, with_prune, parts)[0]))

    skew = skew_demo(spark, parts)
    spark.stop()
    write_doc(results, parts, rows, files, prune_demo, skew)
    fails = [r for r in results if not r["ok"]]
    if fails or not skew["salt_ok"] or not skew["null_ok"]:
        raise SystemExit(f"Hive 版对账未通过：{[r['hq']['id'] for r in fails]}")
    print(f"  {len(results)}/{len(results)} 道 Hive 版与 MySQL 版对账一致 → docs/08_HiveQL与SparkSQL版本.md（用时 {time.time() - t0:.0f}s）")


def skew_demo(spark, parts):
    sts = statements((HIVE_DIR / "90_skew_demo.hql").read_text(encoding="utf-8"))
    res = [spark.sql(s).toPandas() for s in sts[1:]]   # 第一句是 USE
    diag, direct, salted, null_share, join_plain, join_rand = res
    d = direct.set_index("customer_state").sort_index()
    s = salted.set_index("customer_state").sort_index()
    salt_ok = d.equals(s)
    null_ok = join_plain.equals(join_rand)
    # 小文件：不做 DISTRIBUTE BY 时每个分区的文件数
    spark.sql("DROP TABLE IF EXISTS qc_hive.tmp_orders_nodist")
    spark.sql("CREATE TABLE qc_hive.tmp_orders_nodist LIKE qc_hive.ods_orders_di")
    spark.sql("INSERT OVERWRITE TABLE qc_hive.tmp_orders_nodist PARTITION (dt) "
              "SELECT /*+ REPARTITION(16) */ order_id, customer_id, order_status, order_purchase_timestamp, order_approved_at, "
              "order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date, "
              "date_format(order_purchase_timestamp, 'yyyy-MM-dd') AS dt FROM src_orders")
    base = SPARK_HOME_DIR / "warehouse" / "qc_hive.db"
    nfiles = lambda t: sum(1 for p in (base / t).rglob("*") if p.is_file() and not p.name.startswith((".", "_")))
    small = dict(dist=nfiles("ods_orders_di"), nodist=nfiles("tmp_orders_nodist"), parts=parts["ods_orders_di"])
    spark.sql("DROP TABLE IF EXISTS qc_hive.tmp_orders_nodist")
    bplan = spark.sql("EXPLAIN SELECT /*+ BROADCAST(c) */ o.order_id, c.customer_state FROM qc_hive.ods_orders_di o "
                      f"JOIN qc_hive.dim_customers_df c ON c.customer_id = o.customer_id AND c.dt = '{SNAP_DT}'").collect()[0][0]
    return dict(sql=sts[1:], diag=diag, direct=direct, salted=salted, salt_ok=salt_ok, null_share=null_share,
                join_plain=join_plain, join_rand=join_rand, null_ok=null_ok, small=small,
                broadcast="BroadcastHashJoin" in bplan)


def write_doc(results, parts, rows, files, prune_demo, skew):
    L = [
        "# 08 HiveQL / Spark SQL 版本：5 道题的迁移与实跑",
        "",
        "> 大厂数仓多在 Hive / Spark 上。这里挑了题库里 5 道有代表性的题，按 Hive 分区表的方式重写，"
        "在本地 **Spark SQL（Hive Metastore，Hive 兼容语法）** 上实际执行，并与 MySQL 版答案**逐行对账**。",
        ">",
        "> 说明：没有真实 Hive 集群，SQL 按 Hive 2.x 语法编写、在 Spark 上验证；Spark 4 默认的 ANSI 模式已关闭以贴近 Hive 语义。"
        "Hive 与 Spark 行为不同的地方在文中单独标出。本地单机、10 万级数据量看不出性能差异，所以性能相关的部分讲原理、验证写法等价。",
        "",
        "- 重新生成：`python scripts/16_hive_sql.py`（需要 Java 17+ 和 `pip install -r requirements-hive.txt`）",
        "- 建表 / 装载：[`sql/hive/00_ddl.hql`](../sql/hive/00_ddl.hql)、[`sql/hive/01_load.hql`](../sql/hive/01_load.hql)；每题答案：`sql/hive/Qxx_*.hql`",
        "",
        "## 1. 表设计：分区是 Hive 取数的第一件事",
        "",
        "| 表 | 分区字段 dt 的含义 | 分区数 | 行数 | 文件数 |",
        "|---|---|---|---|---|",
    ]
    meaning = {"ods_orders_di": "下单日期", "ods_order_items_di": "下单日期（跟随订单）", "ods_order_reviews_di": "评价提交日期",
               "ods_review_tags_di": "评价提交日期（与评价同分区）"}
    for t in sorted(parts, key=lambda x: (not x.startswith("ods"), x)):
        L.append(f"| `{t}` | {meaning.get(t, '快照日期（存了 ' + PREV_DT + '、' + SNAP_DT + ' 两天，内容相同）')} | {parts[t]} | {rows[t]:,} | {files[t]} |")
    L += [
        "",
        "- **事实表按业务日期增量分区（_di）**：订单按下单日，评价按提交日。商品行跟随订单分区，订单和商品行关联时两边都能裁剪。",
        "- **维表每天全量快照（_df）**：取数时必须写 `dt = 最新快照`，否则每天一份，行数按快照天数翻倍（Q16 的反例实跑了这个错误）。",
        f"- **装载时 `DISTRIBUTE BY dt`**：同一分区的数据进同一个 reducer，每个分区一个文件。对照实验：同一份订单数据不做 `DISTRIBUTE BY`、按 16 个任务写入，"
        f"{skew['small']['parts']} 个分区产生了 **{skew['small']['nodist']} 个文件**，做了之后是 **{skew['small']['dist']} 个**。小文件多会拖慢 NameNode 和后续查询。",
        "",
        "## 2. MySQL → Hive 写法对照",
        "",
        "| 场景 | MySQL 8.0 | Hive / Spark SQL |",
        "|---|---|---|",
        "| 日期格式化 | `DATE_FORMAT(ts, '%Y-%m')` | `date_format(ts, 'yyyy-MM')`（Java 格式）；分区表直接 `substr(dt, 1, 7)` |",
        "| 日期加减 | `DATE_SUB(d, INTERVAL 3 DAY)` | `date_sub(d, 3)`；按月用 `add_months(d, n)` |",
        "| 月份差 | `PERIOD_DIFF(201803, 201712)` | `months_between('2018-03-01', '2017-12-01')` |",
        "| 时间差 | `TIMESTAMPDIFF(SECOND, a, b)` | `unix_timestamp(b) - unix_timestamp(a)`；按天 `datediff(b, a)` |",
        "| 条件计数 | `SUM(cond)`（布尔当 0/1） | `SUM(IF(cond, 1, 0))` 或 `SUM(CASE WHEN ...)`，布尔不能直接求和 |",
        "| 除法精度 | `7 / 2 = 3.5000`：DECIMAL，默认保留 4 位小数 | `7 / 2 = 3.5`：DOUBLE；比较大小前注意两边精度（见 Q07） |",
        "| 分位数 | 无内置，`ROW_NUMBER` 手写 | `percentile`（精确，Hive 只收整数列）、`percentile_approx`（近似） |",
        "| 排序 | `ORDER BY` | `ORDER BY` 全局排序只用一个 reducer；`SORT BY` 分区内排序；`DISTRIBUTE BY` 控制分发；`CLUSTER BY` = 同字段的两者 |",
        "| 修改数据 | `UPDATE` / `DELETE` | 一般不改行，按分区 `INSERT OVERWRITE` 重算 |",
        "| 笛卡尔积 | `CROSS JOIN` | 严格模式会拦截；小表用 `MAPJOIN` / `BROADCAST` 提示 |",
        "| 去重计数 | `COUNT(DISTINCT x)` | 大表上改写成先 `GROUP BY x` 再 `COUNT(*)`，避免单个 reducer 去重 |",
        "",
        "## 3. 分区裁剪：写 `dt` 和不写 `dt` 的区别",
        "",
        "同样是\"2018 年 3-8 月下单的订单数\"，两种写法结果相同，但读取的分区数不同（取自执行计划 `InMemoryFileIndex(N paths)`）：",
        "",
        "| 写法 | 结果 | 读取分区 |",
        "|---|---|---|",
    ]
    for k, lab in [("no", "按时间戳过滤：`WHERE order_purchase_timestamp >= '2018-03-01' AND ... < '2018-09-01'`"),
                   ("yes", "按分区过滤：`WHERE dt >= '2018-03-01' AND dt < '2018-09-01'`")]:
        _, cnt, info = prune_demo[k]
        L.append(f"| {lab} | {cnt:,} | {info[0][1]} / {info[0][2]} |")
    L += ["", "按时间戳过滤会扫全表。Hive 严格模式（`hive.mapred.mode=strict`）下，查询分区表不带分区条件会直接报错。", ""]

    L += ["## 4. 五道题的 Hive 版", "",
          "| 编号 | 题目 | 迁移要点 | 对账 |", "|---|---|---|---|"]
    for r in results:
        L.append(f"| [{r['hq']['id']}](#{r['hq']['id'].lower()}-hive) | {r['mq']['title']} | {r['hq']['why']} | {'✅' if r['ok'] else '❌'} |")
    L.append("")
    for r in results:
        hq, mq = r["hq"], r["mq"]
        L += [f"### {hq['id']}-hive", f"#### {mq['title']}", "", f"> 💬 **业务方原话**：\"{mq['ask']}\"（MySQL 版见 [05_SQL面试题库.md](05_SQL面试题库.md#{hq['id'].lower()})）", "",
              f"**为什么选这道**：{hq['why']}", "", "**与 MySQL 版的差异**", "", *[f"- {c}" for c in hq["changes"]], "",
              "**Hive / Spark SQL 版**", "", "```sql", hq["hql"].replace("${hivevar:snap_dt}", "${hivevar:snap_dt}"), "```", "",
              f"**实跑结果**（共 {len(r['ans'])} 行{'，展示前 10 行' if len(r['ans']) > 10 else ''}）", "", md_table(r["ans"]), "",
              f"**与 MySQL 版对账**：{'✅' if r['ok'] else '❌'} {r['note']}", ""]
        if r["scan"]:
            L += ["**执行计划里的分区裁剪**", "", "| 表 | 读取分区 / 总分区 | 分区过滤条件 |", "|---|---|---|"]
            seen = set()
            for t, n, tot, pf in r["scan"]:
                if (t, n) in seen:
                    continue
                seen.add((t, n))
                L.append(f"| `{t}` | {n} / {tot} | `{pf or '无'}` |")
            L.append("")
        if r["joins"]:
            L += [f"关联方式：{'、'.join(f'`{j}`' for j in r['joins'])}", ""]
        if "extra_ans" in r:
            L += ["**补充：内置分位数函数对比**", "", "```sql", hq["extra"], "```", "", md_table(r["extra_ans"]), "", f"> {hq['extra_note']}", ""]
        if "wrong_ans" in r:
            L += ["**❌ 迁移时最容易犯的错**", "", "```sql", hq["wrong"], "```", ""]
            if hq["id"] == "Q04":
                w = r["wrong_ans"].set_index("month")
                a = r["ans"].set_index("month")
                cmp_ = pd.DataFrame({"正确 qc_cnt": a.qc_cnt, "错误 qc_cnt": w.qc_cnt, "正确 qc_rate": a.qc_rate, "错误 qc_rate": w.qc_rate}).tail(4)
                L += ["错误写法与正确写法的最近 4 个月对比：", "", md_table(cmp_.reset_index()), ""]
            elif hq["id"] == "Q07":
                keys = set(map(tuple, r["ans"][["category_cn", "alert_month"]].values))
                extra = r["wrong_ans"][[tuple(v) not in keys for v in r["wrong_ans"][["category_cn", "alert_month"]].values]]
                L += [f"错误写法返回 {len(r['wrong_ans'])} 行，正确写法（与 MySQL 一致）{len(r['ans'])} 行。多出来的是：", "", md_table(extra), ""]
            else:
                L += ["错误写法的实跑结果：", "", md_table(r["wrong_ans"]), ""]
            L += [f"> {hq['wrong_note']}", ""]
        L += ["**追问**", "", *[f"- {f}" for f in hq["followups"]], ""]

    diag = skew["diag"]
    L += [
        "## 5. 数据倾斜：怎么发现，怎么处理",
        "",
        "倾斜 = 某几个 key 的数据量远大于其他 key，shuffle 后落到同一个 reducer / task 上，整个作业等它一个。",
        "",
        "**第一步：诊断**（先看 key 分布，别急着调参）。这份数据里客户州分布就很不均匀：",
        "",
        "```sql", skew["sql"][0], "```", "", md_table(diag), "",
        f"圣保罗州（SP）一个 key 占了 {diag.share.iloc[0]:.1%} 的订单，是 {len(skew['direct'])} 个州平均水平（{1 / len(skew['direct']):.1%}）的 "
        f"{diag.share.iloc[0] * len(skew['direct']):.1f} 倍。按州聚合或按州关联时，SP 所在的任务最慢，整个作业都要等它。",
        "",
        "**第二步：按场景处理**",
        "",
        "| 场景 | 做法 | Hive 参数 / 写法 | Spark |",
        "|---|---|---|---|",
        "| 大表关联小表 | 小表广播到每个 map，不 shuffle | `/*+ MAPJOIN(t) */`；`hive.auto.convert.join=true` | `/*+ BROADCAST(t) */`；`spark.sql.autoBroadcastJoinThreshold` |",
        "| 聚合时 key 倾斜 | map 端预聚合；两阶段聚合（加盐） | `hive.map.aggr=true`；`hive.groupby.skewindata=true` | AQE 合并 / 拆分分区 |",
        "| 关联时 key 倾斜 | 倾斜 key 单独处理再 UNION；或给大表加盐、小表扩容 N 倍 | `hive.optimize.skewjoin=true`、`hive.skewjoin.key` | `spark.sql.adaptive.skewJoin.enabled=true` |",
        "| 关联键大量为空 | 空值不参与关联，或把空值打散成随机值 | `CASE WHEN k IS NULL THEN concat('null_', rand()) ELSE k END` | 同左 |",
        "| 类型不一致 | 关联键类型不同会被转成同一种类型，转换失败的都变成 NULL 挤在一起 | 关联前统一类型 | 同左 |",
        "",
        "**两阶段聚合（加盐）**：第一阶段给 key 拼一个随机数，把 SP 打散到 8 个组里局部聚合；第二阶段去掉随机数再汇总。实跑验证结果与直接聚合一致：",
        "",
        "```sql", skew["sql"][2], "```", "",
        f"→ {'✅' if skew['salt_ok'] else '❌'} 与直接 `GROUP BY customer_state` 的结果逐州一致（{len(skew['direct'])} 个州）。",
        "",
        "**空值 key 打散**：",
        "",
        "```sql", skew["sql"][3], "```", "", md_table(skew["null_share"]), "",
        "610 个商品没有品类，关联品类维表时这些行的关联键都是 NULL。Hive 会把它们发到同一个 reducer（反正也关联不上）。把 NULL 换成随机字符串后，"
        "数据被打散，结果不变：",
        "",
        "```sql", skew["sql"][5], "```", "",
        f"→ {'✅' if skew['null_ok'] else '❌'} 与不打散的写法结果一致（{md_inline(skew['join_rand'])}）。",
        "",
        f"**广播关联**：订单表关联客户维表时加 `/*+ BROADCAST(c) */`，执行计划为 `{'BroadcastHashJoin' if skew['broadcast'] else '未命中广播'}`，小表不参与 shuffle。",
        "",
        "## 6. 面试时怎么讲",
        "",
        "> \"MySQL 版是我实跑过的；迁到 Hive 时我主要改三类东西：一是**分区**，事实表按业务日期分区、维表取最新快照，所有查询先写 dt；"
        "二是**函数**，日期函数、分位数、除法精度这些在两边不一样；三是**执行**，小表走 map join、大 key 要防倾斜、写表时用 DISTRIBUTE BY 控制文件数。"
        "5 道题的 Hive 版我在 Spark 上跑过，和 MySQL 的结果逐行对得上。\"",
        "",
    ]
    (ROOT / "docs" / "08_HiveQL与SparkSQL版本.md").write_text("\n".join(L), encoding="utf-8")


def md_inline(df):
    return "，".join(f"{c} = {df[c].iloc[0]:,}" for c in df.columns)


if __name__ == "__main__":
    main()
