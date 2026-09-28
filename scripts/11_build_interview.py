"""Step 11：搭建 SQL 面试库 qc_interview，并逐题实跑题库，生成题库文档。

面试库刻意保留原始数据的"脏"：评价表有重复、商品缺品类、订单时间倒挂……
这些正是业务取数时要清洗的地方，也是题目的考点。

输出
  sql/interview/00_schema.sql            面试库建表语句
  sql/interview/Qxx_*.sql                每道题的参考答案
  docs/05_SQL面试题库.md                  答案版（口径 / SQL / 实跑结果 / 自检 / 错误写法 / 追问）
  docs/05_SQL面试题_练习版.md             题目版（只有业务原话、用表提示、输出要求）
"""
import re
import time

import pandas as pd

from common import ROOT, connect
from complaint_rules import tag_text
from interview_questions import Q

DB = "qc_interview"
OUT_SQL = ROOT / "sql" / "interview"

TABLES = [
    # 面试库表名, 来源, 主键/索引, 一行代表什么
    ("orders", "vip_qc.ods_orders", "PRIMARY KEY (order_id), KEY (customer_id)", "一个订单"),
    ("order_items", "vip_qc.ods_order_items", "PRIMARY KEY (order_id, order_item_id), KEY (product_id), KEY (seller_id)",
     "订单里的一个商品行（同一商品买 2 件 = 2 行）"),
    ("order_reviews", "vip_qc.ods_order_reviews", "PRIMARY KEY (review_id, order_id), KEY (order_id)",
     "一条评价（⚠ 同一订单可能有多条）"),
    ("order_payments", "vip_qc.ods_order_payments", "PRIMARY KEY (order_id, payment_sequential)", "一笔支付（组合支付一单多行）"),
    ("products", "vip_qc.ods_products", "PRIMARY KEY (product_id)", "一个商品（⚠ 610 个商品缺品类）"),
    ("sellers", "vip_qc.ods_sellers", "PRIMARY KEY (seller_id)", "一个商家"),
    ("customers", "vip_qc.ods_customers", "PRIMARY KEY (customer_id), KEY (customer_unique_id)",
     "⚠ 一个订单对应一个 customer_id；自然人是 customer_unique_id"),
    ("category_dim", "vip_qc.dim_category", "PRIMARY KEY (product_category_name)", "一个品类（葡语名 → 中文名 → 一级类目）"),
]

SCHEMA_DOC = """| 表 | 一行代表 | 主键 | 关键字段 |
|---|---|---|---|
| `orders` | 一个订单 | order_id | customer_id, order_status, order_purchase_timestamp（下单）, order_delivered_carrier_date（出库）, order_delivered_customer_date（签收）, order_estimated_delivery_date（承诺送达） |
| `order_items` | 订单里的一个商品行（同一商品买 2 件 = 2 行） | (order_id, order_item_id) | product_id, seller_id, shipping_limit_date（商家最晚发货时间）, price, freight_value |
| `order_reviews` | 一条评价，⚠ 同一订单可能有多条 | (review_id, order_id) | review_score（1-5）, review_comment_title, review_comment_message（葡语）, review_answer_timestamp（提交时间） |
| `review_tags` | 一条评价的 NLP 打标结果 | (review_id, order_id) | is_fake 假货, is_defect 质量缺陷, is_mismatch 货不对板, is_missing 少件漏发, is_package 包装破损, is_not_received 未收到货, is_delay 物流延迟, is_service 服务售后（0/1） |
| `order_payments` | 一笔支付（组合支付一单多行） | (order_id, payment_sequential) | payment_type, payment_installments, payment_value |
| `products` | 一个商品，⚠ 610 个缺品类 | product_id | product_category_name（葡语）, product_photos_qty, product_weight_g |
| `sellers` | 一个商家 | seller_id | seller_state |
| `customers` | ⚠ 一个订单对应一个 customer_id | customer_id | customer_unique_id（自然人）, customer_state |
| `category_dim` | 一个品类 | product_category_name | category_cn（中文名）, category_l1（一级类目） |

```mermaid
erDiagram
    customers ||--|| orders : "customer_id"
    orders ||--|{ order_items : "order_id"
    orders ||--o{ order_reviews : "order_id"
    orders ||--o{ order_payments : "order_id"
    order_reviews ||--|| review_tags : "review_id + order_id"
    order_items }o--|| products : "product_id"
    order_items }o--|| sellers : "seller_id"
    products }o--o| category_dim : "product_category_name"
```

**通用口径（题目没说时默认）**：签收 = `order_status = 'delivered'` 且签收时间非空；差评 = 1-2 星；品质客诉 = 最后一次评价 1-3 星且命中假货/质量缺陷/货不对板/少件漏发/包装破损任一标签；时间用半开区间；数据完整月份为 2017-01 ~ 2018-08。"""


