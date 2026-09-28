"""Step 3：评价文本打标（Python 预处理）→ dwd_review_tag + dim_complaint_rule。

对 dwd_review 的"标题 + 正文"做规则打标，输出每单一行的多标签 flag 与主标签。
"""
import pandas as pd

from common import connect, query
from complaint_rules import RULES, tag_text

TAG_CODES = [r[0] for r in RULES]


def main() -> None:
    df = query(
        "SELECT order_id, review_id, review_score, review_comment_title, review_comment_message "
        "FROM dwd_review"
    )
    text = df["review_comment_title"].fillna("") + " " + df["review_comment_message"].fillna("")
    tags = pd.DataFrame([tag_text(t) for t in text])
    out = pd.concat([df[["order_id", "review_id"]], tags], axis=1)
    out["primary_tag"] = out["primary_tag"].astype(object).where(out["primary_tag"].notna(), None)

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS dwd_review_tag")
            flag_cols = ",\n".join(f"tag_{c} TINYINT NOT NULL" for c in TAG_CODES)
            cur.execute(
                f"""CREATE TABLE dwd_review_tag (
                    order_id CHAR(32) PRIMARY KEY,
                    review_id CHAR(32),
                    {flag_cols},
                    primary_tag VARCHAR(20) NULL COMMENT '按优先级取的主标签'
                ) COMMENT 'DWD-评价文字标签（多标签 + 主标签）'"""
            )
            cols = ["order_id", "review_id"] + TAG_CODES + ["primary_tag"]
            sql = (
                f"INSERT INTO dwd_review_tag (order_id, review_id, "
                f"{', '.join('tag_' + c for c in TAG_CODES)}, primary_tag) "
                f"VALUES ({', '.join(['%s'] * len(cols))})"
            )
            rows = [tuple(r) for r in out[cols].itertuples(index=False, name=None)]
            for i in range(0, len(rows), 5000):
                cur.executemany(sql, rows[i : i + 5000])

            cur.execute("DROP TABLE IF EXISTS dim_complaint_rule")
            cur.execute(
                """CREATE TABLE dim_complaint_rule (
                    tag_code VARCHAR(20) PRIMARY KEY, tag_name VARCHAR(32), tag_group VARCHAR(16),
                    priority INT, regex_rule TEXT
                ) COMMENT 'DIM-标签字典（识别规则）'"""
            )
            cur.executemany("INSERT INTO dim_complaint_rule VALUES (%s,%s,%s,%s,%s)", RULES)
    finally:
        conn.close()

    print(f"[OK] dwd_review_tag {len(out):,} 行")
    low = df["review_score"] <= 3
    summary = pd.DataFrame(
        {
            "全部评价命中数": out[TAG_CODES].sum(),
            "1-3星命中数": out.loc[low, TAG_CODES].sum(),
        }
    )
    print(summary)


if __name__ == "__main__":
    main()
