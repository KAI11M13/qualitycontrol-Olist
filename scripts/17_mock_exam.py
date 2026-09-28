"""Step 17：SQL 笔试模拟卷（45 分钟，100 分）。逐题在 MySQL 面试库上实跑参考答案、自检和常见扣分写法。

输出
  docs/09_SQL笔试模拟卷.md              试卷（限时作答用，无答案）
  docs/09_SQL笔试模拟卷_答案与评分.md    参考答案、实跑结果、评分点、扣分写法、开放题参考结论
  sql/exam/Ex_*.sql                    参考答案
依赖：先运行 11_build_interview.py 建好面试库 qc_interview。
"""
import importlib
import re
import time

from common import ROOT, connect
from exam_questions import E

ib = importlib.import_module("11_build_interview")
OUT_SQL = ROOT / "sql" / "exam"


def main():
    conn = connect(db=ib.DB)
    results = []
    for q in E:
        t0 = time.time()
        ans = ib.run(conn, q["sql"])
        ms = (time.time() - t0) * 1000
        chk = ib.run(conn, q["check"])
        ok, note = q["answer_assert"](ans, chk) if "answer_assert" in q else (bool(chk.ok.iloc[0]), str(chk.note.iloc[0]))
        wrong = ib.run(conn, q["wrong"]) if q.get("wrong") else None
        print(f"  {'PASS' if ok else 'FAIL'} {q['id']} {q['title']}（{len(ans)} 行，{ms:.0f} ms）自检：{note}")
        results.append(dict(q=q, ans=ans, ok=ok, note=note, wrong=wrong))
    conn.close()
    OUT_SQL.mkdir(parents=True, exist_ok=True)
    for old in OUT_SQL.glob("E[0-9]*.sql"):  # 题目改名后不留旧文件
        old.unlink()
    for r in results:
        q = r["q"]
        slug = re.sub(r"[^0-9A-Za-z一-龥]+", "_", q["title"]).strip("_")
        (OUT_SQL / f"{q['id']}_{slug}.sql").write_text(
            f"-- {q['id']} {q['title']}（{q['level']}，{q['score']} 分，建议 {q['minutes']} 分钟）\n-- 业务方原话：{q['ask']}\n"
            f"USE {ib.DB};\n\n{q['sql']};\n", encoding="utf-8")
    write_docs(results)
    fails = [r for r in results if not r["ok"]]
    if fails:
        raise SystemExit(f"{len(fails)} 道题自检未通过")
    print(f"  {len(results)}/{len(results)} 道题实跑通过 → docs/09_SQL笔试模拟卷.md")


def write_docs(results):
    total = sum(r["q"]["score"] for r in results)
    minutes = sum(r["q"]["minutes"] for r in results)
    paper = [
        "# 09 SQL 笔试模拟卷（45 分钟 · 100 分）",
        "",
        f"> 规则：限时 {minutes} 分钟，满分 {total} 分；在面试库 `qc_interview`（MySQL 8.0）上作答，表结构见下。"
        "每题先写一两行口径和假设，再写 SQL。题目与 [05 题库](05_SQL面试题库.md) 不重复。",
        ">",
        "> 做完再看 [答案与评分](09_SQL笔试模拟卷_答案与评分.md)，按评分点自己打分。",
        "",
        "| 题号 | 难度 | 分值 | 建议用时 | 题目 |",
        "|---|---|---|---|---|",
        *[f"| {r['q']['id']} | {r['q']['level']} | {r['q']['score']} | {r['q']['minutes']} 分钟 | {r['q']['title']} |" for r in results],
        "",
        "## 表结构",
        "",
        ib.SCHEMA_DOC,
        "",
        "## 题目",
        "",
    ]
    for r in results:
        q = r["q"]
        paper += [f"### {q['id']} {q['title']}（{q['level']} · {q['score']} 分 · {q['minutes']} 分钟）", "",
                  f"> 💬 \"{q['ask']}\"", "", f"- 用到的表：{q['tables']}", f"- 输出：{q['output']}", ""]
    ans = [
        "# 09 SQL 笔试模拟卷 · 答案与评分",
        "",
        "> 参考答案都在 MySQL 8.0 面试库 `qc_interview` 上实际执行过，下方结果是真实运行结果；每题都有独立的自检。"
        "评分点按\"口径 → 粒度 → 写法 → 自检\"给分，写出和参考答案不同但口径正确的 SQL 同样得分。",
        "",
        "- 试卷：[09_SQL笔试模拟卷.md](09_SQL笔试模拟卷.md)；答案文件：`sql/exam/Ex_*.sql`；重新生成：`python scripts/17_mock_exam.py`",
        "",
    ]
    for r in results:
        q = r["q"]
        ans += [f"## {q['id']} {q['title']}（{q['level']} · {q['score']} 分）", "", f"> 💬 \"{q['ask']}\"", "",
                "**评分点**", "", "| 分值 | 评分点 |", "|---|---|", *[f"| {p} | {d} |" for p, d in q["rubric"]], "",
                "**参考答案**", "", "```sql", q["sql"], "```", "",
                f"**实跑结果**（共 {len(r['ans'])} 行{'，展示前 10 行' if len(r['ans']) > 10 else ''}）", "", ib.md_table(r["ans"]), "",
                f"**自检**：{'✅' if r['ok'] else '❌'} {r['note']}", ""]
        if "answer_assert" not in q:
            ans += ["```sql", q["check"], "```", ""]
        else:
            ans += ["<details><summary>验算 SQL</summary>", "", "```sql", q["check"], "```", "", "</details>", ""]
        if r["wrong"] is not None:
            ans += ["**常见扣分写法**", "", "```sql", q["wrong"], "```", ""]
            if q.get("wrong_compare"):
                key, right_col, wrong_col = q["wrong_compare"]
                w = r["wrong"].copy()
                a = r["ans"][[key, right_col]].copy()
                w[key], a[key] = w[key].astype(str), a[key].astype(str)
                cmp_ = w.merge(a, on=key, how="left").rename(columns={right_col: "正确写法", wrong_col: "错误写法"})
                ans += ["与正确写法对比（实跑）：", "", ib.md_table(cmp_), ""]
            else:
                ans += [f"实跑结果（共 {len(r['wrong'])} 行{'，展示前 10 行' if len(r['wrong']) > 10 else ''}）：", "",
                        ib.md_table(r["wrong"]), ""]
            ans += [f"> {q['wrong_note']}", ""]
        if q.get("conclusion"):
            ans += ["**参考结论**", "", *[f"- {c}" for c in q["conclusion"]], ""]
    (ROOT / "docs" / "09_SQL笔试模拟卷.md").write_text("\n".join(paper), encoding="utf-8")
    (ROOT / "docs" / "09_SQL笔试模拟卷_答案与评分.md").write_text("\n".join(ans), encoding="utf-8")


if __name__ == "__main__":
    main()