def run(conn, sql):
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        while cur.nextset():
            pass
    df = pd.DataFrame(rows, columns=cols)
    for c in df.columns:
        if df[c].dtype == object:
            try:
                df[c] = pd.to_numeric(df[c])
            except (ValueError, TypeError):
                pass
    return df


def build_db():
    conn = connect(db=None)
    with conn.cursor() as cur:
        cur.execute(f"DROP DATABASE IF EXISTS {DB}")
        cur.execute(f"CREATE DATABASE {DB} DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
        cur.execute(f"USE {DB}")
        for name, src, keys, _ in TABLES:
            cols = "product_category_name, category_cn, category_l1" if name == "category_dim" else "*"
            cur.execute(f"CREATE TABLE {name} AS SELECT {cols} FROM {src}")
            cur.execute(f"ALTER TABLE {name} ADD {keys.replace(', KEY', ', ADD KEY')}")
        # 评价打标：按原始评价行（未去重）逐条打标，模拟"NLP 团队提供的打标结果表"
        cur.execute("SELECT review_id, order_id, CONCAT_WS(' ', review_comment_title, review_comment_message) FROM order_reviews")
        rows = cur.fetchall()
        cur.execute("""CREATE TABLE review_tags (
            review_id CHAR(32) NOT NULL, order_id CHAR(32) NOT NULL,
            is_fake TINYINT, is_defect TINYINT, is_mismatch TINYINT, is_missing TINYINT, is_package TINYINT,
            is_not_received TINYINT, is_delay TINYINT, is_service TINYINT,
            PRIMARY KEY (review_id, order_id)) COMMENT '评价 NLP 打标结果（每条评价一行，标签可多选）'""")
        keys = ["fake", "defect", "mismatch", "missing", "package", "not_received", "delay", "service"]
        data = []
        for rid, oid, txt in rows:
            t = tag_text(txt)
            data.append((rid, oid, *[t[k] for k in keys]))
        cur.executemany("INSERT INTO review_tags VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", data)
        ddl = []
        for name in [t[0] for t in TABLES] + ["review_tags"]:
            cur.execute(f"SHOW CREATE TABLE {name}")
            ddl.append(cur.fetchone()[1] + ";")
    conn.close()
    OUT_SQL.mkdir(parents=True, exist_ok=True)
    head = ("-- SQL 面试库 qc_interview 表结构（MySQL 8.0）\n-- 数据由 scripts/11_build_interview.py 从数仓 ODS 层复制而来，保留原始脏数据\n"
            f"CREATE DATABASE IF NOT EXISTS {DB} DEFAULT CHARSET utf8mb4;\nUSE {DB};\n\n")
    (OUT_SQL / "00_schema.sql").write_text(head + "\n\n".join(re.sub(r" AUTO_INCREMENT=\d+", "", d) for d in ddl) + "\n",
                                          encoding="utf-8")
    print(f"[OK] 面试库 {DB} 已建好（review_tags {len(data):,} 行）")


def md_table(df, max_rows=10):
    def fmt(v):
        if isinstance(v, float) and v == v and v.is_integer() and abs(v) >= 1:
            return str(int(v))
        if isinstance(v, float):
            return f"{v:.4f}".rstrip("0").rstrip(".") if abs(v) < 1000 else f"{v:.2f}"
        s = "" if v is None else str(v)
        s = s.replace("|", "/").replace("\n", " ")
        return s if len(s) <= 36 else s[:34] + "…"
    shown = df.head(max_rows)
    lines = ["| " + " | ".join(shown.columns) + " |", "|" + "---|" * len(shown.columns)]
    for r in shown.itertuples(index=False):
        lines.append("| " + " | ".join(fmt(v) for v in r) + " |")
    return "\n".join(lines)


def slug(q):
    return f"{q['id']}_{re.sub(r'[^0-9A-Za-z一-龥]+', '_', q['title']).strip('_')[:20]}"


def main():
    build_db()
    conn = connect(db=DB)
    results = []
    for q in Q:
        t0 = time.time()
        ans = run(conn, q["sql"])
        ms = (time.time() - t0) * 1000
        chk = run(conn, q["check"])
        if "answer_assert" in q:
            ok, note = q["answer_assert"](ans, chk)
        else:
            ok, note = bool(chk.ok.iloc[0]), str(chk.note.iloc[0])
        cross = run(conn, q["cross"]) if q.get("cross") else None
        wrong = run(conn, q["wrong"]) if q.get("wrong") else None
        cross_ok = None if cross is None else bool(cross.ok.iloc[0])
        status = "PASS" if ok and cross_ok is not False else "FAIL"
        print(f"  {status} {q['id']} {q['title']}  ({len(ans)} 行, {ms:.0f} ms)  自检: {note}"
              + ("" if cross is None else f" | 对账: {cross.note.iloc[0]} → {cross_ok}"))
        results.append(dict(q=q, ans=ans, ms=ms, ok=ok, note=note, cross=cross, wrong=wrong))
        (OUT_SQL / f"{slug(q)}.sql").write_text(
            f"-- {q['id']} {q['title']}（{q['level']}）\n-- 业务方原话：{q['ask']}\n-- 考点：{'；'.join(q['points'])}\n"
            f"USE {DB};\n\n{q['sql']}\n", encoding="utf-8")
    conn.close()
    fails = [r for r in results if not r["ok"] or (r["cross"] is not None and not bool(r["cross"].ok.iloc[0]))]
    write_docs(results)
    if fails:
        raise SystemExit(f"{len(fails)} 道题自检未通过")
    print(f"\n{len(results)}/{len(results)} 道题全部实跑通过 → docs/05_SQL面试题库.md")


def write_docs(results):
    levels = ["基础", "进阶", "高阶", "开放"]
    idx = ["| 编号 | 难度 | 题目 | 考点 |", "|---|---|---|---|"]
    for r in results:
        q = r["q"]
        idx.append(f"| [{q['id']}](#{q['id'].lower()}) | {q['level']} | {q['title']} | {'、'.join(q['points'])} |")

    full = [
        "# 05 SQL 面试题库：品控业务临时取数",
        "",
        "> 对应 JD 职责 4：**响应业务部门的临时取数需求，编写 SQL 提取原始数据，并进行基础的清洗和加工，支撑各业务决策。**",
        ">",
        "> 每道题都从**业务方原话**出发，要求先把\"业务语言\"翻译成\"数据口径\"，再写 SQL、做自检。"
        "全部答案在 MySQL 8.0 的面试库 `qc_interview` 上实际执行过，下方的结果预览就是真实运行结果；"
        "带\"与数仓对账\"的题目，还和项目数仓 / 看板上的数字逐一核对过。",
        "",
        "- 练习版（只有题目）：[05_SQL面试题_练习版.md](05_SQL面试题_练习版.md)",
        "- 每题答案单独成文件：`sql/interview/Qxx_*.sql`；建表语句：`sql/interview/00_schema.sql`",
        "- 重新生成：`python scripts/11_build_interview.py`",
        "",
        "## 答题方法（面试时按这个顺序讲）",
        "",
        "1. **口径**：指标公式（分子 / 分母）、时间字段与区间、范围、排除项、粒度、去重对象；读不出来的写成**假设**",
        "2. **表与粒度**：每张表一行是什么；一对多关联前先聚合",
        "3. **分层写 SQL**：CTE 一层做一件事（过滤 → 聚合到对象粒度 → 关联 → 算指标 → 输出）",
        "4. **自检**：粒度检查 `COUNT(*) = COUNT(DISTINCT 键)`、分项之和 = 总数、和已有报表对一次总数",
        "5. **交付**：结果 + 口径 + 假设 + 数据截止时间 + 最可能出错的地方",
        "",
        "## 面试库表结构",
        "",
        SCHEMA_DOC,
        "",
        "## 题目索引",
        "",
        *idx,
        "",
    ]
    practice = [
        "# 05 SQL 面试题 · 练习版（无答案）",
        "",
        "> 先自己写，再对照 [05_SQL面试题库.md](05_SQL面试题库.md)。每题都请先写出口径和假设，再写 SQL，最后写自检。",
        "",
        "## 面试库表结构",
        "",
        SCHEMA_DOC,
        "",
    ]
    for lv in levels:
        group = [r for r in results if r["q"]["level"] == lv]
        if not group:
            continue
        full += [f"---\n\n# {lv}题\n"]
        practice += [f"## {lv}题\n"]
        for r in group:
            q = r["q"]
            practice += [f"### {q['id']} {q['title']}\n", f"> {q['ask']}\n",
                         f"- 考点提示：{'、'.join(q['points'])}\n"]
            full += [
                f"## {q['id']}",
                f"### {q['title']}　`{q['level']}`",
                "",
                f"**考点**：{'、'.join(q['points'])}",
                "",
                f"> 💬 **业务方原话**：\"{q['ask']}\"",
                "",
                "**口径拆解**",
                "",
                *[f"- {c}" for c in q["caliber"]],
                "",
                "**默认假设**（交付时写明，业务方可纠正）",
                "",
                *[f"- {a}" for a in q["assume"]],
                "",
                "**思路**：" + " → ".join(q["logic"]),
                "",
                "**参考答案**",
                "",
                "```sql",
                q["sql"],
                "```",
                "",
                f"**实跑结果**（共 {len(r['ans'])} 行{'，展示前 10 行' if len(r['ans']) > 10 else ''}；耗时 {r['ms']:.0f} ms）",
                "",
                md_table(r["ans"]),
                "",
                "**自检**",
                "",
                "```sql",
                q["check"],
                "```",
                "",
                f"→ {'✅ 通过' if r['ok'] else '❌ 未通过'}：{r['note']}",
                "",
            ]
            if r["cross"] is not None:
                full += [f"**与数仓 / 看板对账**：{'✅' if bool(r['cross'].ok.iloc[0]) else '❌'} {r['cross'].note.iloc[0]}", ""]
            if r["wrong"] is not None:
                full += ["**❌ 常见错误写法**", "", "```sql", q["wrong"], "```", "", "错误写法的实跑结果：", "",
                         md_table(r["wrong"]), "", f"> {q['wrong_note']}", ""]
            full += ["**易错点**", "", *[f"- {p}" for p in q["pitfalls"]], "",
                     "**面试官可能的追问**", "", *[f"- {f}" for f in q["followups"]], ""]
    (ROOT / "docs" / "05_SQL面试题库.md").write_text("\n".join(full), encoding="utf-8")
    (ROOT / "docs" / "05_SQL面试题_练习版.md").write_text("\n".join(practice), encoding="utf-8")


if __name__ == "__main__":
    main()
